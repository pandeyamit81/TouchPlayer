"""SMS operations for a SIM868 GPIO-UART modem."""
import asyncio
import json
import os
import re
import select
import subprocess
import termios
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

SERIAL_DEVICE = os.environ.get("TOUCHPLAYER_CELLULAR_SERIAL", "/dev/serial0")
SERIAL_BAUD = int(os.environ.get("TOUCHPLAYER_CELLULAR_BAUD", "115200"))
PPP_SERVICE = os.environ.get("TOUCHPLAYER_CELLULAR_SERVICE", "touchplayer-cellular.service")
PWRKEY_SCRIPT = os.environ.get("TOUCHPLAYER_CELLULAR_PWRKEY_SCRIPT", "/opt/touchplayer/scripts/sim868_pwrkey.py")
SERIAL_LOCK_PATHS = tuple(
    Path(lock_dir) / f"LCK..{Path(SERIAL_DEVICE).name}"
    for lock_dir in ("/run/lock", "/var/lock")
)
SMS_SERVICE_CENTER = os.environ.get("TOUCHPLAYER_SMS_SERVICE_CENTER", "+919810051914")
SMS_LOCK = asyncio.Lock()
PROJECT_DIR = Path(__file__).resolve().parents[3]
SMS_HISTORY_PATH = Path(os.environ.get("TOUCHPLAYER_SMS_HISTORY_PATH", str(PROJECT_DIR / "cache" / "sms_messages.json")))
NETWORK_STATUS_PATH = Path(os.environ.get("TOUCHPLAYER_NETWORK_STATUS_PATH", str(PROJECT_DIR / "cache" / "cellular_status.json")))
SMS_HEADER = re.compile(r'^\+CMGL:\s*(\d+),"([^"]*)","([^"]*)",(.*)$')
NETWORK_STATUS_FIELDS = (
    "sim_ready",
    "signal",
    "signal_quality",
    "registration",
    "packet_registration",
    "registered",
    "packet_attached",
    "operator",
    "apn",
)


def _load_json(path: Path, default: Any) -> Any:
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=True, indent=2)
    os.replace(temporary_path, path)


stored_network_status = _load_json(NETWORK_STATUS_PATH, {})
NETWORK_STATUS_CACHE: Dict[str, Any] = {
    key: stored_network_status[key]
    for key in NETWORK_STATUS_FIELDS
    if isinstance(stored_network_status, dict) and key in stored_network_status
}
ALLOWED_SMS_NUMBERS = frozenset({
    "7007507180",
    "9119688888",
    "8090498544",
    "9415044433",
})


