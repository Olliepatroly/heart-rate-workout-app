import asyncio
import platform
import time
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from async_utils import safe_create_task

# Standard Bluetooth GATT UUIDs
HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_CHARACTERISTIC_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
DEVICE_INFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"

class BluetoothManager(EventDispatcher):
    """
    Manager class for Bluetooth LE heart rate monitors using Bleak library.
    Uses asyncio for handling BLE operations and integrates with Kivy's event loop.
    """
    connected = BooleanProperty(False)
    scanning = BooleanProperty(False)
    hr_data = NumericProperty(0)
    battery_level = NumericProperty(0)
    device_name = StringProperty("")
    connection_status = StringProperty("Not connected")

    def __init__(self, **kwargs):
        super(BluetoothManager, self).__init__(**kwargs)
        self.client = None
        self.discovered_devices = []
        self.loop = asyncio.get_event_loop()
        self._scan_task = None
        self._connection_task = None
        self._device_address = None

    def start_scan(self):
        """Start scanning for BLE heart rate monitors"""
        if self.scanning:
            return

        self.scanning = True
        self.connection_status = "Scanning for devices..."
        self.discovered_devices = []
        
        try:
            # Get or create an event loop if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                # No running event loop - create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Create a new task for scanning with better error handling
            self._scan_task = loop.create_task(self._scan())
        except Exception as e:
            print(f"Error starting scan: {e}")
            import traceback
            traceback.print_exc()
            self.scanning = False
            self.connection_status = f"Scan error: {str(e)}"

    async def _scan(self):
        """Internal method to scan for BLE devices with heart rate service"""
        try:
            # Safer scanning approach with better error handling
            self.connection_status = "Starting Bluetooth scan..."
            print("Starting Bluetooth scan...")
            
            # First attempt a general scan without filtering by service
            devices = await BleakScanner.discover(timeout=5.0)
            print(f"Scan completed, found {len(devices)} devices")
            
            # Filter and store devices
            self.discovered_devices = []
            for device in devices.values():
                # Store all devices but mark heart rate ones
                # This approach is more reliable than filtering during scan
                device_info = {
                    "name": device.name or "Unknown Device",
                    "address": device.address,
                    "is_hr_device": False
                }
                
                # Try to determine if it might be a heart rate device
                if device.name and any(term in device.name.lower() for term in 
                                       ["heart", "hr", "pulse", "band", "watch", "monitor", "polar", "garmin", "wahoo"]):
                    device_info["is_hr_device"] = True
                
                self.discovered_devices.append(device_info)
                print(f"Found device: {device.name} ({device.address})")

        except Exception as e:
            print(f"Scan error: {e}")
            import traceback
            traceback.print_exc()
            self.connection_status = f"Scan error: {e}"
        finally:
            self.scanning = False
            if not self.discovered_devices:
                self.connection_status = "No devices found"
            else:
                hr_devices = [d for d in self.discovered_devices if d["is_hr_device"]]
                if hr_devices:
                    self.connection_status = f"Found {len(hr_devices)} potential HR devices"
                else:
                    self.connection_status = f"Found {len(self.discovered_devices)} devices (no HR monitors identified)"

    def get_discovered_devices(self):
        """Return list of discovered heart rate devices"""
        return self.discovered_devices

    def connect(self, device_address=None):
        """Connect to a heart rate monitor by address"""
        if self.connected:
            return True

        if device_address:
            self._device_address = device_address
        elif not self._device_address and self.discovered_devices:
            # If no address specified and we have discovered devices, use the first one
            self._device_address = self.discovered_devices[0]["address"]
        
        if not self._device_address:
            self.connection_status = "No device selected"
            return False

        self.connection_status = "Connecting..."
        
        try:
            # Get or create an event loop if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                # No running event loop - create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Create connection task
            self._connection_task = loop.create_task(self._connect())
            return True
        except Exception as e:
            print(f"Error initiating connection: {e}")
            import traceback
            traceback.print_exc()
            self.connection_status = f"Connection error: {str(e)}"
            return False

    async def _connect(self):
        """Internal method to establish connection and set up notifications"""
        try:
            self.client = BleakClient(self._device_address)
            await self.client.connect()
            
            if self.client.is_connected:
                # Get device name
                for device in self.discovered_devices:
                    if device["address"] == self._device_address:
                        self.device_name = device["name"]
                        break
                
                # Start heart rate notifications
                await self.client.start_notify(
                    HEART_RATE_CHARACTERISTIC_UUID, 
                    self._heart_rate_changed
                )
                
                # Get battery level if available
                try:
                    battery_data = await self.client.read_gatt_char(BATTERY_CHARACTERISTIC_UUID)
                    self.battery_level = battery_data[0]
                except Exception:
                    self.battery_level = 0
                
                self.connected = True
                self.connection_status = "Connected"
                return True
            else:
                self.connection_status = "Connection failed"
                return False
        
        except Exception as e:
            print(f"Connection error: {e}")
            self.connection_status = f"Connection error: {str(e)}"
            return False

    def disconnect(self):
        """Disconnect from heart rate monitor"""
        if not self.connected:
            return True

        try:
            # Get or create an event loop if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                # No running event loop - create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Create disconnect task
            self._connection_task = loop.create_task(self._disconnect())
            return True
        except Exception as e:
            print(f"Error initiating disconnect: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _disconnect(self):
        """Internal method to disconnect from the device"""
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            
            self.connected = False
            self.hr_data = 0
            self.connection_status = "Disconnected"
            return True
        
        except Exception as e:
            print(f"Disconnect error: {e}")
            return False
    def set_discovery_callback(self, callback):
        """
        Set a callback function to be called when devices are discovered.
        The callback will receive the list of discovered devices.
        """
        self._discovery_callback = callback

    def _notify_discovery(self):
        """
        Notify the discovery callback about found devices.
        Should be called whenever the discovered_devices list is updated.
        """
        if hasattr(self, '_discovery_callback') and callable(self._discovery_callback):
            self._discovery_callback(self.discovered_devices)
    # Updated handle_device_found method with callback notification
    def handle_device_found(self, device, advertisement_data):
        """Handle discovered Bluetooth device"""
        # Extract device info - keep the same logic you already have
        address = device.address
        name = device.name or "Unknown Device"
        
        # If the device isn't already in the discovered devices list, add it
        if not any(d['address'] == address for d in self.discovered_devices):
            device_info = {
                'address': address,
                'name': name,
                'rssi': advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else None
            }
            self.discovered_devices.append(device_info)
            print(f"Found Bluetooth device: {name} ({address})")
            
            # Notify about the updated device list
            self._notify_discovery()

    def integrate_with_main_app(self, app):
        """
        Integrate the BluetoothManager with the main app.
        This adds direct callbacks to ensure the UI is updated when devices are found.
        """
        # Store the app reference
        self.app = app
        
        # Set up a discovery callback
        def on_devices_discovered(devices):
            print(f"Discovery callback: {len(devices)} devices found")
            # Schedule UI update after device discovery
            from kivy.clock import Clock
            Clock.schedule_once(app.update_device_list, 0.1)
        
        # Set the discovery callback
        self.set_discovery_callback(on_devices_discovered)
        
        # Add scanning state callback
        def on_scanning_changed(instance, value):
            if not value:  # Scanning finished
                print("Scanning completed, updating device list")
                Clock.schedule_once(app.update_device_list, 0.5)
        
        # Bind to scanning property
        self.bind(scanning=on_scanning_changed)
    
    def is_connected(self):
        """Check if currently connected to a heart rate monitor"""
        return self.connected

    def get_heart_rate(self):
        """Get the current heart rate value"""
        return self.hr_data

    def get_battery_level(self):
        """Get the current battery level if available"""
        return self.battery_level

    def get_device_name(self):
        """Get the connected device name"""
        return self.device_name

    def _heart_rate_changed(self, sender, data):
        """Callback for heart rate characteristic notifications"""
        # Parse heart rate measurement according to Bluetooth GATT spec
        flags = data[0]
        
        if flags & 0x01:  # Heart Rate Value Format bit (0 = UINT8, 1 = UINT16)
            # 16-bit format
            hr_value = int.from_bytes([data[1], data[2]], byteorder='little')
        else:
            # 8-bit format
            hr_value = data[1]
        
        # Update the heart rate property - will trigger UI updates
        self.hr_data = hr_value
        
        # You could extract additional information if present:
        # - Contact status (flags bit 1)
        # - Energy expended (flags bit 3)
        # - RR intervals (flags bit 4)
        
        # Example for extracting contact status:
        if flags & 0x02:  # Contact status bit
            contact_detected = (flags & 0x04) != 0
            # You could handle contact status here

    def create_debug_hr_updates(self, active=True):
        """
        Create simulated heart rate updates for debugging
        when no actual hardware is available
        """
        if active:
            Clock.schedule_interval(self._simulate_hr_update, 1.0)
            self.connected = True
            self.device_name = "Simulated HR Monitor"
            self.connection_status = "Connected (Simulated)"
        else:
            Clock.unschedule(self._simulate_hr_update)
            self.connected = False
            self.hr_data = 0
            self.connection_status = "Disconnected"
    
    def _simulate_hr_update(self, dt):
        """Generate simulated heart rate data"""
        import random
        base_hr = 70
        variation = 10
        self.hr_data = random.randint(base_hr - variation, base_hr + variation)
        
        # Occasionally simulate exercise with higher heart rate
        if random.random() < 0.1:
            self.hr_data += random.randint(10, 30)