#!/usr/bin/env python3
"""
Heart Rate Monitor App Launcher

This script provides a reliable way to start the heart rate monitor app
by setting up the event loop and error handling before importing Kivy.
"""

import os
import sys
import traceback
import asyncio
import platform

def setup_environment():
    """Set up environment variables needed by Kivy and other libraries"""
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Set up Kivy environment variables
    if platform.system() == 'Darwin':  # macOS
        os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'  # More reliable on macOS
    
    # Disable Kivy's usage statistics collection
    os.environ['KIVY_NO_CONSOLELOG'] = '1'
    os.environ['KIVY_NO_ARGS'] = '1'

def setup_logging():
    """Set up basic logging before importing our debug_helper"""
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('HRApp-Launcher')

def main():
    """Main entry point for the application"""
    # Set up basic environment and logging
    setup_environment()
    logger = setup_logging()
    logger.info("Starting Heart Rate Monitor App")
    
    try:
        # Set up asyncio event loop before importing Kivy
        if platform.system() == 'Windows':
            # Windows requires specific asyncio setup
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create and set the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info(f"Created asyncio event loop: {loop}")
        
        # Now we can safely import and run our app
        logger.info("Importing main application")
        
        # Import the actual app
        from main import HeartRateMonitorApp
        
        # Run the app
        logger.info("Starting Kivy application")
        HeartRateMonitorApp().run()
        
    except Exception as e:
        logger.error(f"Failed to start the application: {e}")
        traceback.print_exc()
        
        # On GUI platforms, show an error dialog
        try:
            if platform.system() == 'Windows':
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, 
                    f"Error starting the Heart Rate Monitor App:\n\n{e}\n\nSee log file for details.", 
                    "Application Error", 0x10)
            elif platform.system() == 'Darwin':
                os.system(f'''osascript -e 'display dialog "Error starting the Heart Rate Monitor App:\n\n{e}\n\nSee log file for details." buttons {"OK"} default button "OK" with icon stop with title "Application Error"' ''')
        except:
            pass
        
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())