"""
Device Selection Fix Utility

This module provides functions to fix device selection in the heart rate monitor app
by properly formatting device information for display in the UI and ensuring
consistent behavior between Bluetooth and ANT+ device selection.
"""

def format_device_list_for_spinner(devices, connection_type):
    """
    Format a list of discovered devices for display in the UI spinner.
    
    Args:
        devices: List of device dictionaries from either manager
        connection_type: Either 'bluetooth' or 'ant'
        
    Returns:
        List of formatted strings for the spinner widget
    """
    if not devices:
        return []
        
    formatted_devices = []
    
    if connection_type == 'bluetooth':
        # Format Bluetooth devices: "Device Name (AA:BB:CC:DD:EE:FF)"
        for device in devices:
            name = device.get('name', 'Unknown Device')
            address = device.get('address', 'Unknown Address')
            formatted_devices.append(f"{name} ({address})")
    else:  # ANT+
        # Format ANT+ devices: "Device Name (ID: 123)"
        for device in devices:
            name = device.get('name', 'Unknown Device')
            device_id = device.get('id', 'Unknown ID')
            last_hr = device.get('last_hr', '')
            
            # Include heart rate if available
            if last_hr:
                formatted_devices.append(f"{name} (ID: {device_id}) - {last_hr} bpm")
            else:
                formatted_devices.append(f"{name} (ID: {device_id})")
    
    return formatted_devices

def extract_device_identifier(selected_text, connection_type):
    """
    Extract the device identifier from the selected text in the spinner.
    
    Args:
        selected_text: The text selected from the spinner
        connection_type: Either 'bluetooth' or 'ant'
        
    Returns:
        The device identifier (address for Bluetooth, ID for ANT+)
    """
    if not selected_text or selected_text == "No devices found":
        return None
        
    try:
        if connection_type == 'bluetooth':
            # Extract the address from "Device Name (AA:BB:CC:DD:EE:FF)"
            address = selected_text.split("(")[1].split(")")[0].strip()
            return address
        else:  # ANT+
            # Extract the ID from "Device Name (ID: 123)" or "Device Name (ID: 123) - 70 bpm"
            id_part = selected_text.split("(ID: ")[1].split(")")[0].strip()
            return id_part
    except:
        print(f"Error extracting identifier from: {selected_text}")
        return None

def update_ui_device_list(app, devices):
    """
    Update the UI spinner with the list of discovered devices.
    
    Args:
        app: The Kivy application instance
        devices: List of device dictionaries
        
    Returns:
        True if devices were found and added to the spinner, False otherwise
    """
    try:
        # Format the devices for the spinner based on connection type
        device_list = format_device_list_for_spinner(devices, app.connection_type)
        
        if device_list:
            app.device_spinner.values = device_list
            app.device_spinner.text = device_list[0]  # Select first device
            return True
        else:
            app.device_spinner.text = "No devices found"
            app.device_spinner.values = []
            return False
    except Exception as e:
        print(f"Error updating device list in UI: {e}")
        app.device_spinner.text = "Error listing devices"
        return False
    