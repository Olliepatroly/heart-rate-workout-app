#!/usr/bin/env python3
"""
Bluetooth Device Detection Debugger

This tool helps diagnose issues with Bluetooth device detection and UI display.
It checks the BluetoothManager functionality and verifies the connection to the UI.
"""

import os
import sys
import importlib.util
import traceback
import time

def import_bluetooth_manager():
    """Import the BluetoothManager from the current directory or path"""
    try:
        # Try direct import first
        try:
            from bluetooth_manager import BluetoothManager
            print("Successfully imported BluetoothManager directly")
            return BluetoothManager
        except ImportError:
            pass
        
        # Try to find the file manually
        bt_manager_path = None
        for root, dirs, files in os.walk('.', topdown=True):
            if 'bluetooth_manager.py' in files:
                bt_manager_path = os.path.join(root, 'bluetooth_manager.py')
                print(f"Found bluetooth_manager.py at: {bt_manager_path}")
                break
        
        if bt_manager_path:
            # Load the module
            spec = importlib.util.spec_from_file_location("bluetooth_manager", bt_manager_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"Successfully loaded BluetoothManager from {bt_manager_path}")
            return module.BluetoothManager
        else:
            print("Could not find bluetooth_manager.py")
            return None
        
    except Exception as e:
        print(f"Error importing BluetoothManager: {e}")
        traceback.print_exc()
        return None

def test_bluetooth_scanning():
    """Test direct Bluetooth scanning functionality"""
    print("=== Testing Bluetooth Scanning ===")
    
    BluetoothManager = import_bluetooth_manager()
    if not BluetoothManager:
        print("Failed to import BluetoothManager")
        return
    
    # Create instance
    print("Creating BluetoothManager instance...")
    bt_manager = BluetoothManager()
    
    # Set up callback to see real-time results
    def discovery_callback(devices):
        print(f"Callback received {len(devices)} devices:")
        for i, device in enumerate(devices):
            print(f"  {i+1}. {device.get('name', 'Unknown')} ({device.get('address', 'Unknown')})")
    
    # Check if there's a callback registry method
    if hasattr(bt_manager, 'set_discovery_callback'):
        print("Setting discovery callback...")
        bt_manager.set_discovery_callback(discovery_callback)
    else:
        print("No discovery callback method found, will check manually")
    
    # Start scan
    print("\nStarting Bluetooth scan...")
    bt_manager.start_scan()
    
    # Wait for scan to complete (checking every second)
    print("Waiting for scan to complete...")
    max_wait = 30  # seconds
    for i in range(max_wait):
        if not bt_manager.scanning:
            break
        time.sleep(1)
        # Check intermediate results
        if i % 5 == 0 and i > 0:
            devices = bt_manager.get_discovered_devices()
            print(f"Found {len(devices)} devices so far...")
    
    # Get final results
    devices = bt_manager.get_discovered_devices()
    print(f"\nScan complete! Found {len(devices)} devices.")
    
    # Print detailed device information
    if devices:
        print("\nDetailed device information:")
        for i, device in enumerate(devices):
            print(f"Device {i+1}:")
            for key, value in device.items():
                print(f"  {key}: {value}")
    else:
        print("No devices found.")
    
    # Check device format compatibility
    print("\nChecking device format compatibility with UI...")
    try:
        from device_selection_fix import format_device_list_for_spinner
        formatted_devices = format_device_list_for_spinner(devices, 'bluetooth')
        print(f"Formatted {len(formatted_devices)} devices for UI:")
        for i, formatted in enumerate(formatted_devices):
            print(f"  {i+1}. {formatted}")
    except ImportError:
        print("Could not import device_selection_fix module. UI formatting check skipped.")
    except Exception as e:
        print(f"Error formatting devices for UI: {e}")
        traceback.print_exc()
    
    return devices

def check_event_binding():
    """Check if event binding is properly set up in main.py"""
    print("\n=== Checking Event Binding in Main App ===")
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
            # Look for binding logic
            binding_patterns = [
                "bt_manager.bind(",
                "update_device_list",
                ".scanning",
                "connection_status",
            ]
            
            for pattern in binding_patterns:
                if pattern in content:
                    print(f"✓ Found '{pattern}' in main.py")
                else:
                    print(f"✗ Could not find '{pattern}' in main.py")
            
            # Check for specific device list update code
            if "self.device_spinner.values" in content:
                print("✓ Found code to update device_spinner values")
            else:
                print("✗ Could not find code to update device_spinner values")
    except FileNotFoundError:
        print("main.py not found in current directory")
    except Exception as e:
        print(f"Error checking main.py: {e}")

def check_update_method():
    """Check if the update_device_list method is working correctly"""
    print("\n=== Checking Update Device List Method ===")
    
    try:
        # Try to find the method in main.py
        with open('main.py', 'r') as f:
            content = f.read()
            
            if "def update_device_list" in content:
                print("✓ Found update_device_list method in main.py")
                
                # Check key parts of the method
                checks = [
                    ("gets devices", "get_discovered_devices()"),
                    ("updates spinner values", "device_spinner.values"),
                    ("handles empty device list", "No devices found"),
                    ("has error handling", "except Exception"),
                ]
                
                for name, pattern in checks:
                    if pattern in content:
                        print(f"  ✓ Method {name}")
                    else:
                        print(f"  ✗ Method may not {name}")
            else:
                print("✗ Could not find update_device_list method in main.py")
    except FileNotFoundError:
        print("main.py not found in current directory")
    except Exception as e:
        print(f"Error checking update_device_list method: {e}")

