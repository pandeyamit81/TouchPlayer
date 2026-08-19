"""
TouchPlayer Samba Manager
Configures a single Samba (SMB) file share for uploading/downloading files
over the local network, backed by an include file managed by TouchPlayer.
"""
import configparser
import grp
import os
import pwd
import re
import socket
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

SAMBA_INCLUDE_PATH = "/etc/samba/smb.conf.d/touchplayer.conf"
SHARE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
MANAGED_HEADER = "# Managed by TouchPlayer -- edited via Settings > Network Share\n"


class SambaManager:
    """Manages the TouchPlayer-owned Samba share definition"""

    def __init__(self, include_path: str = SAMBA_INCLUDE_PATH):
        self.include_path = Path(include_path)

    def is_active(self) -> bool:
        """Check whether the smbd service is running"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "smbd"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() == "active"
        except Exception as e:
            logger.warning(f"Failed to check smbd status: {e}")
            return False

    def get_share(self) -> Optional[Dict[str, Any]]:
        """Read the currently configured share, if any"""
        if not self.include_path.exists():
            return None

        parser = configparser.ConfigParser(delimiters=("=",), strict=False)
        try:
            parser.read(self.include_path)
        except configparser.Error as e:
            logger.warning(f"Failed to parse Samba include file: {e}")
            return None

        sections = [s for s in parser.sections() if s.upper() != "GLOBAL"]
        if not sections:
            return None

        name = sections[0]
        section = parser[name]
        return {
            "name": name,
            "path": section.get("path", ""),
            "read_only": section.get("read only", "no").strip().lower() in ("yes", "true", "1"),
            "guest_ok": section.get("guest ok", "no").strip().lower() in ("yes", "true", "1"),
            "server": socket.gethostname(),
            "smb_url": f"smb://{socket.gethostname()}/{name}",
        }

    def list_files(self, subpath: str = "") -> Dict[str, Any]:
        """List the shared folder's contents with permissions, owner, and size"""
        share = self.get_share()
        if not share or not share.get("path"):
            return {"error": "No shared folder is configured"}

        root = Path(share["path"]).resolve()
        target = (root / subpath).resolve() if subpath else root

        # Prevent escaping the shared folder via ".." segments.
        if root not in target.parents and target != root:
            return {"error": "Invalid path"}

        if not target.exists():
            return {"error": "Folder not found"}

        entries: List[Dict[str, Any]] = []
        try:
            for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
                try:
                    info = entry.stat()
                except OSError:
                    continue

                try:
                    owner = pwd.getpwuid(info.st_uid).pw_name
                except KeyError:
                    owner = str(info.st_uid)
                try:
                    group = grp.getgrgid(info.st_gid).gr_name
                except KeyError:
                    group = str(info.st_gid)

                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": info.st_size,
                    "permissions": stat.filemode(info.st_mode),
                    "owner": owner,
                    "group": group,
                    "modified": info.st_mtime,
                })
        except OSError as e:
            return {"error": f"Failed to list folder: {e}"}

        relative = str(target.relative_to(root)) if target != root else ""
        return {
            "path": relative,
            "entries": entries,
        }

    def _ensure_directory(self, path: str) -> Optional[str]:
        """Create the shared directory if needed; returns an error message on failure"""
        try:
            os.makedirs(path, exist_ok=True)
            return None
        except PermissionError:
            pass

        try:
            subprocess.run(["sudo", "-n", "mkdir", "-p", path], check=True, capture_output=True, text=True, timeout=10)
            subprocess.run(["sudo", "-n", "chown", "pi:pi", path], check=True, capture_output=True, text=True, timeout=10)
            return None
        except subprocess.CalledProcessError as e:
            return e.stderr.strip() or "Failed to create shared directory"
        except Exception as e:
            return str(e)

    def apply_share(
        self,
        name: str,
        path: str,
        read_only: bool = False,
        guest_ok: bool = True,
    ) -> Dict[str, Any]:
        """Configure (or replace) the single managed Samba share"""
        if not SHARE_NAME_PATTERN.match(name):
            return {"error": "Share name must be 1-32 letters, numbers, hyphens, or underscores"}

        abs_path = os.path.abspath(path)
        dir_error = self._ensure_directory(abs_path)
        if dir_error:
            return {"error": f"Could not prepare shared folder: {dir_error}"}

        content = (
            f"{MANAGED_HEADER}"
            f"[{name}]\n"
            f"    comment = TouchPlayer shared folder\n"
            f"    path = {abs_path}\n"
            f"    browseable = yes\n"
            f"    read only = {'yes' if read_only else 'no'}\n"
            f"    guest ok = {'yes' if guest_ok else 'no'}\n"
            f"    force user = pi\n"
            f"    force group = pi\n"
            f"    create mask = 0664\n"
            f"    directory mask = 0775\n"
        )

        write_error = self._write_include(content)
        if write_error:
            return {"error": write_error}

        reload_error = self._reload_smbd()
        if reload_error:
            return {"error": reload_error}

        return {"success": True, "share": self.get_share()}

    def remove_share(self) -> Dict[str, Any]:
        """Remove the managed share definition"""
        write_error = self._write_include(MANAGED_HEADER)
        if write_error:
            return {"error": write_error}

        reload_error = self._reload_smbd()
        if reload_error:
            return {"error": reload_error}

        return {"success": True}

    def _write_include(self, content: str) -> Optional[str]:
        """Write the include file via sudo since /etc/samba is root-owned"""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            subprocess.run(
                ["sudo", "-n", "install", "-m", "644", "-o", "root", "-g", "root", tmp_path, str(self.include_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to write Samba include file: {e.stderr}")
            return e.stderr.strip() or "Failed to write Samba configuration"
        except Exception as e:
            logger.error(f"Failed to write Samba include file: {e}")
            return str(e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _reload_smbd(self) -> Optional[str]:
        """Restart smbd so the new share definition takes effect"""
        try:
            subprocess.run(
                ["sudo", "-n", "systemctl", "restart", "smbd"],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart smbd: {e.stderr}")
            return e.stderr.strip() or "Failed to restart Samba service"
        except Exception as e:
            logger.error(f"Failed to restart smbd: {e}")
            return str(e)


# Global instance
samba_manager = SambaManager()
