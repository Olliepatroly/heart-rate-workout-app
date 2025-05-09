#!/usr/bin/env python3
"""
Garmin HRM Dual Debugger

This script specifically focuses on detecting Garmin HRM Dual heart rate monitors,
which can be difficult to discover with standard BLE scanning approaches.
"""

import asyncio
import platform
import time
import sys

# Check for bleak availability
try:
    import bleak
    # Get version safely - some bleak installations don't have __version__
    try:
        BLEAK_VERSION = bleak.__version__
        print(f"Bleak version: {BLEAK_VERSION}")
    except AttributeError:
        print("Bleak installed (version attribute not available)")
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Bleak library not found. Install with 'pip install bleak'")

# Constants for heart rate service
HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
DEVICE_INFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"

async def debug_scan():
    """Run a comprehensive scan with detailed debugging information"""
    if not BLEAK_AVAILABLE:
        print("Bleak library is required for this test.")
        return
    
    from bleak import BleakScanner
    print("\n=== Starting Comprehensive BLE Scan ===")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    # Track all discovered devices
    all_devices = []
    
    # Setup verbose callback that logs everything
    def verbose_callback(device, advertisement_data):
        all_devices.append((device, advertisement_data))
        
        print("\n----- Device Detected -----")
        print(f"Address: {device.address}")
        print(f"Name: {device.name or 'Unknown'}")
        
        if hasattr(advertisement_data, 'local_name') and advertisement_data.local_name:
            print(f"Local Name: {advertisement_data.local_name}")
        
        if hasattr(advertisement_data, 'rssi'):
            print(f"RSSI: {advertisement_data.rssi}")
        
        if hasattr(advertisement_data, 'service_uuids') and advertisement_data.service_uuids:
            print("Service UUIDs:")
            for uuid in advertisement_data.service_uuids:
                service_name = "Unknown"
                if HEART_RATE_SERVICE_UUID.lower() in uuid.lower():
                    service_name = "Heart Rate Service"
                print(f"  - {uuid} ({service_name})")
        
        if hasattr(advertisement_data, 'manufacturer_data') and advertisement_data.manufacturer_data:
            print("Manufacturer Data:")
            for company_id, data in advertisement_data.manufacturer_data.items():
                company_name = f"ID: {company_id}"
                if company_id == 0x006b:
                    company_name = "Garmin"
                
                print(f"  - {company_name}: {data.hex()}")
        
        if hasattr(advertisement_data, 'service_data') and advertisement_data.service_data:
            print("Service Data:")
            for uuid, data in advertisement_data.service_data.items():
                print(f"  - {uuid}: {data.hex()}")
    
    # Start scanner with verbose callback
    scanner = BleakScanner(detection_callback=verbose_callback)
    await scanner.start()
    
    print("\nScanning for 30 seconds...")
    for i in range(30):
        await asyncio.sleep(1)
        # Print progress every 5 seconds
        if (i + 1) % 5 == 0:
            print(f"Still scanning... ({i+1}s elapsed, found {len(all_devices)} devices)")
    
    await scanner.stop()
    
    # Process results
    print("\n=== Scan Complete ===")
    print(f"Discovered {len(all_devices)} total devices")
    
    # Filter for potential heart rate monitors
    hrm_devices = []
    garmin_devices = []
    
    for device, adv_data in all_devices:
        is_hrm = False
        is_garmin = False
        
        # Check service UUIDs for heart rate service
        if hasattr(adv_data, 'service_uuids') and adv_data.service_uuids:
            for uuid in adv_data.service_uuids:
                if HEART_RATE_SERVICE_UUID.lower() in uuid.lower():
                    is_hrm = True
                    break
        
        # Check manufacturer data for Garmin
        if hasattr(adv_data, 'manufacturer_data') and 0x006b in adv_data.manufacturer_data:
            is_garmin = True
        
        # Check name for indicators
        if device.name:
            lower_name = device.name.lower()
            if any(kw in lower_name for kw in ['garmin', 'hrm']):
                is_garmin = True
            if any(kw in lower_name for kw in ['heart', 'hr', 'pulse']):
                is_hrm = True
        
        if is_hrm:
            hrm_devices.append((device, adv_data))
        if is_garmin:
            garmin_devices.append((device, adv_data))
    
    print(f"\n=== Heart Rate Monitors: {len(hrm_devices)} ===")
    for device, _ in hrm_devices:
        print(f"- {device.name or 'Unknown'} ({device.address})")
    
    print(f"\n=== Garmin Devices: {len(garmin_devices)} ===")
    for device, _ in garmin_devices:
        print(f"- {device.name or 'Unknown'} ({device.address})")
    
    # Now scan specifically for ANT+ sticks
    try:
        import usb.core
        print("\n=== Scanning for ANT+ USB Sticks ===")
        
        # Garmin/Dynastream ANT+ USB stick vendor/product IDs
        ant_ids = [
            (0x0fcf, 0x1004),  # ANT+ USB stick
            (0x0fcf, 0x1008),  # ANT+ USB2 stick
            (0x0fcf, 0x1009),  # ANT+ USB-m stick
        ]
        
        ant_sticks = []
        for vendor_id, product_id in ant_ids:
            device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if device:
                print(f"Found ANT+ USB stick: {vendor_id:04x}:{product_id:04x}")
                ant_sticks.append(device)
        
        if not ant_sticks:
            print("No ANT+ USB sticks found.")
        
    except ImportError:
        print("\nUSB library not available. Cannot check for ANT+ USB sticks.")
    
    return all_devices, hrm_devices, garmin_devices

