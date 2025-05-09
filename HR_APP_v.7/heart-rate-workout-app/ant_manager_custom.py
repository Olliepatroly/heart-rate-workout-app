"""
ANT+ Manager for the Heart Rate Monitor App (Custom for OpenANT 1.3.3)

This module provides a class to manage ANT+ device connections and data processing,
specifically for heart rate monitors. It is optimized for OpenANT version 1.3.3
and is designed to integrate with the main Kivy heart rate application.
"""

import threading
import time
import traceback
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.clock import Clock

# Check for openant availability
try:
    import openant_wrapper
    from openant_wrapper import Node, ANTPLUS_NETWORK_KEY, Driver
    OPENANT_AVAILABLE = openant_wrapper.is_available()
        
    OPENANT_AVAILABLE = True
except ImportError:
    OPENANT_AVAILABLE = False

class ANTManager(EventDispatcher):
    """
    Manager class for ANT+ heart rate monitors using the openant library.
    Customized for OpenANT 1.3.3 and implements a similar interface to BluetoothManager
    for compatibility with the main application.
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
        self.driver = None
        
        # Check if openant is available
        if not OPENANT_AVAILABLE:
            self.connection_status = "OpenANT library not found. Install with 'pip install openant'"
        else:
            self.connection_status = f"OpenANT {getattr(openant_wrapper, '__version__', 'unknown')} ready"
    
    def find_ant_usb_devices(self):
        """
        Find available ANT+ USB devices manually.
        This method is customized for OpenANT 1.3.3 which doesn't have the find_devices function.
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
            
            # Create a Driver with the USB device
            self.driver = Driver(usb_device_info['device'])
            
            # Create a temporary node for scanning
            temp_node = Node(self.driver)
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
                    
                    # Extract information from the extended message
                    # In ANT+ protocol, broadcast data from a heart rate monitor typically
                    # has the device number at a specific position in the message
                    
                    # The device number is usually part of the message (position varies by format)
                    device_number = None
                    device_type = None
                    
                    # Try to get extended info if available
                    if len(data_bytes) >= 12:
                        device_number = data_bytes[10]
                        device_type = data_bytes[9]
                    
                    # Parse heart rate value
                    hr_value = None
                    if len(data_bytes) >= 8:
                        hr_value = data_bytes[7]
                    
                    if device_number is not None and device_type == 120:  # heart rate profile = 120
                        # Check if we already have this device
                        if not any(d.get('id') == device_number for d in self.discovered_devices):
                            device_info = {
                                'name': f"ANT+ HR Monitor {device_number}",
                                'id': device_number,
                                'type': 'heart_rate',
                                'type_id': device_type,
                                'last_hr': hr_value
                            }
                            self.discovered_devices.append(device_info)
                            nonlocal hr_found
                            hr_found = True
                            print(f"Found ANT+ HR device: {device_info['name']} ({hr_value} bpm)")
                        
                        # Update the device with the latest heart rate
                        for device in self.discovered_devices:
                            if device.get('id') == device_number:
                                device['last_hr'] = hr_value
                                break
                except Exception as e:
                    print(f"Error processing ANT+ device data: {e}")
            
            # Set the callback
            channel.on_broadcast_data = on_device_found
            
            # Open the channel
            channel.open()
            
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
                temp_node.stop()
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
            
            # Create Driver and Node
            self.driver = Driver(usb_device_info['device'])
            self.node = Node(self.driver)
            
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