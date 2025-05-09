import kivy
import asyncio
import sys
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy_garden.graph import Graph, MeshLinePlot
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.core.window import Window
from kivy.utils import get_color_from_hex


app_dir = os.path.dirname(os.path.abspath(__file__))
hr_app_dir = os.path.join(app_dir, 'heart-rate-workout-app')
if hr_app_dir not in sys.path:
    sys.path.insert(0, hr_app_dir)
    
from bluetooth_manager import BluetoothManager
from ant_manager_final import ANTManager
from async_utils import install_asyncio_loop, run_async
from hr_controller import HRController
from debug_helper import log_startup_info, log_info, log_error, log_debug, log_warning, inject_exception_handler
from device_selection_fix import format_device_list_for_spinner, extract_device_identifier, update_ui_device_list

class HeartRateMonitorApp(App):
    # Properties
    current_hr = NumericProperty(0)
    current_zone = NumericProperty(0)
    current_wattage = NumericProperty(0)
    workout_time = NumericProperty(0)
    calories_burned = NumericProperty(0)
    is_connected = BooleanProperty(False)
    is_workout_active = BooleanProperty(False)
    auto_mode = BooleanProperty(False)
    
    # Zone colors
    zone_colors = {
        0: get_color_from_hex("#CCCCCC"),  # Gray for no zone
        1: get_color_from_hex("#3b82f6"),  # Blue - Zone 1
        2: get_color_from_hex("#10b981"),  # Green - Zone 2
        3: get_color_from_hex("#f59e0b"),  # Orange - Zone 3
        4: get_color_from_hex("#ef4444"),  # Red - Zone 4
        5: get_color_from_hex("#8b5cf6")   # Purple - Zone 5
    }

    def build(self):
        # Set up asyncio integration - CRITICAL: Must be done before any Bluetooth operations
        self.event_loop = install_asyncio_loop()
        log_info(f"Asyncio event loop initialized: {self.event_loop}")
        
        # Set window size
        Window.size = (900, 600)
        
        # Initialize managers
        log_info("Initializing BluetoothManager and HRController")
        self.bt_manager = BluetoothManager()
        self.hr_controller = HRController()
        self.ant_manager = ANTManager()
        
        if hasattr(self.bt_manager, 'integrate_with_main_app'):
            self.bt_manager.integrate_with_main_app(self)
            print("Integrated BluetoothManager with main app")
        
        if hasattr(self.ant_manager, 'integrate_with_main_app'):
            self.ant_manager.integrate_with_main_app(self)
            print("Integrated ANTManager with main app")
            
        self.active_manager = self.bt_manager
        self.connection_type = "Bluetooth"
        # Setup event bindings
        log_debug("Setting up bluetooth bindings")
        self.bt_manager.bind(
            connected=self._on_connection_changed,
            hr_data=self._on_hr_data_changed,
            connection_status=self._on_connection_status_changed
        )
            
        log_debug("setting up ANTManager bindings")
        self.ant_manager.bind(
            connected=self._on_connection_changed,
            hr_data=self._on_hr_data_changed,
            connection_status=self._on_connection_status_changed
        )
        
        # Initialize history for graph
        self.hr_history = []
        self.time_points = []
        self.workout_seconds = 0
        
        # Main layout
        self.main_layout = TabbedPanel(do_default_tab=False)
        
        # Add tabs
        self.main_layout.add_widget(self.build_dashboard_tab())
        self.main_layout.add_widget(self.build_settings_tab())
        self.main_layout.add_widget(self.build_workout_tab())
        self.main_layout.add_widget(self.build_connection_tab())
        
        # Start update loop
        Clock.schedule_interval(self.update, 1)
        
        return self.main_layout
    
    def build_dashboard_tab(self):
        tab = TabbedPanelItem(text='Dashboard')
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        
        # Header with connection status
        header = BoxLayout(size_hint_y=0.1)
        header.add_widget(Label(text='Heart Rate Monitor', font_size=24))
        self.connection_label = Label(text='Not Connected', color=(1, 0, 0, 1))
        header.add_widget(self.connection_label)
        layout.add_widget(header)
        
        # Main content - split into left and right
        content = BoxLayout(spacing=10)
        
        # Left panel - HR display and controls
        left_panel = BoxLayout(orientation='vertical', spacing=10)
        
        # HR display
        hr_display = BoxLayout(orientation='vertical', size_hint_y=0.5)
        hr_display.add_widget(Label(text='HEART RATE', font_size=18))
        self.hr_value_label = Label(text='--', font_size=60, color=(1, 0.2, 0.2, 1))
        hr_display.add_widget(self.hr_value_label)
        hr_display.add_widget(Label(text='BPM', font_size=18))
        
        # HR progress bar
        self.hr_progress = ProgressBar(max=100, value=0)
        hr_display.add_widget(self.hr_progress)
        
        # Current zone display
        self.zone_label = Label(text='Zone: --', font_size=24, color=(0.7, 0.7, 0.7, 1))
        hr_display.add_widget(self.zone_label)
        
        left_panel.add_widget(hr_display)
        
        # Connection buttons
        connection_buttons = BoxLayout(size_hint_y=0.2)
        self.connect_btn = Button(text='Connect HR Monitor', on_press=self.toggle_connection)
        connection_buttons.add_widget(self.connect_btn)
        left_panel.add_widget(connection_buttons)
        
        # Workout control buttons
        workout_buttons = BoxLayout(size_hint_y=0.2)
        self.start_workout_btn = Button(text='Start Workout', on_press=self.toggle_workout)
        self.stop_workout_btn = Button(text='Stop Workout', on_press=self.stop_workout, disabled=True)
        workout_buttons.add_widget(self.start_workout_btn)
        workout_buttons.add_widget(self.stop_workout_btn)
        left_panel.add_widget(workout_buttons)
        
        # Control mode
        control_mode = BoxLayout(size_hint_y=0.2)
        self.manual_btn = ToggleButton(text='Manual Control', state='down', group='control_mode')
        self.auto_btn = ToggleButton(text='Auto Control', group='control_mode')
        self.manual_btn.bind(on_press=lambda x: self.set_control_mode(False))
        self.auto_btn.bind(on_press=lambda x: self.set_control_mode(True))
        control_mode.add_widget(self.manual_btn)
        control_mode.add_widget(self.auto_btn)
        left_panel.add_widget(control_mode)
        
        content.add_widget(left_panel)
        
        # Right panel - Zone info and graph
        right_panel = BoxLayout(orientation='vertical', spacing=10)
        
        # Zone information
        zones_box = BoxLayout(orientation='vertical', size_hint_y=0.4)
        zones_box.add_widget(Label(text='Heart Rate Zones', font_size=18))
        
        # Zone displays
        self.zone_displays = {}
        for i in range(1, 6):
            zone_row = BoxLayout()
            zone_row.add_widget(Label(text=f'Zone {i}:', size_hint_x=0.3))
            self.zone_displays[i] = Label(text='-- to --')
            zone_row.add_widget(self.zone_displays[i])
            zones_box.add_widget(zone_row)
        
        right_panel.add_widget(zones_box)
        
        # Graph display
        graph_box = BoxLayout(orientation='vertical', size_hint_y=0.6)
        graph_box.add_widget(Label(text='Heart Rate Trend', font_size=18))
        
        self.graph = Graph(xlabel='Time (min)', ylabel='BPM', 
                           x_ticks_minor=1, x_ticks_major=5, y_ticks_major=20,
                           y_grid_label=True, x_grid_label=True, padding=5,
                           x_grid=True, y_grid=True, xmin=0, xmax=10, ymin=40, ymax=200)
        
        self.plot = MeshLinePlot(color=[1, 0, 0, 1])
        self.plot.points = []
        self.graph.add_plot(self.plot)
        
        graph_box.add_widget(self.graph)
        right_panel.add_widget(graph_box)
        
        content.add_widget(right_panel)
        layout.add_widget(content)
        
        # Analytics at bottom
        analytics = BoxLayout(size_hint_y=0.15, spacing=10)
        
        # Time
        time_box = BoxLayout(orientation='vertical')
        time_box.add_widget(Label(text='WORKOUT TIME'))
        self.time_label = Label(text='00:00', font_size=24)
        time_box.add_widget(self.time_label)
        analytics.add_widget(time_box)
        
        # Watts
        watts_box = BoxLayout(orientation='vertical')
        watts_box.add_widget(Label(text='WATTS'))
        self.watts_label = Label(text='0', font_size=24)
        watts_box.add_widget(self.watts_label)
        analytics.add_widget(watts_box)
        
        # Calories
        calories_box = BoxLayout(orientation='vertical')
        calories_box.add_widget(Label(text='CALORIES'))
        self.calories_label = Label(text='0', font_size=24)
        calories_box.add_widget(self.calories_label)
        analytics.add_widget(calories_box)
        
        layout.add_widget(analytics)
        
        tab.add_widget(layout)
        return tab
    
    def build_settings_tab(self):
        tab = TabbedPanelItem(text='Settings')
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        
        # User profile settings
        layout.add_widget(Label(text='User Profile', font_size=24))
        
        # Age
        age_row = BoxLayout()
        age_row.add_widget(Label(text='Age:', size_hint_x=0.3))
        self.age_input = TextInput(text='30', input_filter='int', multiline=False)
        age_row.add_widget(self.age_input)
        layout.add_widget(age_row)
        
        # Resting HR
        resting_hr_row = BoxLayout()
        resting_hr_row.add_widget(Label(text='Resting HR:', size_hint_x=0.3))
        self.resting_hr_input = TextInput(text='60', input_filter='int', multiline=False)
        resting_hr_row.add_widget(self.resting_hr_input)
        layout.add_widget(resting_hr_row)
        
        # Max HR
        max_hr_row = BoxLayout()
        max_hr_row.add_widget(Label(text='Max HR:', size_hint_x=0.3))
        self.max_hr_input = TextInput(text='190', input_filter='int', multiline=False)
        max_hr_row.add_widget(self.max_hr_input)
        layout.add_widget(max_hr_row)
        
        # Weight
        weight_row = BoxLayout()
        weight_row.add_widget(Label(text='Weight (kg):', size_hint_x=0.3))
        self.weight_input = TextInput(text='70', input_filter='float', multiline=False)
        weight_row.add_widget(self.weight_input)
        layout.add_widget(weight_row)
        
        # Target Zone
        target_zone_row = BoxLayout()
        target_zone_row.add_widget(Label(text='Target Zone:', size_hint_x=0.3))
        self.target_zone_input = TextInput(text='3', input_filter='int', multiline=False)
        target_zone_row.add_widget(self.target_zone_input)
        layout.add_widget(target_zone_row)
        
        # Apply button
        apply_btn = Button(text='Apply Settings', size_hint_y=0.2)
        apply_btn.bind(on_press=self.apply_settings)
        layout.add_widget(apply_btn)
        
        # App settings section
        layout.add_widget(Label(text='App Settings', font_size=24, size_hint_y=0.1))
        
        # Debug mode
        debug_row = BoxLayout(size_hint_y=0.15)
        debug_row.add_widget(Label(text='Debug Mode:', size_hint_x=0.3))
        self.debug_btn = ToggleButton(text='Enable Simulated HR', size_hint_x=0.7)
        self.debug_btn.bind(state=self.toggle_debug_mode)
        debug_row.add_widget(self.debug_btn)
        layout.add_widget(debug_row)
        
        tab.add_widget(layout)
        return tab
    
    def build_workout_tab(self):
        tab = TabbedPanelItem(text='Workout')
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        
        # Simulated treadmill controls
        layout.add_widget(Label(text='Treadmill Controls', font_size=24))
        
        # Manual controls section
        self.manual_controls = BoxLayout(orientation='vertical', spacing=10)
        
        # Speed control
        speed_control = BoxLayout(orientation='vertical')
        speed_control.add_widget(Label(text='Speed (km/h)'))
        self.speed_slider = Slider(min=1, max=20, value=5, step=0.5)
        self.speed_slider.bind(value=self.update_speed)
        speed_control.add_widget(self.speed_slider)
        self.speed_label = Label(text='5.0 km/h')
        speed_control.add_widget(self.speed_label)
        self.manual_controls.add_widget(speed_control)
        
        # Incline control
        incline_control = BoxLayout(orientation='vertical')
        incline_control.add_widget(Label(text='Incline (%)'))
        self.incline_slider = Slider(min=0, max=15, value=0, step=0.5)
        self.incline_slider.bind(value=self.update_incline)
        incline_control.add_widget(self.incline_slider)
        self.incline_label = Label(text='0.0 %')
        incline_control.add_widget(self.incline_label)
        self.manual_controls.add_widget(incline_control)
        
        layout.add_widget(self.manual_controls)
        
        # Auto control section
        self.auto_controls = BoxLayout(orientation='vertical', spacing=10)
        self.auto_controls.opacity = 0  # Initially hidden
        
        # Base speed
        base_speed = BoxLayout(orientation='vertical')
        base_speed.add_widget(Label(text='Base Speed (km/h)'))
        self.base_speed_slider = Slider(min=1, max=10, value=3, step=0.5)
        base_speed.add_widget(self.base_speed_slider)
        self.base_speed_label = Label(text='3.0 km/h')
        self.base_speed_slider.bind(value=lambda _, val: setattr(self.base_speed_label, 'text', f'{val:.1f} km/h'))
        base_speed.add_widget(self.base_speed_label)
        self.auto_controls.add_widget(base_speed)
        
        # Max adjustment
        max_adjust = BoxLayout(orientation='vertical')
        max_adjust.add_widget(Label(text='Max Adjustment (km/h)'))
        self.max_adjust_slider = Slider(min=0, max=10, value=5, step=0.5)
        max_adjust.add_widget(self.max_adjust_slider)
        self.max_adjust_label = Label(text='5.0 km/h')
        self.max_adjust_slider.bind(value=lambda _, val: setattr(self.max_adjust_label, 'text', f'{val:.1f} km/h'))
        max_adjust.add_widget(self.max_adjust_label)
        self.auto_controls.add_widget(max_adjust)
        
        # Response speed
        response = BoxLayout(orientation='vertical')
        response.add_widget(Label(text='Response Speed'))
        self.response_slider = Slider(min=1, max=10, value=5, step=1)
        response.add_widget(self.response_slider)
        self.response_label = Label(text='5')
        self.response_slider.bind(value=lambda _, val: setattr(self.response_label, 'text', f'{int(val)}'))
        response.add_widget(self.response_label)
        self.auto_controls.add_widget(response)
        
        layout.add_widget(self.auto_controls)
        
        tab.add_widget(layout)
        return tab
    
    def build_connection_tab(self):
        tab = TabbedPanelItem(text='Connection')
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        type_box = BoxLayout(size_hint_y=0.1, spacing=10)
        type_box.add_widget(Label(text='Connection Type:', size_hint_x=0.3))
        
        # Create toggle buttons for connection type
        self.ble_btn = ToggleButton(text='Bluetooth', state='down', group='conn_type')
        self.ant_btn = ToggleButton(text='ANT+', group='conn_type')
        
        self.ble_btn.bind(on_press=lambda x: self.set_connection_type('bluetooth'))
        self.ant_btn.bind(on_press=lambda x: self.set_connection_type('ant'))
        
        type_box.add_widget(self.ble_btn)
        type_box.add_widget(self.ant_btn)
        
        layout.add_widget(type_box)
        
        # Device scan and selection
        layout.add_widget(Label(text='Bluetooth Device Management', font_size=24))
        
        # Scan button
        scan_row = BoxLayout(size_hint_y=0.1)
        self.scan_btn = Button(text='Scan for HR Monitors')
        self.scan_btn.bind(on_press=self.start_scan)
        scan_row.add_widget(self.scan_btn)
        layout.add_widget(scan_row)
        
        # Device list
        devices_box = BoxLayout(orientation='vertical', size_hint_y=0.4, spacing=5)
        devices_box.add_widget(Label(text='Available Devices:'))
        
        self.device_spinner = Spinner(
            text='No devices found',
            values=[],
            size_hint_y=0.8
        )
        devices_box.add_widget(self.device_spinner)
        
        layout.add_widget(devices_box)
        
        # Connection status
        status_box = BoxLayout(orientation='vertical', size_hint_y=0.2)
        status_box.add_widget(Label(text='Connection Status:'))
        self.connection_status_label = Label(text='Not connected')
        status_box.add_widget(self.connection_status_label)
        layout.add_widget(status_box)
        
        # Device info
        device_info_box = BoxLayout(orientation='vertical', size_hint_y=0.3)
        device_info_box.add_widget(Label(text='Device Information:'))
        
        info_grid = GridLayout(cols=2)
        info_grid.add_widget(Label(text='Name:'))
        self.device_name_label = Label(text='--')
        info_grid.add_widget(self.device_name_label)
        
        info_grid.add_widget(Label(text='Battery:'))
        self.battery_label = Label(text='--')
        info_grid.add_widget(self.battery_label)
        
        device_info_box.add_widget(info_grid)
        layout.add_widget(device_info_box)
        
        #refresh button
        refresh_btn = Button(text='Refresh Device List')
        refresh_btn.bind(on_press=self.force_refresh_devices)
        layout.add_widget(refresh_btn)
        
        # Connect button (separate from scan)
        connect_box = BoxLayout(size_hint_y=0.1)
        self.connect_device_btn = Button(text='Connect Selected Device')
        self.connect_device_btn.bind(on_press=self.connect_selected_device)
        connect_box.add_widget(self.connect_device_btn)
        layout.add_widget(connect_box)
        
        tab.add_widget(layout)
        return tab
    
    def set_connection_type(self, conn_type):
        """Switch between Bluetooth and ANT+ connection types"""
        # This is a new method - add it anywhere after your class definition
        self.connection_type = conn_type
        
        # Update active manager
        if conn_type == 'bluetooth':
            self.active_manager = self.bt_manager
            self.connection_status_label.text = "Ready to scan for Bluetooth devices"
        else:  # ANT+
            self.active_manager = self.ant_manager
            self.connection_status_label.text = "Ready to scan for ANT+ devices"
        
        # Reset device list
        self.device_spinner.values = []
        self.device_spinner.text = "No devices found"
        
        # Update UI based on connection type
        if self.active_manager.is_connected():
            self.connect_btn.text = "Disconnect"
        else:
            self.connect_btn.text = "Connect"
        
    def toggle_connection(self, instance):
        # Replace your existing toggle_connection method with this one
        if self.active_manager.is_connected():  # Changed from self.bt_manager.is_connected()
            # Disconnect
            self.active_manager.disconnect()  # Changed from self.bt_manager.disconnect()
        else:
            # If we haven't scanned yet or no device is selected, show the Connection tab
            if not self.device_spinner.values:
                self.main_layout.switch_to(self.main_layout.tab_list[3])  # Switch to Connection tab
                self.start_scan(None)
            else:
                self.connect_selected_device(None)
    
    def start_scan(self, instance):
        """Start scanning for devices with proper callbacks"""
        try:
            print("\n=== Starting Device Scan ===")
            print(f"Connection type: {self.connection_type}")
            
            self.scan_btn.text = "Scanning..."
            self.scan_btn.disabled = True
            self.device_spinner.values = []
            self.device_spinner.text = "Scanning for devices..."
            
            # Start scan with the active manager
            self.active_manager.start_scan()
            
            # Create a direct callback to handle scan completion
            def on_scan_complete(dt):
                print("Scan completion callback triggered")
                # Get devices directly from manager
                devices = self.active_manager.get_discovered_devices()
                print(f"Scan found {len(devices)} devices")
                
                # Update the UI immediately
                self.update_device_list(None)
            
            # Schedule the callback with a longer timeout (15 seconds)
            Clock.schedule_once(on_scan_complete, 15)
            
            print(f"Scheduled UI update to run in 15 seconds")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error starting scan: {e}")
            
            # Reset UI
            self.scan_btn.text = "Scan for Devices"
            self.scan_btn.disabled = False
            self.device_spinner.text = "Scanning failed. Try again."
    
    def update_device_list(self, dt):
        """Update the device spinner with discovered devices"""
        try:
            print("\n=== Updating Device List ===")
            devices = self.active_manager.get_discovered_devices()
            print(f"Retrieved {len(devices)} devices from {self.connection_type} manager")
            
            # Debug output of raw devices
            for i, device in enumerate(devices):
                print(f"  {i+1}. {device}")
            
            # Update the UI with formatted device list
            if devices:
                # Format devices for spinner based on connection type
                device_list = format_device_list_for_spinner(devices, self.connection_type)
                print(f"Formatted device list ({len(device_list)} items):")
                for i, item in enumerate(device_list):
                    print(f"  {i+1}. {item}")
                
                # Update spinner
                self.device_spinner.values = device_list
                print(f"Updated spinner values: {len(self.device_spinner.values)} items")
                
                if device_list:
                    self.device_spinner.text = device_list[0]  # Select first device
                    print(f"Set spinner selection to: {self.device_spinner.text}")
                else:
                    self.device_spinner.text = "No devices found"
            else:
                print("No devices found, clearing spinner")
                self.device_spinner.text = "No devices found"
                self.device_spinner.values = []
                
            print("=== Device list update completed ===\n")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error updating device list: {e}")
            self.device_spinner.text = "Error retrieving devices"
        finally:
            self.scan_btn.text = "Scan for Devices"
            self.scan_btn.disabled = False
    
    def force_refresh_devices(self, instance):
        """Manually force refresh of the device list"""
        print("Manually refreshing device list")
        devices = self.active_manager.get_discovered_devices()
        print(f"Active manager has {len(devices)} devices")
        self.update_device_list(None)
    
    def connect_selected_device(self, instance):
        """Connect to the selected device with the active manager"""
        if not self.device_spinner.values:
            return
            
        selected = self.device_spinner.text
        if selected == "No devices found" or "Error" in selected:
            return
        
        # Extract device identifier based on connection type
        identifier = extract_device_identifier(selected, self.connection_type)
        
        if not identifier:
            print(f"Could not extract device identifier from: {selected}")
            return
        
        print(f"Connecting to {self.connection_type} device with identifier: {identifier}")
        
        # Connect to the device with the active manager
        self.connect_btn.text = "Connecting..."
        self.connect_btn.disabled = True
        self.active_manager.connect(identifier)
        
    def toggle_debug_mode(self, instance, value):
        """Toggle simulated heart rate for debugging"""
        # Replace your existing toggle_debug_mode method with this one
        if value == 'down':  # Button is pressed (enabled)
            # Enable simulation on the active manager
            self.active_manager.create_debug_hr_updates(True)  # Changed from self.bt_manager
        else:
            self.active_manager.create_debug_hr_updates(False)  # Changed from self.bt_manager
        
    def toggle_workout(self, instance):
        if self.is_workout_active:
            # Pause workout
            self.is_workout_active = False
            self.start_workout_btn.text = 'Resume Workout'
        else:
            # Start workout
            self.is_workout_active = True
            self.start_workout_btn.text = 'Pause Workout'
            self.stop_workout_btn.disabled = False
            
            # If first start (not resume)
            if self.workout_seconds == 0:
                # Reset workout data
                self.hr_history = []
                self.time_points = []
                self.workout_seconds = 0
                self.calories_burned = 0
    
    def stop_workout(self, instance):
        self.is_workout_active = False
        self.workout_seconds = 0
        self.start_workout_btn.text = 'Start Workout'
        self.stop_workout_btn.disabled = True
        self.time_label.text = '00:00'
        self.calories_label.text = '0'
        
        # Reset graph
        self.plot.points = []
    
    def set_control_mode(self, auto):
        self.auto_mode = auto
        if auto:
            self.manual_controls.opacity = 0
            self.auto_controls.opacity = 1
        else:
            self.manual_controls.opacity = 1
            self.auto_controls.opacity = 0
    
    def update_speed(self, instance, value):
        self.speed_label.text = f'{value:.1f} km/h'
    
    def update_incline(self, instance, value):
        self.incline_label.text = f'{value:.1f} %'
    
    def apply_settings(self, instance):
        try:
            age = int(self.age_input.text)
            resting_hr = int(self.resting_hr_input.text)
            max_hr = int(self.max_hr_input.text) if self.max_hr_input.text else None
            
            # Calculate zones
            zones = self.hr_controller.calculate_zones(age, resting_hr, max_hr)
            
            # Update zone displays
            for i in range(1, 6):
                self.zone_displays[i].text = f"{zones[i]['min']} - {zones[i]['max']}"
        except ValueError:
            pass  # Handle invalid input
    
    def _on_connection_changed(self, instance, value):
        """Handle connection state changes"""
        self.is_connected = value
        
        if value:  # Connected
            self.connection_label.text = 'Connected'
            self.connection_label.color = (0, 1, 0, 1)
            self.connect_btn.text = 'Disconnect'
            self.connect_btn.disabled = False
            
            # Update device info
            self.device_name_label.text = self.bt_manager.device_name
            self.battery_label.text = f"{self.bt_manager.battery_level}%" if self.bt_manager.battery_level > 0 else "--"
            
            # Calculate zones when first connected
            self.apply_settings(None)
        else:  # Disconnected
            self.connection_label.text = 'Not Connected'
            self.connection_label.color = (1, 0, 0, 1)
            self.connect_btn.text = 'Connect HR Monitor'
            self.connect_btn.disabled = False
            
            # Reset HR display
            self.hr_value_label.text = "--"
            self.zone_label.text = "Zone: --"
            self.zone_label.color = self.zone_colors[0]
            self.hr_progress.value = 0
    
    def _on_hr_data_changed(self, instance, value):
        """Handle heart rate data updates"""
        # Update displays
        self.current_hr = value
        self.hr_value_label.text = str(value)
        
        if value > 0:
            # Update progress bar
            max_hr = int(self.max_hr_input.text) if self.max_hr_input.text else 220 - int(self.age_input.text)
            progress = min(100, (value / max_hr) * 100)
            self.hr_progress.value = progress
            
            # Update current zone
            self.current_zone = self.hr_controller.get_zone(value)
            zone_text = f"Zone: {self.current_zone}" if self.current_zone > 0 else "Zone: --"
            self.zone_label.text = zone_text
            
            # Set zone color
            self.zone_label.color = self.zone_colors[self.current_zone]
            
            # Update wattage if needed
            weight = float(self.weight_input.text) if self.weight_input.text else 70
            self.current_wattage = self.hr_controller.calculate_wattage(value, weight)
            self.watts_label.text = str(self.current_wattage)
    
    def _on_connection_status_changed(self, instance, value):
        """Handle connection status message changes"""
        self.connection_status_label.text = value
    
    def adjust_speed_based_on_hr(self):
        """Adjust treadmill speed based on heart rate relative to target zone"""
        # Get target HR for selected zone
        target_zone = int(self.target_zone_input.text) if self.target_zone_input.text else 3
        max_hr_value = int(self.max_hr_input.text) if self.max_hr_input.text else (220 - int(self.age_input.text))
        resting_hr = int(self.resting_hr_input.text) if self.resting_hr_input.text else 60
        
        hr_reserve = max_hr_value - resting_hr
        target_hr = 0
        
        # Calculate mid-point of target zone
        if target_zone == 1:
            target_hr = resting_hr + hr_reserve * 0.55  # Mid zone 1
        elif target_zone == 2:
            target_hr = resting_hr + hr_reserve * 0.65  # Mid zone 2
        elif target_zone == 3:
            target_hr = resting_hr + hr_reserve * 0.75  # Mid zone 3
        elif target_zone == 4:
            target_hr = resting_hr + hr_reserve * 0.85  # Mid zone 4
        elif target_zone == 5:
            target_hr = resting_hr + hr_reserve * 0.95  # Mid zone 5
        
        # Calculate adjustment
        hr_diff = self.current_hr - target_hr
        base_speed = self.base_speed_slider.value
        max_adjustment = self.max_adjust_slider.value
        response_factor = self.response_slider.value / 10
        
        speed_adjustment = (hr_diff / 10) * response_factor * -1  # Negative because if HR is high, decrease speed
        speed_adjustment = max(-max_adjustment, min(max_adjustment, speed_adjustment))
        
        new_speed = base_speed + speed_adjustment
        new_speed = max(1, min(20, new_speed))
        
        # Update treadmill display
        self.speed_slider.value = new_speed
    
    def update(self, dt):
        """Main update loop that runs every second"""
        # Update workout data if active
        if self.is_workout_active:
            self.workout_seconds += 1
            minutes = self.workout_seconds // 60
            seconds = self.workout_seconds % 60
            self.time_label.text = f'{minutes:02d}:{seconds:02d}'
            
            # Update graph data if we have heart rate data
            if self.current_hr > 0:
                self.hr_history.append(self.current_hr)
                self.time_points.append(self.workout_seconds / 60)  # Convert to minutes
                
                # Update plot (keep last 10 minutes or less)
                display_points = min(len(self.hr_history), 600)  # 10 minutes at 1 second intervals
                self.plot.points = [(self.time_points[-i], self.hr_history[-i]) 
                                   for i in range(1, display_points + 1)][::-1]
                
                # Update xmax for graph if needed
                current_time = self.workout_seconds / 60
                if current_time > self.graph.xmax:
                    self.graph.xmax = max(10, current_time + 1)
            
            # Update calories
            weight = float(self.weight_input.text) if self.weight_input.text else 70
            workout_minutes = self.workout_seconds / 60
            self.calories_burned = self.hr_controller.calculate_calories(self.current_hr, workout_minutes, weight)
            self.calories_label.text = str(self.calories_burned)
            
            # If in auto mode, adjust speed based on heart rate
            if self.auto_mode and self.active_manager.get_heart_rate() > 0:  # Updated
                self.adjust_speed_based_on_hr()


if __name__ == '__main__':
    try:
        # Set up global exception handler
        inject_exception_handler()
        
        # Log startup information
        log_startup_info()
        
        # Start the app
        log_info("Starting HeartRateMonitorApp")
        HeartRateMonitorApp().run()
    except Exception as e:
        log_error("Failed to start the application", e)
        print(f"Error starting app: {e}")
        import traceback
        traceback.print_exc()