"""
ANT+ Manager for the Heart Rate Monitor App (OpenANT 1.3.3 Compatible)

This module provides a class to manage ANT+ device connections and data processing,
specifically for heart rate monitors. It is optimized to work with the actual
OpenANT 1.3.3 API structure (without the Driver class).
"""

import threading
import time
import traceback
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.clock import Clock

# Check for openant availability and import correctly
try:
    import openant
    from openant.easy.node import Node
    from openant.devices import ANTPLUS_NETWORK_KEY
    
    OPENANT_AVAILABLE = True
    OPENANT_VERSION = getattr(openant, '__version__', 'unknown')
    print(f"Successfully imported OpenANT {OPENANT_VERSION}")
except ImportError as e:
    OPENANT_AVAILABLE = False
    print(f"Failed to import OpenANT: {e}")

class ANTManager(EventDispatcher):
    """
    Manager class for ANT+ heart rate monitors using the openant library.
    Compatible with OpenANT 1.3.3 API structure.
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
        else:
            self.connection_status = f"OpenANT {OPENANT_VERSION} ready"
    
    def find_ant_usb_devices(self):
        """
        Find available ANT+ USB devices manually.
        This method is compatible with OpenANT 1.3.3.
        """
        devices = []
        
        # Try to find USB ANT sticks using PyUSB directly
        try:
            import usb.core
            import usb.util
            
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
                    
                    # Create a simple device object structure for tracking
                    device_info = {
                        'name': f"ANT+ USB Stick ({vendor_id:04x}:{product_id:04x})",
                        'id': f"{vendor_id:04x}{product_id:04x}",
                        'device': device,
                        'vendor_id': vendor_id,
                        'product_id': product_id
                    }
                    devices.append(device_info)
        except Exception as e:
            print(f"Error searching for USB devices: {e}")
        
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
            # Look for ANT+ USB devices using our custom finder
            usb_devices = self.find_ant_usb_devices()
            
            if not usb_devices:
                self.connection_status = "No ANT+ USB devices found"
                self.scanning = False
                return
                
            # Use the first ANT+ USB device found
            usb_device_info = usb_devices[0]
            print(f"Using ANT+ USB device: {usb_device_info['name']}")
            
            # For OpenANT 1.3.3, we directly pass the USB device to Node
            # without using a Driver class (which doesn't exist in this version)
            try:
                # Create a node with the raw USB device
                self.node = Node(usb_device_info['device'])
                self.node.start()
                print("ANT+ node started successfully")
            except Exception as e:
                print(f"Error creating node with USB device, trying default approach: {e}")
                # If direct device passing fails, try without any arguments
                self.node = Node()
                self.node.start()
                print("ANT+ node started with default configuration")
            
            # Set network key
            network = self.node.new_network(key=ANTPLUS_NETWORK_KEY)
            
            # Create a channel for scanning
            channel = self.node.new_channel(network=network, channel_type=0x00)
            
            # Set the channel as a slave (receiving) channel with wildcard search
            channel.set_period(8070)  # Standard heart rate period
            channel.set_search_timeout(10)  # 10 seconds timeout
            channel.set_rf_freq(57)  # ANT+ frequency
            channel.set_id(0, 120, 0)  # Any device, HR type, any transmission type
            
            # Keep track of found devices
            hr_found = False
            
            # Define callback for broadcast data
            def on_device_found(data):
                # Ensure we're still scanning
                if not self.scanning:
                    return
                
                try:
                    # Convert data to a list of integers if it's not already
                    data_bytes = [int(b) for b in data]
                    
                    # Parse heart rate value (typically at byte 7)
                    hr_value = None
                    if len(data_bytes) >= 8:
                        hr_value = data_bytes[7]
                    
                    # For demonstration, assume any device sending data is a heart rate monitor
                    device_number = len(self.discovered_devices) + 1  # Simple numbering
                    
                    # Check if we already have this device (basic duplicate detection)
                    if not any(d.get('last_hr') == hr_value for d in self.discovered_devices[-5:]):
                        device_info = {
                            'name': f"ANT+ HR Monitor {device_number}",
                            'id': device_number,
                            'type': 'heart_rate',
                            'type_id': 120,
                            'last_hr': hr_value
                        }
                        self.discovered_devices.append(device_info)
                        nonlocal hr_found
                        hr_found = True
                        print(f"Found ANT+ HR device: {device_info['name']} ({hr_value} bpm)")
                
                except Exception as e:
                    print(f"Error processing ANT+ device data: {e}")
            
            # Set the callback
            channel.on_broadcast_data = on_device_found
            
            # Open the channel
            channel.open()
            print("ANT+ channel opened for scanning")
            
            # Wait for devices to be found (15 seconds max)
            timeout = time.time() + 15
            while time.time() < timeout and self.scanning:
                if hr_found and len(self.discovered_devices) >= 1:
                    # We found at least one HR monitor, we can stop early
                    if time.time() > timeout - 10:  # But scan at least 5 seconds
                        break
                time.sleep(0.1)
            
            # Clean up
            try:
                channel.close()
                self.node.stop()
            except:
                pass
            
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
            # Try to convert ID to integer if it's a string
            try:
                self._device_id = int(device_id)
            except:
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
            # Find ANT+ USB device using our custom finder
            usb_devices = self.find_ant_usb_devices()
            
            if not usb_devices:
                self.connection_status = "No ANT+ USB devices found"
                return False
                
            usb_device_info = usb_devices[0]
            
            # Create Node - for OpenANT 1.3.3, we pass the device directly
            try:
                self.node = Node(usb_device_info['device'])
            except:
                # Fallback to default if direct device passing doesn't work
                self.node = Node()
            
            # Start the node
            self.node.start()
            
            # Set network key
            self.network = self.node.new_network(key=ANTPLUS_NETWORK_KEY)
            
            # Create a channel for the specific device
            self.channel = self.node.new_channel(network=self.network, channel_type=0x00)
            
            # Set up the channel for the selected device
            self.channel.set_period(8070)  # Standard heart rate period
            self.channel.set_search_timeout(30)  # 30 seconds timeout
            self.channel.set_rf_freq(57)  # ANT+ frequency
            
            # Since we might not have precise device IDs, use wildcard search
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
                try:
                    self.channel.close()
                except:
                    pass
                self.channel = None
                
            if self.node:
                try:
                    self.node.stop()
                except:
                    pass
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
            
            # The heart rate is typically in byte 7 for most pages
            if len(data_bytes) >= 8:
                hr_value = data_bytes[7]
                
                # Update the heart rate property on the main thread
                def update_hr(dt):
                    self.hr_data = hr_value
                
                # Schedule on main thread
                Clock.schedule_once(update_hr)
                
                # Debug output
                print(f"ANT+ HR: {hr_value} bpm")
            
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