class SMSService:
    """Read and send SMS messages through the SIM868 AT interface."""

    def read_messages(self) -> List[Dict[str, Any]]:
        modem_messages = self._with_modem(self._read_messages)
        stored_ids = {message["id"] for message in modem_messages}
        stored_history = _load_json(SMS_HISTORY_PATH, [])
        if not isinstance(stored_history, list):
            stored_history = []
        stored_sent = [
            message for message in stored_history
            if isinstance(message, dict) and message.get("id") not in stored_ids
        ]
        return modem_messages + stored_sent

    def send_message(self, number: str, text: str) -> Dict[str, Any]:
        normalized_number = re.sub(r"\D", "", number)
        if normalized_number.startswith("91") and len(normalized_number) == 12:
            normalized_number = normalized_number[2:]
        if normalized_number not in ALLOWED_SMS_NUMBERS:
            raise ValueError("SMS recipient is not in the approved contact list")
        if not text.strip() or len(text) > 1600:
            raise ValueError("SMS text must contain 1 to 1600 characters")
        result = self._with_modem(lambda: self._send_message(normalized_number, text))
        sent_message = {
            "id": -(time.time_ns() // 1_000_000),
            "modem_status": "STO SENT",
            "status": "submitted",
            "direction": "sent",
            "number": f"+91{normalized_number}",
            "date": datetime.now(timezone.utc).isoformat(),
            "text": text,
            "reference": result.get("reference"),
        }
        try:
            history = _load_json(SMS_HISTORY_PATH, [])
            if not isinstance(history, list):
                history = []
            _save_json(SMS_HISTORY_PATH, [*history, sent_message])
        except OSError as error:
            logger.warning("SMS sent but could not save local history: {}", error)
        return result

    def delete_message(self, message_id: int) -> None:
        if message_id == 0:
            raise ValueError("Invalid SMS message id")
        if message_id < 0:
            history = _load_json(SMS_HISTORY_PATH, [])
            if isinstance(history, list):
                _save_json(
                    SMS_HISTORY_PATH,
                    [message for message in history if message.get("id") != message_id],
                )
            return
        self._with_modem(lambda: self._delete_messages(message_id))

    def delete_all_messages(self) -> None:
        self._with_modem(lambda: self._delete_messages())
        try:
            _save_json(SMS_HISTORY_PATH, [])
        except OSError as error:
            logger.warning("SMS modem storage cleared but local history could not be cleared: {}", error)

    def get_network_status(self) -> Dict[str, Any]:
        """Return SIM868 registration, signal, and PPP connection details."""
        service_active = self._service_is_active()
        status: Dict[str, Any] = {
            "service": "active" if service_active else "inactive",
            "serial_device": SERIAL_DEVICE,
            "serial_available": os.path.exists(SERIAL_DEVICE),
            "sim_ready": None,
            "signal": None,
            "signal_quality": None,
            "registration": "unknown",
            "packet_registration": "unknown",
            "registered": None,
            "packet_attached": None,
            "operator": None,
            "apn": None,
            "ppp_interface": "ppp0",
            "ppp_connected": False,
            "ip_addresses": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        status.update(self._read_ppp_status())
        if not status["serial_available"]:
            status["message"] = "SIM868 UART device is not available"
            return status
        if status["ppp_connected"]:
            status.update(NETWORK_STATUS_CACHE)
        else:
            try:
                modem_status = self._with_modem(self._read_network_status)
                NETWORK_STATUS_CACHE.update({
                    key: modem_status[key]
                    for key in NETWORK_STATUS_FIELDS
                    if key in modem_status
                })
                try:
                    _save_json(NETWORK_STATUS_PATH, NETWORK_STATUS_CACHE)
                except OSError as error:
                    logger.warning("Cellular status read succeeded but could not be cached: {}", error)
                status.update(modem_status)
                status.update(self._read_ppp_status())
                status["service"] = "active" if self._service_is_active() else "inactive"
            except Exception as error:
                status["modem_error"] = str(error)
        status["healthy"] = bool(
            status.get("ppp_connected")
            and status.get("sim_ready") is not False
            and status.get("registered") is not False
            and status.get("packet_attached") is not False
        )
        return status

    def restart_network(self) -> Dict[str, Any]:
        """Restart the UART PPP service and return its resulting state."""
        self._run_systemctl("stop", no_block=True)
        self._wait_for_service_state(active=False)
        self._wait_for_serial_release()
        self._pulse_pwrkey()
        time.sleep(8)
        self._run_systemctl("start")
        self._wait_for_service_state(active=True)
        self._wait_for_ppp_connection()
        return {
            "service": "active" if self._service_is_active() else "inactive",
            "message": "SIM868 PWRKEY pulse sent; cellular network service restart requested",
        }

    def _with_modem(self, operation):
        was_active = self._service_is_active()
        if was_active:
            self._run_systemctl("stop", no_block=True)
            self._wait_for_service_state(active=False)
            self._wait_for_serial_release()
        try:
            return operation()
        finally:
            if was_active:
                try:
                    self._run_systemctl("start")
                    self._wait_for_service_state(active=True)
                    self._wait_for_ppp_connection()
                except Exception as error:
                    logger.error("Failed to restore cellular service after SMS operation: {}", error)

    def _read_messages(self) -> List[Dict[str, Any]]:
        with self._open_serial() as serial:
            self._enter_command_mode(serial)
            self._command(serial, "AT")
            self._command(serial, "ATE0")
            self._command(serial, "AT+CMGF=1")
            response = self._command(serial, 'AT+CMGL="ALL"')

        lines = [line.strip() for line in response.replace("\r", "").split("\n") if line.strip()]
        messages: List[Dict[str, Any]] = []
        index = 0
        while index < len(lines):
            match = SMS_HEADER.match(lines[index])
            if match and index + 1 < len(lines):
                modem_status = match.group(2).upper()
                is_received = modem_status.startswith("REC")
                if modem_status == "REC UNREAD":
                    status = "unread"
                elif modem_status == "REC READ":
                    status = "read"
                elif modem_status == "STO SENT":
                    status = "delivered"
                elif modem_status == "STO UNSENT":
                    status = "undelivered"
                else:
                    status = modem_status.lower().replace(" ", "_")
                date_match = re.search(r'"([^"]*)"\s*$', match.group(4))
                messages.append({
                    "id": int(match.group(1)),
                    "modem_status": modem_status,
                    "status": status,
                    "direction": "received" if is_received else "sent",
                    "number": match.group(3),
                    "date": date_match.group(1) if date_match else "",
                    "text": lines[index + 1],
                })
                index += 2
            else:
                index += 1
        return messages

    def _read_network_status(self) -> Dict[str, Any]:
        with self._open_serial() as serial:
            self._enter_command_mode(serial)
            self._command(serial, "AT")
            self._command(serial, "ATE0")
            commands = {
                "sim": "AT+CPIN?",
                "signal": "AT+CSQ",
                "registration": "AT+CREG?",
                "packet_registration": "AT+CGREG?",
                "attachment": "AT+CGATT?",
                "operator": "AT+COPS?",
                "context": "AT+CGDCONT?",
            }
            responses: Dict[str, str] = {}
            command_errors: List[str] = []
            for key, command in commands.items():
                try:
                    responses[key] = self._command(serial, command, timeout=2)
                except RuntimeError as error:
                    command_errors.append(str(error))

        sim_match = re.search(r"\+CPIN:\s*([^\r\n]+)", responses.get("sim", ""))
        signal_match = re.search(r"\+CSQ:\s*(\d+),(\d+)", responses.get("signal", ""))
        registration_match = re.search(r"\+CREG:\s*\d,([0-5])", responses.get("registration", ""))
        packet_registration_match = re.search(r"\+CGREG:\s*\d,([0-5])", responses.get("packet_registration", ""))
        attachment_match = re.search(r"\+CGATT:\s*([01])", responses.get("attachment", ""))
        operator_match = re.search(r"\+COPS:\s*\d(?:,\d)?(?:,\"([^\"]*)\")?", responses.get("operator", ""))
        context_match = re.search(r'\+CGDCONT:\s*\d+,"[^"]*","([^"]*)"', responses.get("context", ""))
        registration = registration_match.group(1) if registration_match else "unknown"
        packet_registration = packet_registration_match.group(1) if packet_registration_match else "unknown"
        result: Dict[str, Any] = {
            "sim_ready": bool(sim_match and sim_match.group(1).strip() == "READY"),
            "signal": int(signal_match.group(1)) if signal_match else None,
            "signal_quality": int(signal_match.group(2)) if signal_match else None,
            "registration": registration,
            "packet_registration": packet_registration,
            "registered": registration in {"1", "5"} or packet_registration in {"1", "5"},
            "packet_attached": bool(attachment_match and attachment_match.group(1) == "1"),
            "operator": operator_match.group(1) if operator_match else None,
            "apn": context_match.group(1) if context_match else None,
        }
        if command_errors:
            result["modem_error"] = "; ".join(command_errors)
        return result

    @staticmethod
    def _read_ppp_status() -> Dict[str, Any]:
        result = subprocess.run(
            ["ip", "-j", "address", "show", "dev", "ppp0"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        try:
            interfaces = json.loads(result.stdout) if result.stdout else []
        except json.JSONDecodeError:
            interfaces = []
        addresses = [address.get("local") for address in (interfaces[0].get("addr_info", []) if interfaces else []) if address.get("local")]
        return {"ppp_connected": bool(interfaces and interfaces[0].get("operstate") == "UNKNOWN" and addresses), "ip_addresses": addresses}

    def _send_message(self, number: str, text: str) -> Dict[str, Any]:
        with self._open_serial() as serial:
            self._enter_command_mode(serial)
            self._command(serial, "AT")
            self._command(serial, "ATE0")
            self._require_network_registration(serial)
            self._ensure_service_center(serial)
            self._command(serial, "AT+CMGF=1")
            modem_number = f"+91{number}"
            self._write(serial, f'AT+CMGS="{modem_number}"\r'.encode())
            prompt = self._read_until(serial, {b">"}, 10)
            if b">" not in prompt:
                raise RuntimeError("Modem did not accept the SMS recipient")
            self._write(serial, text.encode() + b"\x1a")
            sent_response = self._read_until(serial, {b"OK", b"ERROR"}, 60)
            if b"ERROR" in sent_response:
                sent_response += self._read_until(serial, set(), 2)
                self._write(serial, b"\x1b")
            if b"ERROR" in sent_response or b"OK" not in sent_response:
                detail = sent_response.decode(errors="replace").strip()
                raise RuntimeError(f"The modem did not confirm SMS submission: {detail or 'no response'}")
            reference = re.search(rb"\+CMGS:\s*(\d+)", sent_response)
            return {"reference": int(reference.group(1)) if reference else None}

    def _delete_messages(self, message_id: int | None = None) -> None:
        with self._open_serial() as serial:
            self._enter_command_mode(serial)
            self._command(serial, "AT")
            self._command(serial, "ATE0")
            command = f"AT+CMGD={message_id}" if message_id is not None else "AT+CMGD=1,4"
            self._command(serial, command)

    def _open_serial(self):
        fd = os.open(SERIAL_DEVICE, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attributes = termios.tcgetattr(fd)
        attributes[0] = 0
        attributes[1] = 0
        attributes[2] = termios.CS8 | termios.CLOCAL | termios.CREAD
        attributes[3] = 0
        baud = getattr(termios, f"B{SERIAL_BAUD}", None)
        if baud is None:
            raise ValueError(f"Unsupported cellular UART baud rate: {SERIAL_BAUD}")
        attributes[4] = baud
        attributes[5] = baud
        termios.tcsetattr(fd, termios.TCSANOW, attributes)
        termios.tcflush(fd, termios.TCIOFLUSH)
        return os.fdopen(fd, "r+b", buffering=0)

    @staticmethod
    def _write(serial, data: bytes) -> None:
        serial.write(data)

    @staticmethod
    def _enter_command_mode(serial) -> None:
        termios.tcflush(serial.fileno(), termios.TCIOFLUSH)
        serial.write(b"AT\r")
        response = SMSService._read_until(serial, {b"OK", b"ERROR"}, 2)
        if b"OK" in response:
            return

        # pppd can leave the modem in online data mode after it exits. The
        # guard time prevents the escape sequence from becoming user data.
        time.sleep(1.1)
        serial.write(b"+++")
        time.sleep(1.1)
        termios.tcflush(serial.fileno(), termios.TCIOFLUSH)
        for _ in range(3):
            serial.write(b"AT\r")
            response = SMSService._read_until(serial, {b"OK", b"ERROR"}, 2)
            if b"OK" in response:
                return
            time.sleep(0.5)
        raise RuntimeError("Modem did not return to command mode after PPP escape")

    def _ensure_service_center(self, serial) -> None:
        response = self._command(serial, "AT+CSCA?")
        current = re.search(r'\+CSCA:\s*"(\+?[0-9]{8,20})"', response)
        configured = re.sub(r"\D", "", SMS_SERVICE_CENTER)
        if not configured:
            raise RuntimeError("No SMS service-center number is configured")
        if not current or re.sub(r"\D", "", current.group(1)) != configured:
            self._command(serial, f'AT+CSCA="{SMS_SERVICE_CENTER}",145')

    def _require_network_registration(self, serial) -> None:
        circuit_response = self._command(serial, "AT+CREG?")
        packet_response = self._command(serial, "AT+CGREG?")
        circuit_match = re.search(r"\+CREG:\s*\d,([0-5])", circuit_response)
        packet_match = re.search(r"\+CGREG:\s*\d,([0-5])", packet_response)
        registered = {match.group(1) for match in (circuit_match, packet_match) if match}
        if not registered.intersection({"1", "5"}):
            status = ", ".join(sorted(registered)) or "unknown"
            raise RuntimeError(
                f"Cellular network registration unavailable (CREG/CGREG status {status}); SMS was not sent"
            )

    def _command(self, serial, command: str, timeout: float = 10) -> str:
        attempts = 3 if command == "AT" else 2
        last_response = b""
        for attempt in range(attempts):
            self._write(serial, (command + "\r").encode())
            response = self._read_until(serial, {b"OK", b"ERROR"}, timeout)
            if b"OK" in response and b"ERROR" not in response:
                return response.decode(errors="replace")
            last_response = response
            transient_error = not response or b"+CME ERROR: 19" in response
            if attempt < attempts - 1 and transient_error:
                time.sleep(0.5)
                termios.tcflush(serial.fileno(), termios.TCIOFLUSH)
            elif not transient_error:
                break
        raise RuntimeError(f"Modem command failed: {command} ({last_response.decode(errors='replace').strip()})")

    @staticmethod
    def _read_until(serial, markers: set[bytes], timeout: float) -> bytes:
        response = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            ready, _, _ = select.select([serial], [], [], min(0.25, remaining))
            if ready:
                data = serial.read(4096)
                if data:
                    response.extend(data)
                if any(marker in response for marker in markers):
                    return bytes(response)
        return bytes(response)

    @staticmethod
    def _service_is_active() -> bool:
        result = subprocess.run(
            ["sudo", "-n", "systemctl", "is-active", "--quiet", PPP_SERVICE],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0

    @staticmethod
    def _run_systemctl(action: str, no_block: bool = False) -> None:
        if action == "start":
            reset_result = subprocess.run(
                ["sudo", "-n", "systemctl", "reset-failed", PPP_SERVICE],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if reset_result.returncode != 0:
                raise RuntimeError(reset_result.stderr.strip() or "Could not reset cellular service state")
        command = ["sudo", "-n", "systemctl", action]
        if no_block:
            command.append("--no-block")
        command.append(PPP_SERVICE)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Could not {action} cellular service")

    @staticmethod
    def _pulse_pwrkey() -> None:
        result = subprocess.run(
            ["sudo", "-n", "/usr/bin/python3", PWRKEY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Could not pulse SIM868 PWRKEY")

    @staticmethod
    def _wait_for_service_state(active: bool, timeout: float = 10) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            is_active = SMSService._service_is_active()
            if is_active == active:
                return
            time.sleep(0.25)
        expected = "active" if active else "inactive"
        raise RuntimeError(f"Cellular service did not become {expected} in time")

    @staticmethod
    def _wait_for_ppp_connection(timeout: float = 30) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not SMSService._service_is_active():
                return
            if SMSService._read_ppp_status()["ppp_connected"]:
                return
            time.sleep(0.25)

    @staticmethod
    def _wait_for_serial_release(timeout: float = 10) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not any(lock_path.exists() for lock_path in SERIAL_LOCK_PATHS):
                return
            time.sleep(0.25)
        locks = ", ".join(str(lock_path) for lock_path in SERIAL_LOCK_PATHS if lock_path.exists())
        raise RuntimeError(f"Cellular UART is still locked: {locks or SERIAL_DEVICE}")


async def read_sms_messages() -> List[Dict[str, Any]]:
    async with SMS_LOCK:
        return await asyncio.to_thread(SMSService().read_messages)


async def send_sms_message(number: str, text: str) -> Dict[str, Any]:
    async with SMS_LOCK:
        return await asyncio.to_thread(SMSService().send_message, number, text)


async def delete_sms_message(message_id: int) -> None:
    async with SMS_LOCK:
        await asyncio.to_thread(SMSService().delete_message, message_id)


async def delete_all_sms_messages() -> None:
    async with SMS_LOCK:
        await asyncio.to_thread(SMSService().delete_all_messages)


async def get_sms_network_status() -> Dict[str, Any]:
    async with SMS_LOCK:
        return await asyncio.to_thread(SMSService().get_network_status)


async def restart_sms_network() -> Dict[str, Any]:
    async with SMS_LOCK:
        return await asyncio.to_thread(SMSService().restart_network)
