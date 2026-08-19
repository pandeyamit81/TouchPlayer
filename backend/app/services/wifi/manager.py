"""
TouchPlayer WiFi Manager
"""
import asyncio
from typing import List, Dict, Any
from loguru import logger


class WiFiManager:
    """WiFi manager service"""
    
    def __init__(self):
        self._running = False
    
    async def run(self):
        """Run the WiFi manager"""
        self._running = True
        logger.info("WiFi manager started")
        
        while self._running:
            try:
                # In a real implementation, this would handle WiFi events
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WiFi manager error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the WiFi manager"""
        self._running = False
    
    async def get_networks(self) -> List[Dict[str, Any]]:
        """Get available WiFi networks"""
        try:
            import subprocess
            result = subprocess.run(
                ["nmcli", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                networks = []
                current_network = {}
                
                for line in result.stdout.strip().split("\n"):
                    if line.startswith("SSID:"):
                        if current_network:
                            networks.append(current_network)
                        current_network = {"ssid": line.split(":", 1)[1].strip()}
                    elif line.startswith("BSSID:"):
                        current_network["bssid"] = line.split(":", 1)[1].strip()
                    elif line.startswith("MODE:"):
                        current_network["mode"] = line.split(":", 1)[1].strip()
                    elif line.startswith("CHAN:"):
                        current_network["channel"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("FREQ:"):
                        current_network["frequency"] = line.split(":", 1)[1].strip()
                    elif line.startswith("RATE:"):
                        current_network["rate"] = line.split(":", 1)[1].strip()
                    elif line.startswith("SIGNAL:"):
                        current_network["signal"] = int(line.split(":", 1)[1].strip().split()[0])
                    elif line.startswith("SECURITY:"):
                        security = line.split(":", 1)[1].strip()
                        current_network["encrypted"] = security != "--"
                
                if current_network:
                    networks.append(current_network)
                
                # Sort by signal strength
                networks.sort(key=lambda x: x.get("signal", 0), reverse=True)
                
                return networks
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get WiFi networks: {e}")
            return []
    
    async def connect(self, ssid: str, password: str = None) -> bool:
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
                return True
            
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
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to connect to WiFi: {e}")
            return False
    
    async def disconnect(self, ssid: str = None) -> bool:
        """Disconnect from WiFi network"""
        try:
            import subprocess
            
            if ssid:
                result = subprocess.run(
                    ["nmcli", "connection", "down", ssid],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                result = subprocess.run(
                    ["nmcli", "device", "disconnect", "wlan0"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to disconnect WiFi: {e}")
            return False
    
    async def status(self) -> Dict[str, Any]:
        """Get WiFi adapter status"""
        try:
            import subprocess
            
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
                return status
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get WiFi status: {e}")
            return {}
    
    async def scan(self) -> bool:
        """Trigger WiFi scan"""
        try:
            import subprocess
            result = subprocess.run(
                ["nmcli", "device", "wifi", "rescan"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to scan WiFi: {e}")
            return False
    
    async def __aenter__(self):
        await self.run()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
