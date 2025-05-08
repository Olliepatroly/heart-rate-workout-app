#!/usr/bin/env python3
"""
ANT+ Tester Application (Fixed Version)

A simple Kivy application to test ANT+ USB stick detection and openant functionality.
This version is compatible with various OpenANT library versions.
"""

import os
import sys
import time
from threading import Thread
import traceback

# Check for openant before importing Kivy
try:
    import openant
    print(f"OpenANT found (version: {getattr(openant, '__version__', 'unknown')})")
    
    # Import core ANT+ functionality
    from openant.easy.node import Node
    from openant.devices import ANTPLUS_NETWORK_KEY
    
    # Import USB device classes directly instead of using find_devices
    from openant.devices import USBDevice, SerialDevice
    
    OPENANT_AVAILABLE = True
except ImportError as e:
    OPENANT_AVAILABLE = False
    print(f"OpenANT import error: {e}")
    print("Please install openant with: pip install openant")

# Import Kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.logger import Logger


class ANTDeviceScanner:
    """Class for scanning and testing ANT+ devices"""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.node = None
        self.channels = []
        self.running = False
        self.scan_thread = None
        self.device_info = {}
        
    def log_message(self, message):
        """Log a message and call the callback if available"""
        print(message)
        if self.callback:
            self.callback(message)
    
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
                    self.log_message(f"Found ANT+ USB device: {vendor_id:04x}:{product_id:04x}")
                    # Create USBDevice instance
                    ant_device = USBDevice(vendor_id, product_id)
                    devices.append(ant_device)
        except Exception as e:
            self.log_message(f"Error searching for USB devices: {e}")
        
        # Also try to find serial devices (some ANT+ devices use serial connections)
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            for port in ports:
                # Try to identify potential ANT+ serial devices
                if "ANT" in port.description or "Garmin" in port.description:
                    self.log_message(f"Found potential ANT+ serial device: {port.device}")
                    ant_device = SerialDevice(port.device)
                    devices.append(ant_device)
        except Exception as e:
            self.log_message(f"Error searching for serial devices: {e}")
        
        return devices
    
    def scan_for_devices(self):
        """Start the scanning thread"""
        if not OPENANT_AVAILABLE:
            self.log_message("ERROR: openant library not found. Install with 'pip install openant'")
            return False
        
        if self.running:
            self.log_message("Scan already in progress.")
            return False
        
        self.running = True
        self.scan_thread = Thread(target=self._scan_worker)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        return True
    
    def stop_scan(self):
        """Stop the scanning process"""
        self.running = False
        if self.node:
            try:
                self.log_message("Stopping ANT+ channels...")
                for channel in self.channels:
                    try:
                        channel.close()
                    except:
                        pass
                self.node.stop()
            except Exception as e:
                self.log_message(f"Error closing ANT+ connection: {e}")
        
        self.node = None
        self.channels = []
        self.log_message("Scan stopped.")
    
    def _scan_worker(self):
        """Worker thread for ANT+ scanning"""
        try:
            self.log_message("Looking for ANT+ USB devices...")
            
            # Get USB device path using our manual finder
            devices = self.find_ant_usb_devices()
            
            if not devices:
                self.log_message("No ANT+ USB devices found. Please connect your ANT+ stick.")
                self.running = False
                return
            
            # Use the first device found
            device = devices[0]
            self.log_message(f"Using ANT+ device: {device}")
            
            # Connect to the device
            self.log_message("Connecting to ANT+ stick...")
            self.node = Node(device)
            self.log_message("Starting ANT+ node...")
            self.node.start()
            
            # Set network key
            self.log_message("Setting network key...")
            network = self.node.new_network(key=ANTPLUS_NETWORK_KEY)
            
            # Get some device-specific info
            try:
                capabilities = self.node.get_capabilities()
                self.device_info['max_channels'] = capabilities.max_channels
                self.device_info['max_networks'] = capabilities.max_networks
                self.device_info['max_sensrcore_channels'] = capabilities.max_sensrcore_channels
                self.device_info['ant_version'] = f"{capabilities.ant_version[0]}.{capabilities.ant_version[1]}"
                
                self.log_message(f"ANT+ device info:")
                for key, value in self.device_info.items():
                    self.log_message(f"  {key}: {value}")
            except Exception as e:
                self.log_message(f"Could not get device capabilities: {e}")
            
            # Listen for heart rate monitors (device type 120)
            self.log_message("Setting up channel to listen for heart rate monitors...")
            channel = self.node.new_channel(network=network, channel_type=0x00)
            self.channels.append(channel)
            
            # Set the channel as a slave (receiving) channel for ANT+ heart rate devices
            channel.set_period(8070)
            channel.set_search_timeout(0)  # Infinite timeout
            channel.set_rf_freq(57)  # ANT+ frequency
            channel.set_id(0, 120, 0)  # Any device, HR type, any transmission type
            
            # Set a callback for received data
            channel.on_broadcast_data = self._on_broadcast_data
            channel.on_burst_data = self._on_burst_data
            
            # Open the channel
            self.log_message("Opening channel...")
            channel.open()
            self.log_message("Channel opened. Listening for ANT+ heart rate data...")
            
            # Keep the worker running for receiving data
            timeout = time.time() + 60  # 60 second timeout
            while self.running and time.time() < timeout:
                time.sleep(0.1)
                
            if time.time() >= timeout and self.running:
                self.log_message("Scan timeout reached (60 seconds). Stopping scan.")
                self.running = False
                
        except Exception as e:
            self.log_message(f"Error during ANT+ scan: {e}")
            traceback.print_exc()
        finally:
            if self.running:
                self.stop_scan()
            self.running = False
    
    def _on_broadcast_data(self, data):
        """Handle broadcast data from ANT+ device"""
        try:
            # Convert to readable format
            data_bytes = [int(b) for b in data]
            
            # For heart rate devices (type 120), first byte after header is typically the heart rate
            # This is a simplified interpretation, actual parsing depends on the device profile
            if len(data_bytes) >= 8:
                hr_value = data_bytes[7]  # Page format varies, this is simplified
                self.log_message(f"ANT+ Broadcast Data: {data_bytes} (HR: {hr_value} bpm)")
        except Exception as e:
            self.log_message(f"Error parsing broadcast data: {e}")
    
    def _on_burst_data(self, data):
        """Handle burst data from ANT+ device"""
        try:
            # Just log the raw data for this simple tester
            data_bytes = [int(b) for b in data]
            self.log_message(f"ANT+ Burst Data: {data_bytes}")
        except Exception as e:
            self.log_message(f"Error parsing burst data: {e}")


