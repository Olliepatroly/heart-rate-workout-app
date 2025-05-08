#!/usr/bin/env python3
"""
OpenANT Version Checker

This script checks your OpenANT installation version and provides
information about compatibility with our ANT+ tester application.
"""

import sys
import os
import importlib
import importlib.util
import subprocess
import platform

def check_openant():
    """Check OpenANT installation and version"""
    print("Checking OpenANT installation...")
    
    try:
        import openant
        print(f"✓ OpenANT is installed")
        
        # Check version
        version = getattr(openant, "__version__", "unknown")
        print(f"✓ OpenANT version: {version}")
        
        # Check location
        location = getattr(openant, "__file__", "unknown")
        print(f"✓ OpenANT location: {location}")
        
        # Check key components
        has_usb_device = hasattr(openant.devices, "USBDevice")
        has_network_key = hasattr(openant.devices, "ANTPLUS_NETWORK_KEY")
        
        if has_usb_device and has_network_key:
            print("✓ Critical components found: USBDevice and ANTPLUS_NETWORK_KEY")
        else:
            missing = []
            if not has_usb_device:
                missing.append("USBDevice")
            if not has_network_key:
                missing.append("ANTPLUS_NETWORK_KEY")
            print(f"✗ Missing critical components: {', '.join(missing)}")
        
        # Check for find_devices function (which was causing issues)
        has_find_devices = hasattr(openant.devices, "find_devices")
        if has_find_devices:
            print("✓ find_devices function is available")
        else:
            print("✗ find_devices function is NOT available (as expected with some versions)")
            print("  → Our fixed tester uses custom device detection, so this is fine")
        
        return True, version, location
        
    except ImportError as e:
        print(f"✗ OpenANT is NOT installed: {e}")
        return False, None, None

def check_dependencies():
    """Check for required dependencies"""
    print("\nChecking dependencies...")
    
    dependencies = {
        "pyusb": "usb",
        "pyserial": "serial"
    }
    
    all_installed = True
    
    for package, module in dependencies.items():
        try:
            importlib.import_module(module)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is NOT installed")
            all_installed = False
    
    return all_installed

def suggest_installation():
    """Suggest how to install OpenANT based on platform"""
    print("\nInstallation instructions:")
    
    system = platform.system()
    pip_command = "pip3" if sys.version_info.major == 3 else "pip"
    
    print(f"To install OpenANT:")
    print(f"  {pip_command} install openant")
    
    print("\nRequired dependencies:")
    print(f"  {pip_command} install pyusb pyserial")
    
    if system == "Linux":
        print("\nOn Linux, you may also need:")
        print("  sudo apt-get install libusb-1.0-0-dev libudev-dev")
        print("\nAnd set up USB device permissions:")
        print("  sudo sh -c 'echo SUBSYSTEM==\\\"usb\\\", ATTRS{idVendor}==\\\"0fcf\\\", MODE=\\\"0666\\\" > /etc/udev/rules.d/99-antplus.rules'")
        print("  sudo udevadm control --reload-rules")
        print("  sudo udevadm trigger")
    
    elif system == "Darwin":  # macOS
        print("\nOn macOS, you may also need:")
        print("  brew install libusb")
    
    elif system == "Windows":
        print("\nOn Windows, you may need to install ANT+ USB drivers from:")
        print("  https://www.thisisant.com/developer/resources/downloads/")

def check_which_tester_to_use():
    """Check which ANT+ tester version should be used"""
    print("\nDetermining which ANT+ tester to use...")
    
    has_openant, version, _ = check_openant()
    
    if not has_openant:
        print("✗ OpenANT is not installed - install it first")
        return "none"
    
    has_find_devices = False
    try:
        import openant.devices
        has_find_devices = hasattr(openant.devices, "find_devices")
    except:
        pass
    
    if has_find_devices:
        print("✓ Your OpenANT version has the find_devices function")
        print("  → You can use either the original or fixed tester")
        return "both"
    else:
        print("✓ Your OpenANT version does NOT have the find_devices function")
        print("  → You should use the fixed tester version (ant_tester_fixed.py)")
        return "fixed"

def main():
    """Main function"""
    print("=" * 60)
    print(" OpenANT Version Checker for ANT+ Tester")
    print("=" * 60)
    
    # Check Python version
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print()
    
    # Check OpenANT
    has_openant, version, location = check_openant()
    
    # Check dependencies
    has_dependencies = check_dependencies()
    
    # Determine which tester to use
    print()
    tester_to_use = check_which_tester_to_use()
    
    # Suggestions
    print("\n" + "=" * 60)
    if not has_openant or not has_dependencies:
        print("Some components are missing. Please install the required packages.")
        suggest_installation()
    else:
        print("OpenANT installation looks good!")
        
        if tester_to_use == "fixed":
            print("\nTo run the ANT+ tester, use:")
            print("  python ant_tester_fixed.py")
        elif tester_to_use == "both":
            print("\nYou can use either tester:")
            print("  python ant_tester.py")
            print("  python ant_tester_fixed.py")
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())