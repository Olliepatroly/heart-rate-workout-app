"""
ANT+ Manager for the Heart Rate Monitor App (Fixed Version)

This module provides a class to manage ANT+ device connections and data processing,
particularly for heart rate monitors. It is designed to be used with the Kivy application.
This version is compatible with various OpenANT library versions.
"""

import threading
import time
import traceback
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.clock import Clock

# Check for openant availability
try:
    import openant
    from openant.easy.node import Node
    from openant.devices import ANTPLUS_NETWORK_KEY
    
    # Import USB device classes directly instead of using find_devices
    from openant.devices import USBDevice, SerialDevice
    
    OPENANT_AVAILABLE = True
except ImportError:
    OPENANT_AVAILABLE = False

class ANTManager(EventDispatcher):
    """
    Manager class for ANT+ heart rate monitors using the openant library.
    Implements a similar interface to BluetoothManager for compatibility.
    """
    connected = BooleanProperty(False)
    scanning = BooleanProperty(False)
    hr_data = NumericProperty(0)
    battery_level = NumericProperty(0)
    device_name = StringProperty("")
    connection_status = StringProperty("Not connected")
    
    def __init__(self, **kwargs):
        super(ANTManager, self).__init__(**kwargs)
        self.node = None
        self.channel = None
        self.network = None
        self.discovered_devices = []
        self._scan_thread = None
        self._listen_thread = None
        self._device_id = None
        self.running = False
        
        # Check if openant is available
        if not OPENANT_AVAILABLE:
            self.connection_status = "OpenANT library not found. Install with 'pip install openant'"
    
    def find_ant_usb_devices(self):
        """
        Find available ANT+ USB devices manually.
        This method replaces the find_devices() function that may not be available in all OpenANT versions.
        """
        devices = []
        
        # Try to find USB ANT sticks
        try:
            import usb.core
            # Garmin/Dynastream ANT+ USB stick vendor/product IDs
            ant_ids = [
                (0x0fcf, 0x1004),  # ANT+ USB stick
                (0x0fcf, 0x1008),  # ANT+ USB2 stick
                (0x0fcf, 0x1009),  # ANT+ USB-m stick
            ]
            
            for vendor_id, product_id in ant_ids:
                device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
                if device:
                    print(f"Found ANT+ USB device: {vendor_id:04x}:{product_id:04x}")
                    # Create USBDevice instance
                    ant_device = USBDevice(vendor_id, product_id)
                    devices.append(ant_device)
        except Exception as e:
            print(f"Error searching for USB devices: {e}")
        
        # Also try to find serial devices (some ANT+ devices use serial connections)
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            for port in ports:
                # Try to identify potential ANT+ serial devices
                if "ANT" in port.description or "Garmin" in port.description:
                    print(f"Found potential ANT+ serial device: {port.device}")
                    ant_device = SerialDevice(port.device)
                    devices.append(ant_device)
        except Exception as e:
            print(f"Error searching for serial devices: {e}")
        
        return devices
    
    def start_scan(self):
        """Start scanning for ANT+ heart rate monitors"""
        if not OPENANT_AVAILABLE:
            self.connection_status = "OpenANT library not found"
            return False
            
        if self.scanning:
            return False

        self.scanning = True
        self.connection_status = "Scanning for ANT+ devices..."
        self.discovered_devices = []
        
        # Create a thread for scanning to avoid blocking the UI
        self._scan_thread = threading.Thread(target=self._scan)
        self._scan_thread.daemon = True
        self._scan_thread.start()
        return True
    
    def _scan(self):
        """Internal method to scan for ANT+ devices"""
        try:
            # Look for ANT+ USB devices using our manual finder
            usb_devices = self.find_ant_usb_devices()
            
            if not usb_devices:
                self.connection_status = "No ANT+ USB devices found"
                self.scanning = False
                return
                
            # Use the first ANT+ USB device found
            usb_device = usb_devices[0]
            print(f"Using ANT+ USB device: {usb_device}")
            
            # Create a temporary node for scanning
            temp_node = Node(usb_device)
            temp_node.start()
            
            # Set network key
            network = temp_node.new_network(key=ANTPLUS_NETWORK_KEY)
            
            # Create a channel for scanning
            channel = temp_node.new_channel(network=network, channel_type=0x00)
            
            # Set the channel as a slave (receiving) channel with wildcard search
            channel.set_period(8070)  # Standard heart rate period
            channel.set_search_timeout(10)  # 10 seconds timeout
            channel.set_rf_freq(57)  # ANT+ frequency
            channel.set_id(0, 120, 0)  # Any device, HR type, any transmission type
            
            # Set a callback for found devices
            self.found_devices = []
            
            def on_device_found(data):
                # Extract device ID from the data
                try:
                    # Parse data based on ANT+ protocol
                    # For heart rate devices, the device ID is typically in a specific location
                    # in the broadcast message - this may need adjustment
                    device_id = None
                    device_type = None
                    
                    # Convert data to a list of integers if it's not already
                    data_bytes = [int(b) for b in data]
                    
                    # Check if this appears to be a heart rate broadcast
                    # The device type is typically at index 9 in the extended message
                    if len(data_bytes) >= 12:
                        device_type = data_bytes[9] if data_bytes[9] == 120 else None
                        device_id = data_bytes[10] if device_type == 120 else None
                    
                    if device_id is not None and device_type == 120:  # Heart rate device
                        # Check if we've already found this device
                        if not any(d.get('id') == device_id for d in self.discovered_devices):
                            device_info = {
                                'name': f"ANT+ HR Monitor {device_id}",
                                'id': device_id,
                                'type': device_type
                            }
                            self.discovered_devices.append(device_info)
                            print(f"Found ANT+ device: {device_info}")
                except Exception as e:
                    print(f"Error parsing device data: {e}")
            
            channel.on_broadcast_data = on_device_found
            
            # Open the channel for scanning
            channel.open()
            
            # Scan for devices for 10 seconds
            timeout = time.time() + 10
            while time.time() < timeout and self.scanning:
                time.sleep(0.1)
            
            # Clean up
            channel.close()
            temp_node.stop()
            
        except Exception as e:
            print(f"ANT+ scan error: {e}")
            traceback.print_exc()
            self.connection_status = f"Scan error: {str(e)}"
        finally:
            self.scanning = False
            if not self.discovered_devices:
                self.connection_status = "No ANT+ heart rate monitors found"
            else:
                self.connection_status = f"Found {len(self.discovered_devices)} ANT+ devices"
    
    def get_discovered_devices(self):
        """Return list of discovered ANT+ heart rate devices"""
        return self.discovered_devices
    
    def connect(self, device_id=None):
        """Connect to an ANT+ heart rate monitor by ID"""
        if not OPENANT_AVAILABLE:
            self.connection_status = "OpenANT library not found"
            return False
            
        if self.connected:
            return True

        if device_id:
            self._device_id = device_id
        elif not self._device_id and self.discovered_devices:
            # If no ID specified and we have discovered devices, use the first one
            self._device_id = self.discovered_devices[0]['id']
        
        if not self._device_id:
            self.connection_status = "No device selected"
            return False

        self.connection_status = "Connecting to ANT+ device..."
        
        # Create a thread for connection to avoid blocking the UI
        self._listen_thread = threading.Thread(target=self._connect)
        self._listen_thread.daemon = True
        self._listen_thread.start()
        return True
    
    def _connect(self):
        """Internal method to establish connection and set up ANT+ channel"""
        try:
            # Find ANT+ USB device using our manual finder
            usb_devices = self.find_ant_usb_devices()
            
            if not usb_devices:
                self.connection_status = "No ANT+ USB devices found"
                return False
                
            usb_device = usb_devices[0]
            
            # Create node and start it
            self.node = Node(usb_device)
            self.node.start()
            
            # Set network key
            self.network = self.node.new_network(key=ANTPLUS_NETWORK_KEY)
            
            # Create a channel for the specific device
            self.channel = self.node.new_channel(network=self.network, channel_type=0x00)
            
            # Set up the channel for the selected device
            self.channel.set_period(8070)  # Standard heart rate period
            self.channel.set_search_timeout(30)  # 30 seconds timeout
            self.channel.set_rf_freq(57)  # ANT+ frequency
            
            # If we have a specific device ID, use it. Otherwise, search for any HR monitor
            if self._device_id:
                self.channel.set_id(self._device_id, 120, 0)  # Specific device, HR type, any transmission type
            else:
                self.channel.set_id(0, 120, 0)  # Any device, HR type, any transmission type
            
            # Set callbacks for data
            self.channel.on_broadcast_data = self._on_broadcast_data
            
            # Open the channel
            self.channel.open()
            self.running = True
            
            # Update connection status
            for device in self.discovered_devices:
                if device.get('id') == self._device_id:
                    self.device_name = device.get('name', f"ANT+ HR Monitor {self._device_id}")
                    break
            else:
                self.device_name = f"ANT+ HR Monitor {self._device_id}"
            
            self.connection_status = "Connected"
            self.connected = True
            
            # Keep thread running to receive data
            while self.running:
                time.sleep(0.1)
                
            return True
            
        except Exception as e:
            print(f"ANT+ connection error: {e}")
            traceback.print_exc()
            self.connection_status = f"Connection error: {str(e)}"
            return False
    
    def disconnect(self):
        """Disconnect from ANT+ heart rate monitor"""
        if not self.connected:
            return True

        try:
            self.running = False
            
            if self.channel:
                self.channel.close()
                self.channel = None
                
            if self.node:
                self.node.stop()
                self.node = None
            
            self.connected = False
            self.hr_data = 0
            self.connection_status = "Disconnected"
            return True
            
        except Exception as e:
            print(f"ANT+ disconnect error: {e}")
            return False
    
    def is_connected(self):
        """Check if currently connected to an ANT+ heart rate monitor"""
        return self.connected
    
    def get_heart_rate(self):
        """Get the current heart rate value"""
        return self.hr_data
    
    def _on_broadcast_data(self, data):
        """Process broadcast data from ANT+ heart rate monitor"""
        try:
            # Convert data to a list of integers if it's not already
            data_bytes = [int(b) for b in data]
            
            # Process heart rate data from ANT+ broadcast
            # For heart rate devices, the data format follows the ANT+ HR profile
            
            # Check if this is a heart rate data page (different pages have different formats)
            # The heart rate is typically in byte 7 for most pages
            if len(data_bytes) >= 8:
                hr_value = data_bytes[7]
                
                # Update the heart rate property
                def update_hr(dt):
                    self.hr_data = hr_value
                
                # Schedule on main thread
                Clock.schedule_once(update_hr)
                
                # Debug output
                print(f"ANT+ HR: {hr_value} bpm - data: {data_bytes}")
            
        except Exception as e:
            print(f"Error processing ANT+ heart rate data: {e}")
    
    def create_debug_hr_updates(self, active=True):
        """
        Create simulated heart rate updates for debugging
        when no actual hardware is available
        """
        if active:
            Clock.schedule_interval(self._simulate_hr_update, 1.0)
            self.connected = True
            self.device_name = "Simulated ANT+ HR Monitor"
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