def verify_device_spinner():
    """Check if the device_spinner widget is properly created"""
    print("\n=== Checking Device Spinner Widget ===")
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
            # Check spinner creation
            if "device_spinner" in content:
                print("✓ Found device_spinner in main.py")
                
                # Check spinner configuration
                spinner_checks = [
                    ("is defined as class variable", "self.device_spinner"),
                    ("is created as Spinner widget", "Spinner("),
                    ("has values property set", ".values = "),
                    ("has text property set", ".text = "),
                ]
                
                for name, pattern in spinner_checks:
                    if pattern in content:
                        print(f"  ✓ Spinner {name}")
                    else:
                        print(f"  ✗ Spinner may not {name}")
            else:
                print("✗ Could not find device_spinner in main.py")
    except FileNotFoundError:
        print("main.py not found in current directory")
    except Exception as e:
        print(f"Error checking device_spinner: {e}")

def inject_debug_logs():
    """Generate code to inject debug logs in key spots of main.py"""
    print("\n=== Debug Log Injection Code ===")
    print("Add these print statements to your main.py file to debug the device list update process:")
    
    debug_code = """
# In update_device_list method:
def update_device_list(self, dt):
    try:
        print("\\n=== update_device_list called ===")
        devices = self.active_manager.get_discovered_devices()
        print(f"Retrieved {len(devices)} devices from {self.connection_type} manager")
        print(f"Devices: {devices}")
        
        if devices:
            # Format devices for spinner based on connection type
            device_list = format_device_list_for_spinner(devices, self.connection_type)
            print(f"Formatted device list: {device_list}")
            
            # Update spinner
            self.device_spinner.values = device_list
            print(f"Updated spinner values: {self.device_spinner.values}")
            self.device_spinner.text = device_list[0]  # Select first device
            print(f"Updated spinner text: {self.device_spinner.text}")
        else:
            print("No devices found, clearing spinner")
            self.device_spinner.text = "No devices found"
            self.device_spinner.values = []
            
        print("=== update_device_list completed ===\\n")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error updating device list: {e}")
        self.device_spinner.text = "Error retrieving devices"
    finally:
        self.scan_btn.text = "Scan for Devices"
        self.scan_btn.disabled = False
"""
    print(debug_code)
    
    print("\nAdd this to your start_scan method:")
    debug_scan = """
def start_scan(self, instance):
    print("\\n=== start_scan called ===")
    print(f"Connection type: {self.connection_type}")
    print(f"Active manager: {self.active_manager}")
    
    # Rest of your method...
    
    # At the end, add:
    print(f"Scheduled update_device_list to run in 10 seconds")
"""
    print(debug_scan)

def suggest_fixes():
    """Suggest potential fixes based on common issues"""
    print("\n=== Suggested Fixes ===")
    
    fixes = [
        "1. Make sure update_device_list is being called after scan completes:\n"
        "   Clock.schedule_once(self.update_device_list, 10)  # Increase timeout to 10 seconds",
        
        "2. Verify device_spinner is properly initialized:\n"
        "   self.device_spinner = Spinner(text='No devices found', values=[])",
        
        "3. Check that format_device_list_for_spinner is working correctly:\n"
        "   device_list = format_device_list_for_spinner(devices, self.connection_type)\n"
        "   print(f\"Formatted device list: {device_list}\")",
        
        "4. Add direct binding to the scanning property:\n"
        "   self.bt_manager.bind(scanning=self._on_scanning_changed)",
        
        "5. Create a scanning callback handler:\n"
        "   def _on_scanning_changed(self, instance, value):\n"
        "       if not value:  # Scanning completed\n"
        "           print(\"Scanning completed, updating device list\")\n"
        "           Clock.schedule_once(self.update_device_list, 0.5)",
        
        "6. Verify the device list is actually being populated:\n"
        "   def debug_devices(self, dt):\n"
        "       devices = self.active_manager.get_discovered_devices()\n"
        "       print(f\"Found {len(devices)} devices: {devices}\")",
        
        "7. Add the scan completion binding directly in start_scan:\n"
        "   def start_scan(self, instance):\n"
        "       # existing code...\n"
        "       # Add a direct callback for scan completion\n"
        "       def on_scan_complete(dt):\n"
        "           devices = self.active_manager.get_discovered_devices()\n"
        "           print(f\"Scan complete! Found {len(devices)} devices\")\n"
        "           self.update_device_list(None)\n"
        "       # Schedule the callback\n"
        "       Clock.schedule_once(on_scan_complete, 10)"
    ]
    
    for fix in fixes:
        print(f"\n{fix}")

def main():
    """Main function to run the debugger"""
    print("=" * 60)
    print(" Bluetooth Device Detection Debugger")
    print("=" * 60)
    
    # Run the tests
    devices = test_bluetooth_scanning()
    check_event_binding()
    check_update_method()
    verify_device_spinner()
    inject_debug_logs()
    suggest_fixes()
    
    print("\n=" * 30)
    print("Debugging complete! Follow the suggestions above to fix your device detection issues.")
    print("=" * 60)
    
    if devices and len(devices) > 0:
        print(f"\nBluetooth scanning found {len(devices)} devices, but they're not showing in the UI.")
        print("This confirms the issue is in the connection between the BluetoothManager and the UI.")
    else:
        print("\nBluetooth scanning did not find any devices. Check your Bluetooth adapter and permissions.")

if __name__ == "__main__":
    main()