async def quick_scan_for_garmin():
    """Run a quicker scan specifically targeting Garmin devices"""
    if not BLEAK_AVAILABLE:
        print("Bleak library is required for this test.")
        return
    
    from bleak import BleakScanner
    print("\n=== Quick Scan for Garmin HRM Dual ===")
    
    # Track discovered devices
    garmin_devices = []
    
    # Callback looking specifically for Garmin devices
    def garmin_callback(device, adv_data):
        # Check if it might be a Garmin HRM
        is_garmin_hrm = False
        
        # Check manufacturer data
        if hasattr(adv_data, 'manufacturer_data') and 0x006b in adv_data.manufacturer_data:
            is_garmin_hrm = True
        
        # Check name
        if device.name and 'garmin' in device.name.lower():
            is_garmin_hrm = True
        
        # Check service UUIDs
        if hasattr(adv_data, 'service_uuids') and adv_data.service_uuids:
            for uuid in adv_data.service_uuids:
                if HEART_RATE_SERVICE_UUID.lower() in uuid.lower():
                    is_garmin_hrm = True
                    break
        
        if is_garmin_hrm:
            print(f"Found potential Garmin HRM: {device.name or 'Unknown'} ({device.address})")
            garmin_devices.append((device, adv_data))
        else:
            # Also log heart rate devices
            if (hasattr(adv_data, 'service_uuids') and adv_data.service_uuids and 
                any(HEART_RATE_SERVICE_UUID.lower() in uuid.lower() for uuid in adv_data.service_uuids)):
                print(f"Found heart rate device: {device.name or 'Unknown'} ({device.address})")
    
    # Start scanner with Garmin-focused callback
    scanner = BleakScanner(detection_callback=garmin_callback)
    await scanner.start()
    
    print("Scanning for 15 seconds...")
    await asyncio.sleep(15)
    
    await scanner.stop()
    
    # Process results
    print("\n=== Quick Scan Complete ===")
    if garmin_devices:
        print(f"Found {len(garmin_devices)} potential Garmin heart rate monitors:")
        for device, _ in garmin_devices:
            print(f"- {device.name or 'Unknown'} ({device.address})")
    else:
        print("No Garmin heart rate monitors found.")
        print("\nTroubleshooting tips:")
        print("1. Make sure the strap is worn (skin contact activates some HRMs)")
        print("2. Check if the strap is wet (needed for proper electrical contact)")
        print("3. Make sure batteries are fresh")
        print("4. Try putting the device in pairing mode (if applicable)")
    
    return garmin_devices

