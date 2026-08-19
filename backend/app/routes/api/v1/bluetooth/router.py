"""
TouchPlayer Bluetooth API Routes
Bluetooth device management endpoints
"""
from fastapi import APIRouter, HTTPException

from app.services.bluetooth.manager import BluetoothManager

router = APIRouter()


@router.get("/bluetooth/devices")
async def get_bluetooth_devices():
    """Get paired Bluetooth devices"""
    try:
        import subprocess
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            connected_result = subprocess.run(
                ["bluetoothctl", "devices", "Connected"],
                capture_output=True,
                text=True,
                timeout=10
            )
            paired_result = subprocess.run(
                ["bluetoothctl", "devices", "Paired"],
                capture_output=True,
                text=True,
                timeout=10
            )

            connected_addresses = {
                line.split()[1]
                for line in connected_result.stdout.strip().split("\n")
                if len(line.split()) >= 2
            }
            paired_addresses = {
                line.split()[1]
                for line in paired_result.stdout.strip().split("\n")
                if len(line.split()) >= 2
            }
            devices = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        address = parts[1]
                        devices.append({
                            "address": address,
                            "name": " ".join(parts[2:]) if len(parts) > 2 else "",
                            "connected": address in connected_addresses,
                            "paired": address in paired_addresses,
                        })
            return {"devices": devices}
        else:
            return {"devices": []}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Bluetooth devices: {e}")


@router.post("/bluetooth/scan")
async def start_bluetooth_scan():
    """Start Bluetooth device scan"""
    try:
        import subprocess
        result = subprocess.run(
            ["bluetoothctl", "--timeout", "8", "scan", "on"],
            capture_output=True,
            text=True,
            timeout=12
        )
        
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        # bluetoothctl behavior varies by adapter state and can report
        # partial success via stdout/stderr while still returning non-zero.
        if result.returncode == 0 or "SetDiscoveryFilter success" in stdout or "Discovery started" in stdout or "InProgress" in stderr:
            return {"success": True, "message": "Scan completed"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to start scan: {stderr or stdout}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Bluetooth scan: {e}")


@router.post("/bluetooth/connect/{address}")
async def connect_bluetooth_device(address: str):
    """Connect to Bluetooth device"""
    try:
        manager = BluetoothManager()
        manager._validate_address(address)
        if manager._is_connected(address):
            manager._trust_device(address)
            manager._remember_device(address)
            return {"success": True, "address": address, "message": "Already connected"}
        if await manager.connect(address):
            return {"success": True, "address": address}
        raise HTTPException(status_code=500, detail="Failed to connect")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to device: {e}")


@router.post("/bluetooth/disconnect/{address}")
async def disconnect_bluetooth_device(address: str):
    """Disconnect from Bluetooth device"""
    try:
        if await BluetoothManager().disconnect(address):
            return {"success": True, "address": address}
        raise HTTPException(status_code=500, detail="Failed to disconnect")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect device: {e}")


@router.post("/bluetooth/remove/{address}")
async def remove_bluetooth_device(address: str):
    """Remove paired Bluetooth device"""
    try:
        import subprocess
        result = subprocess.run(
            ["bluetoothctl", "remove", address],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {"success": True, "address": address}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove device")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove device: {e}")


@router.get("/bluetooth/status")
async def get_bluetooth_status():
    """Get Bluetooth adapter status"""
    try:
        import subprocess
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
            return {"status": status}
        else:
            return {"status": {}}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Bluetooth status: {e}")
