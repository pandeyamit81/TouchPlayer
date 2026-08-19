"""
TouchPlayer Bluetooth Manager
"""
import asyncio
import json
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger


BLUETOOTH_ADDRESS = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
PROJECT_DIR = Path(__file__).resolve().parents[4]
AUTOCONNECT_PATH = Path(
    os.environ.get("TOUCHPLAYER_BLUETOOTH_AUTOCONNECT", str(PROJECT_DIR / "data" / "bluetooth_autoconnect.json"))
)


class BluetoothManager:
    """Bluetooth manager service"""
    
    def __init__(self):
        self._running = False
    
    async def run(self):
        """Run the Bluetooth manager"""
        self._running = True
        logger.info("Bluetooth manager started")
        await self.reconnect_saved_devices()
        
        while self._running:
            try:
                # In a real implementation, this would handle Bluetooth events
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Bluetooth manager error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the Bluetooth manager"""
        self._running = False
    
    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get paired Bluetooth devices"""
        try:
            result = subprocess.run(
                ["bluetoothctl", "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                devices = []
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            devices.append({
                                "address": parts[1],
                                "name": " ".join(parts[2:]) if len(parts) > 2 else "",
                            })
                return devices
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get Bluetooth devices: {e}")
            return []
    
    async def scan(self) -> bool:
        """Start Bluetooth device scan"""
        try:
            result = subprocess.run(
                ["bluetoothctl", "scan on"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to start Bluetooth scan: {e}")
            return False
    
    async def connect(self, address: str) -> bool:
        """Connect to Bluetooth device"""
        self._validate_address(address)
        try:
            result = subprocess.run(
                ["bluetoothctl", "connect", address],
                capture_output=True,
                text=True,
                timeout=30
            )
            output = f"{result.stdout}\n{result.stderr}"
            connected = result.returncode == 0 and (
                "Connection successful" in output or "Connected: yes" in output
            )
            if connected:
                self._trust_device(address)
                self._remember_device(address)
            return connected
        except Exception as e:
            logger.error(f"Failed to connect to device: {e}")
            return False
    
    async def disconnect(self, address: str) -> bool:
        """Disconnect from Bluetooth device"""
        self._validate_address(address)
        try:
            result = subprocess.run(
                ["bluetoothctl", "disconnect", address],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to disconnect device: {e}")
            return False
    
    async def remove(self, address: str) -> bool:
        """Remove paired Bluetooth device"""
        self._validate_address(address)
        try:
            result = subprocess.run(
                ["bluetoothctl", "remove", address],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self._forget_device(address)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to remove device: {e}")
            return False
    
    async def status(self) -> Dict[str, Any]:
        """Get Bluetooth adapter status"""
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                status = {}
                for line in result.stdout.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        status[key.strip()] = value.strip()
                return status
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get Bluetooth status: {e}")
            return {}

    async def reconnect_saved_devices(self, attempts: int = 12, delay: float = 5.0) -> None:
        """Reconnect remembered audio devices after BlueZ becomes available."""
        addresses = self._read_saved_devices()
        if not addresses:
            addresses = self._get_connected_devices()
            if addresses:
                for address in addresses:
                    self._trust_device(address)
                    self._remember_device(address)
                logger.info("Remembered currently connected Bluetooth devices: {}", ", ".join(addresses))
            else:
                logger.info("No Bluetooth devices are configured for autoconnect")
                return

        for attempt in range(1, attempts + 1):
            if not self._running:
                return

            remaining = []
            for address in addresses:
                try:
                    if self._is_connected(address):
                        logger.info("Bluetooth device {} is already connected", address)
                        continue
                    if await self.connect(address):
                        logger.info("Reconnected Bluetooth device {}", address)
                    else:
                        remaining.append(address)
                except Exception as error:
                    logger.warning("Bluetooth reconnect attempt failed for {}: {}", address, error)
                    remaining.append(address)

            if not remaining:
                return
            addresses = remaining
            if attempt < attempts:
                logger.info(
                    "Bluetooth devices unavailable; retrying in {} seconds ({}/{})",
                    delay,
                    attempt,
                    attempts,
                )
                await asyncio.sleep(delay)

        logger.warning("Could not reconnect Bluetooth devices after {} attempts", attempts)

    @staticmethod
    def _validate_address(address: str) -> None:
        if not BLUETOOTH_ADDRESS.fullmatch(address):
            raise ValueError(f"Invalid Bluetooth address: {address}")

    @staticmethod
    def _is_connected(address: str) -> bool:
        result = subprocess.run(
            ["bluetoothctl", "info", address],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "Connected: yes" in result.stdout

    @staticmethod
    def _get_connected_devices() -> List[str]:
        result = subprocess.run(
            ["bluetoothctl", "devices", "Connected"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        addresses = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and BLUETOOTH_ADDRESS.fullmatch(parts[1]):
                addresses.append(parts[1])
        return addresses

    @staticmethod
    def _trust_device(address: str) -> None:
        result = subprocess.run(
            ["bluetoothctl", "trust", address],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("Could not mark Bluetooth device {} as trusted", address)

    @staticmethod
    def _read_saved_devices() -> List[str]:
        try:
            with AUTOCONNECT_PATH.open("r", encoding="utf-8") as file:
                saved = json.load(file)
            if not isinstance(saved, list):
                return []
            return [address for address in saved if isinstance(address, str) and BLUETOOTH_ADDRESS.fullmatch(address)]
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Could not read Bluetooth autoconnect state: {}", error)
            return []

    @staticmethod
    def _remember_device(address: str) -> None:
        addresses = BluetoothManager._read_saved_devices()
        if address not in addresses:
            addresses.append(address)
        AUTOCONNECT_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = AUTOCONNECT_PATH.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(addresses, file)
        temporary_path.replace(AUTOCONNECT_PATH)

    @staticmethod
    def _forget_device(address: str) -> None:
        addresses = [saved for saved in BluetoothManager._read_saved_devices() if saved != address]
        if not addresses:
            try:
                AUTOCONNECT_PATH.unlink()
            except FileNotFoundError:
                pass
            return
        AUTOCONNECT_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = AUTOCONNECT_PATH.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(addresses, file)
        temporary_path.replace(AUTOCONNECT_PATH)
    
    async def __aenter__(self):
        await self.run()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