async def test_connection(device_address):
    """Test connection to a specific device address"""
    if not BLEAK_AVAILABLE:
        print("Bleak library is required for this test.")
        return
    
    from bleak import BleakClient
    
    print(f"\n=== Testing Connection to {device_address} ===")
    print("Attempting connection...")
    
    client = BleakClient(device_address)
    try:
        await client.connect()
        print("Connected successfully!")
        
        print("\nDiscovering services...")
        services = await client.get_services()
        
        print("\nAvailable services:")
        hr_service = None
        device_info_service = None
        
        for service in services:
            service_name = "Unknown"
            if HEART_RATE_SERVICE_UUID.lower() in service.uuid.lower():
                service_name = "Heart Rate Service"
                hr_service = service
            elif DEVICE_INFO_SERVICE_UUID.lower() in service.uuid.lower():
                service_name = "Device Information Service"
                device_info_service = service
            
            print(f"- {service.uuid} ({service_name})")
            for char in service.characteristics:
                print(f"  * {char.uuid} - Properties: {','.join(char.properties)}")
        
        # Try to read device information if available
        if device_info_service:
            print("\nDevice Information:")
            for char in device_info_service.characteristics:
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        if value:
                            # Try to decode as string
                            try:
                                value_str = value.decode('utf-8')
                                print(f"  {char.uuid}: {value_str}")
                            except:
                                print(f"  {char.uuid}: {value.hex()}")
                    except Exception as e:
                        print(f"  {char.uuid}: Error reading - {e}")
        
        # Try to subscribe to heart rate notifications if available
        if hr_service:
            print("\nSetting up heart rate notifications...")
            hr_char = None
            
            for char in hr_service.characteristics:
                if "notify" in char.properties:
                    hr_char = char
                    break
            
            if hr_char:
                print(f"Found heart rate characteristic: {hr_char.uuid}")
                
                def hr_notification_handler(sender, data):
                    """Handle heart rate notifications"""
                    try:
                        # Parse according to heart rate profile
                        flags = data[0]
                        
                        if flags & 0x01:  # 16-bit format
                            hr_value = int.from_bytes(data[1:3], byteorder='little')
                        else:  # 8-bit format
                            hr_value = data[1]
                            
                        print(f"Received heart rate: {hr_value} BPM")
                    except Exception as e:
                        print(f"Error parsing heart rate data: {e}")
                
                await client.start_notify(hr_char.uuid, hr_notification_handler)
                print("Heart rate notifications started")
                print("Waiting for 20 seconds to receive data...")
                
                await asyncio.sleep(20)
                
                print("Stopping notifications...")
                await client.stop_notify(hr_char.uuid)
            else:
                print("No suitable heart rate characteristic found")
        
        print("\nDisconnecting...")
        await client.disconnect()
        print("Disconnected")
        
    except Exception as e:
        print(f"Connection error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client.is_connected:
            await client.disconnect()

def main():
    """Main function to run the Garmin HRM debugger"""
    print("=" * 60)
    print(" Garmin HRM Dual Debugger")
    print("=" * 60)
    
    if not BLEAK_AVAILABLE:
        print("\nERROR: Bleak library not found. Please install it with:")
        print("pip install bleak")
        return 1
    
    if len(sys.argv) > 1 and sys.argv[1] == "--connect":
        if len(sys.argv) > 2:
            address = sys.argv[2]
            print(f"Will attempt to connect to device: {address}")
            asyncio.run(test_connection(address))
        else:
            print("Please specify a device address to connect to.")
            print("Usage: python debug_garmin_hrm.py --connect <device_address>")
    elif len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("Running quick scan for Garmin devices...")
        asyncio.run(quick_scan_for_garmin())
    else:
        print("Running comprehensive scan for all BLE devices...")
        print("This will take about 30 seconds.")
        print("For a quicker scan specifically for Garmin devices, use:")
        print("python debug_garmin_hrm.py --quick")
        asyncio.run(debug_scan())
    
    return 0

if __name__ == "__main__":
    sys.exit(main())