"""
TouchPlayer WiFi API Routes
WiFi network management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_session

router = APIRouter()


@router.get("/wifi/networks")
async def get_wifi_networks():
    """Get available WiFi networks"""
    try:
        import subprocess
        result = subprocess.run(
            ["nmcli", "-t", "-f", "BSSID,SSID,MODE,CHAN,SIGNAL,SECURITY", "device", "wifi", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            networks = []
            
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                
                # Parse colon-separated format (BSSID uses \: as escape)
                import re
                # Split on unescaped colons
                parts = re.split(r'(?<!\\):', line)
                if len(parts) < 6:
                    continue
                
                # Unescape the BSSID (\: -> :)
                bssid = parts[0].replace('\\:', ':')
                ssid = parts[1]
                mode = parts[2]
                channel = parts[3]
                signal = parts[4]
                security = parts[5]

                if not ssid.strip():
                    continue
                
                try:
                    channel_int = int(channel) if channel else 0
                except ValueError:
                    channel_int = 0
                    
                try:
                    signal_int = int(signal) if signal else 0
                except ValueError:
                    signal_int = 0
                
                network = {
                    "bssid": bssid,
                    "ssid": ssid,
                    "mode": mode,
                    "channel": channel_int,
                    "signal": signal_int,
                    "encrypted": security not in ["--", "Open"]
                }
                
                networks.append(network)
            
            # Sort by signal strength
            networks.sort(key=lambda x: x.get("signal", 0), reverse=True)

            unique_networks = []
            seen_ssids = set()
            for network in networks:
                if network["ssid"] in seen_ssids:
                    continue
                seen_ssids.add(network["ssid"])
                unique_networks.append(network)
            
            return {"networks": unique_networks}
        else:
            return {"networks": []}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get WiFi networks: {e}")


@router.post("/wifi/connect")
async def connect_wifi(ssid: str, password: Optional[str] = None):
    """Connect to WiFi network"""
    try:
        import subprocess
        
        # Check if already connected
        result = subprocess.run(
            ["nmcli", "connection", "show", "--active"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if ssid in result.stdout:
            return {"success": True, "message": "Already connected"}
        
        # Connect to network
        if password:
            cmd = ["nmcli", "device", "wifi", "connect", ssid, "password", password]
        else:
            cmd = ["nmcli", "device", "wifi", "connect", ssid]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "ssid": ssid}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to connect: {result.stderr}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to WiFi: {e}")


@router.post("/wifi/disconnect")
async def disconnect_wifi(ssid: Optional[str] = None):
    """Disconnect from WiFi network"""
    try:
        import subprocess
        
        if ssid:
            # Disconnect specific network
            result = subprocess.run(
                ["nmcli", "connection", "down", ssid],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            # Disconnect all WiFi
            result = subprocess.run(
                ["nmcli", "device", "disconnect", "wlan0"],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if result.returncode == 0:
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to disconnect")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect WiFi: {e}")


@router.delete("/wifi/connections")
async def remove_wifi_connection(name: Optional[str] = None, uuid: Optional[str] = None):
    """Remove a saved NetworkManager WiFi profile."""
    if not name and not uuid:
        raise HTTPException(status_code=400, detail="Connection name or UUID is required")

    try:
        import subprocess

        identifier = uuid or name
        result = subprocess.run(
            ["sudo", "-n", "nmcli", "connection", "delete", identifier],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove saved WiFi connection: {result.stderr.strip()}",
            )
        return {"success": True, "name": name, "uuid": uuid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove WiFi connection: {e}")


@router.get("/wifi/status")
async def get_wifi_status():
    """Get WiFi adapter status"""
    try:
        import subprocess
        
        # Get device status
        result = subprocess.run(
            ["nmcli", "device", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            status = {}
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 3:
                    device = parts[0]
                    status[device] = {
                        "type": parts[1],
                        "state": parts[2],
                        "connection": " ".join(parts[3:]) if len(parts) > 3 else None,
                    }
            return {"status": status}
        else:
            return {"status": {}}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get WiFi status: {e}")


@router.post("/wifi/scan")
async def scan_wifi_networks():
    """Trigger WiFi scan"""
    try:
        import subprocess
        result = subprocess.run(
            ["nmcli", "device", "wifi", "list", "--rescan", "yes"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to scan: {result.stderr.strip()}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan WiFi: {e}")


@router.get("/wifi/connections")
async def get_wifi_connections():
    """Get all available WiFi connections"""
    try:
        import subprocess

        # Get a terse, parseable list of connections
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,UUID,TYPE,DEVICE", "connection", "show"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            connections = []

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split(":")
                if len(parts) < 4:
                    continue

                name, uuid, conn_type, device = parts[0], parts[1], parts[2], parts[3]

                # Focus on WiFi profiles for the WiFi UI.
                if conn_type not in ["wifi", "802-11-wireless"]:
                    continue

                connections.append({
                    "name": name,
                    "uuid": uuid,
                    "type": conn_type,
                    "interface": None if device == "--" else device,
                    "ssid": name,
                    "autoconnect": True,
                    "priority": 0,
                })

            return {"connections": connections}
        else:
            return {"connections": []}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get WiFi connections: {e}")


HOTSPOT_CON_NAME = "touchplayer-hotspot"
HOTSPOT_IFNAME = "wlan0"
DEFAULT_HOTSPOT_PASSWORD = "touchplayer123"


@router.get("/wifi/hotspot/status")
async def get_hotspot_status():
    """Get the TouchPlayer hotspot configuration and active state"""
    try:
        import subprocess

        exists = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show"],
            capture_output=True, text=True, timeout=10,
        )
        if HOTSPOT_CON_NAME not in exists.stdout.strip().split("\n"):
            return {"configured": False, "active": False, "ssid": None}

        details = subprocess.run(
            ["nmcli", "-t", "-f", "802-11-wireless.ssid,GENERAL.STATE", "connection", "show", HOTSPOT_CON_NAME],
            capture_output=True, text=True, timeout=10,
        )
        ssid = None
        active = False
        for line in details.stdout.strip().split("\n"):
            if line.startswith("802-11-wireless.ssid:"):
                ssid = line.split(":", 1)[1]
            elif line.startswith("GENERAL.STATE:"):
                active = "activated" in line.lower()

        return {"configured": True, "active": active, "ssid": ssid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hotspot status: {e}")


@router.post("/wifi/hotspot/start")
async def start_hotspot(ssid: str, password: Optional[str] = None):
    """Configure and start a WiFi access point (hotspot) on the WiFi adapter"""
    if not (1 <= len(ssid) <= 32):
        raise HTTPException(status_code=400, detail="SSID must be 1-32 characters")
    password = (password or DEFAULT_HOTSPOT_PASSWORD).strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    try:
        import subprocess

        # Recreate the profile each time so SSID/password changes take effect cleanly.
        # Elevated: creating an AP-mode profile is denied by polkit for a
        # headless service session, unlike ordinary client connect/disconnect.
        subprocess.run(
            ["sudo", "-n", "nmcli", "connection", "delete", HOTSPOT_CON_NAME],
            capture_output=True, text=True, timeout=10,
        )

        cmd = ["sudo", "-n", "nmcli", "device", "wifi", "hotspot", "ifname", HOTSPOT_IFNAME, "con-name", HOTSPOT_CON_NAME, "ssid", ssid]
        cmd += ["password", password]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to start hotspot: {result.stderr.strip()}")

        return {"success": True, "ssid": ssid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start hotspot: {e}")


@router.post("/wifi/hotspot/stop")
async def stop_hotspot():
    """Stop the hotspot; the adapter returns to normal WiFi client mode"""
    try:
        import subprocess
        result = subprocess.run(
            ["sudo", "-n", "nmcli", "connection", "down", HOTSPOT_CON_NAME],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to stop hotspot: {result.stderr.strip()}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop hotspot: {e}")


@router.delete("/wifi/hotspot")
async def delete_hotspot():
    """Stop the hotspot and remove its saved profile"""
    try:
        import subprocess
        subprocess.run(
            ["sudo", "-n", "nmcli", "connection", "down", HOTSPOT_CON_NAME],
            capture_output=True, text=True, timeout=15,
        )
        result = subprocess.run(
            ["sudo", "-n", "nmcli", "connection", "delete", HOTSPOT_CON_NAME],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to remove hotspot: {result.stderr.strip()}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove hotspot: {e}")