class ANTTesterApp(App):
    """Kivy application for testing ANT+ functionality"""
    
    def build(self):
        self.title = "ANT+ Tester App"
        Window.size = (800, 600)
        
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Status section
        status_box = BoxLayout(orientation='vertical', size_hint_y=0.2)
        
        # OpenANT status
        openant_status = "FOUND" if OPENANT_AVAILABLE else "NOT FOUND"
        openant_color = [0.2, 0.8, 0.2, 1] if OPENANT_AVAILABLE else [0.8, 0.2, 0.2, 1]
        
        status_box.add_widget(Label(
            text="OpenANT Library Status:",
            size_hint_y=0.4,
            halign='left',
            text_size=(Window.width, None)
        ))
        
        self.openant_status_label = Label(
            text=f"Status: {openant_status}",
            color=openant_color,
            size_hint_y=0.6,
            halign='left',
            text_size=(Window.width, None)
        )
        status_box.add_widget(self.openant_status_label)
        
        layout.add_widget(status_box)
        
        # USB devices section
        usb_box = BoxLayout(orientation='vertical', size_hint_y=0.2)
        usb_box.add_widget(Label(
            text="USB Device Path:",
            size_hint_y=0.4,
            halign='left',
            text_size=(Window.width, None)
        ))
        
        self.usb_path_label = Label(
            text="Not detected",
            size_hint_y=0.6,
            halign='left',
            text_size=(Window.width, None)
        )
        usb_box.add_widget(self.usb_path_label)
        
        layout.add_widget(usb_box)
        
        # Log output
        log_box = BoxLayout(orientation='vertical', size_hint_y=0.5)
        log_box.add_widget(Label(
            text="Log Output:",
            size_hint_y=0.1,
            halign='left',
            text_size=(Window.width, None)
        ))
        
        # Scrollable log area
        scroll_view = ScrollView(size_hint_y=0.9)
        self.log_output = TextInput(
            text="",
            readonly=True,
            multiline=True,
            size_hint=(1, None),
            height=Window.height * 0.4
        )
        scroll_view.add_widget(self.log_output)
        log_box.add_widget(scroll_view)
        
        layout.add_widget(log_box)
        
        # Buttons
        button_box = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)
        
        self.scan_button = Button(
            text="Scan for ANT+ Devices",
            disabled=not OPENANT_AVAILABLE
        )
        self.scan_button.bind(on_press=self.start_scan)
        button_box.add_widget(self.scan_button)
        
        self.stop_button = Button(
            text="Stop Scan",
            disabled=True
        )
        self.stop_button.bind(on_press=self.stop_scan)
        button_box.add_widget(self.stop_button)
        
        layout.add_widget(button_box)
        
        # Initialize scanner
        self.scanner = ANTDeviceScanner(callback=self.update_log)
        
        # Automatically check for USB devices
        Clock.schedule_once(self.check_usb_devices, 1)
        
        return layout
    
    def check_usb_devices(self, dt):
        """Check for ANT+ USB devices at startup"""
        if not OPENANT_AVAILABLE:
            self.update_log("OpenANT library not found. Cannot check for USB devices.")
            self.usb_path_label.text = "Cannot check (openant not found)"
            return
        
        try:
            # Use our manual device finder instead of the find_devices function
            devices = self.scanner.find_ant_usb_devices()
            
            if devices:
                self.usb_path_label.text = f"Found: {devices[0]}"
                self.usb_path_label.color = [0.2, 0.8, 0.2, 1]
                self.update_log(f"Found ANT+ USB device: {devices[0]}")
            else:
                self.usb_path_label.text = "No ANT+ USB devices found"
                self.usb_path_label.color = [0.8, 0.2, 0.2, 1]
                self.update_log("No ANT+ USB devices found. Please connect your ANT+ stick.")
                
        except Exception as e:
            self.usb_path_label.text = f"Error: {str(e)}"
            self.usb_path_label.color = [0.8, 0.2, 0.2, 1]
            self.update_log(f"Error checking USB devices: {e}")
    
    def update_log(self, message):
        """Update the log output with a new message"""
        def update_log_text(*args):
            self.log_output.text += f"{message}\n"
            # Scroll to bottom
            self.log_output.cursor = (0, len(self.log_output.text))
        
        # Run on the main thread
        Clock.schedule_once(update_log_text)
    
    def start_scan(self, instance):
        """Start scanning for ANT+ devices"""
        if self.scanner.scan_for_devices():
            self.scan_button.disabled = True
            self.stop_button.disabled = False
            self.update_log("Starting ANT+ scan...")
    
    def stop_scan(self, instance):
        """Stop scanning for ANT+ devices"""
        self.scanner.stop_scan()
        self.scan_button.disabled = False
        self.stop_button.disabled = True
    
    def on_stop(self):
        """Clean up when the app is closed"""
        self.scanner.stop_scan()


if __name__ == "__main__":
    try:
        ANTTesterApp().run()
    except Exception as e:
        print(f"Error running ANT+ Tester: {e}")
        traceback.print_exc()