#!/usr/bin/env python3
"""
ANT+ Diagnostic Tool

This simple script checks your OpenANT installation and provides
detailed information to help troubleshoot import and detection issues.
"""

import sys
import os
import traceback
import importlib
import importlib.util
from pprint import pprint

def check_python_env():
    """Print information about the Python environment"""
    print("\n=== Python Environment ===")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Working Directory: {os.getcwd()}")
    
    # Check if running in virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"In Virtual Environment: {in_venv}")
    
    # Print sys.path to see where Python looks for modules
    print("\nPython Module Search Paths:")
    for idx, path in enumerate(sys.path):
        print(f"  {idx}: {path}")
        
def check_openant_installation():
    """Check for OpenANT installation details"""
    print("\n=== OpenANT Installation ===")
    
    # Method 1: Try direct import
    try:
        import openant
        print("OpenANT Import: SUCCESS")
        
        # Get version
        version = getattr(openant, "__version__", "unknown")
        print(f"OpenANT Version: {version}")
        
        # Get module location
        module_location = getattr(openant, "__file__", "unknown")
        print(f"OpenANT Location: {module_location}")
        
        # Check for key submodules
        submodules = ["devices", "easy", "easy.node", "base", "message"]
        print("\nOpenANT Submodules:")
        for submodule in submodules:
            full_name = f"openant.{submodule}"
            try:
                module = importlib.import_module(full_name)
                print(f"  ✓ {full_name} - Found at: {getattr(module, '__file__', 'unknown')}")
            except ImportError as e:
                print(f"  ✗ {full_name} - Error: {e}")
        
        # Check specific critical components
        print("\nOpenANT Critical Components:")
        
        # Check for USBDevice
        try:
            from openant.devices import USBDevice
            print("  ✓ USBDevice class found")
        except ImportError as e:
            print(f"  ✗ USBDevice class not found: {e}")
        
        # Check for Node
        try:
            from openant.easy.node import Node
            print("  ✓ Node class found")
        except ImportError as e:
            print(f"  ✗ Node class not found: {e}")
        
        # Check for ANTPLUS_NETWORK_KEY
        try:
            from openant.devices import ANTPLUS_NETWORK_KEY
            print("  ✓ ANTPLUS_NETWORK_KEY found")
        except ImportError as e:
            print(f"  ✗ ANTPLUS_NETWORK_KEY not found: {e}")
            
        # Check for find_devices (which was causing issues)
        try:
            # Try to access find_devices through different potential locations
            find_devices_found = False
            
            # Try direct import first
            try:
                from openant.devices import find_devices
                print("  ✓ find_devices function found in openant.devices")
                find_devices_found = True
            except ImportError:
                pass
                
            # Try searching in module attributes if direct import failed
            if not find_devices_found:
                for attr_name in dir(openant.devices):
                    if attr_name.lower() == "find_devices":
                        print(f"  ✓ find_devices found as: openant.devices.{attr_name}")
                        find_devices_found = True
                        break
                
            if not find_devices_found:
                print("  ✗ find_devices function not found in openant.devices")
        except Exception as e:
            print(f"  ✗ Error checking for find_devices: {e}")
            
    except ImportError as e:
        print(f"OpenANT Import: FAILED - {e}")
        traceback.print_exc()
    
def check_usb_libraries():
    """Check for USB-related libraries"""
    print("\n=== USB Libraries ===")
    
    usb_libraries = [
        "usb", "usb.core", "usb.util",
        "serial", "serial.tools.list_ports"
    ]
    
    for lib in usb_libraries:
        try:
            module = importlib.import_module(lib)
            print(f"✓ {lib}: FOUND at {getattr(module, '__file__', 'unknown')}")
        except ImportError as e:
            print(f"✗ {lib}: NOT FOUND - {e}")

def check_kivy_environment():
    """Check Kivy installation and settings"""
    print("\n=== Kivy Environment ===")
    
    try:
        import kivy
        print(f"Kivy Import: SUCCESS")
        print(f"Kivy Version: {kivy.__version__}")
        print(f"Kivy Location: {kivy.__file__}")
        
        # Check Kivy configuration
        if hasattr(kivy, 'config'):
            print("\nKivy Configuration:")
            config = kivy.config.Config
            for section in config.sections():
                print(f"  Section: {section}")
                for option in config.options(section):
                    value = config.get(section, option)
                    print(f"    {option} = {value}")
    
    except ImportError as e:
        print(f"Kivy Import: FAILED - {e}")
    
def detect_usb_devices():
    """Try to detect connected USB devices"""
    print("\n=== USB Device Detection ===")
    
    # Try using PyUSB
    try:
        import usb.core
        
        # List all USB devices
        devices = usb.core.find(find_all=True)
        count = 0
        
        print("USB Devices Detected by PyUSB:")
        for device in devices:
            count += 1
            try:
                vendor = device.idVendor
                product = device.idProduct
                print(f"  Device {count}: Vendor ID: 0x{vendor:04x}, Product ID: 0x{product:04x}")
                
                # Check if it's potentially an ANT+ device
                if vendor == 0x0fcf:  # Dynastream/Garmin ANT+ vendor ID
                    print(f"    *** Potential ANT+ device found! ***")
            except:
                print(f"  Device {count}: Error accessing device details")
        
        if count == 0:
            print("  No USB devices detected")
    
    except Exception as e:
        print(f"Error using PyUSB: {e}")
    
    # Try using serial ports
    try:
        import serial.tools.list_ports
        
        ports = list(serial.tools.list_ports.comports())
        print("\nSerial Ports Detected:")
        
        if ports:
            for port in ports:
                print(f"  Port: {port.device}")
                print(f"    Description: {port.description}")
                print(f"    Hardware ID: {port.hwid}")
        else:
            print("  No serial ports detected")
    
    except Exception as e:
        print(f"Error detecting serial ports: {e}")

def run_diagnostics():
    """Run all diagnostic tests"""
    print("=== ANT+ Integration Diagnostic Tool ===")
    print("Running comprehensive diagnostics to check OpenANT installation...")
    
    try:
        check_python_env()
        check_openant_installation()
        check_usb_libraries()
        check_kivy_environment()
        detect_usb_devices()
        
        print("\n=== Diagnostic Complete ===")
        print("Please share the output above when seeking support.")
        
    except Exception as e:
        print(f"Error during diagnostics: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostics()