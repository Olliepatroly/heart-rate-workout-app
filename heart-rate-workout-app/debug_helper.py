import logging
import os
import sys
import traceback
from datetime import datetime

# Configure logging
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = f"hr_app_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Create logger
logger = logging.getLogger('HRMonitorApp')
logger.setLevel(LOG_LEVEL)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(console_handler)

# Create file handler
try:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
except Exception as e:
    print(f"Warning: Could not create log file. {e}")

def log_info(message):
    """Log an info message"""
    logger.info(message)
    
def log_error(message, exception=None):
    """Log an error message with optional exception details"""
    if exception:
        logger.error(f"{message}: {exception}")
        logger.error(traceback.format_exc())
    else:
        logger.error(message)
        
def log_debug(message):
    """Log a debug message"""
    logger.debug(message)
    
def log_warning(message):
    """Log a warning message"""
    logger.warning(message)

def log_exception(message="Uncaught exception"):
    """Log the current exception"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    logger.error(f"{message}: {exc_value}")
    logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

def get_platform_info():
    """Get information about the current platform"""
    import platform
    
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version()
    }
    
    # Add kivy version if available
    try:
        import kivy
        info["kivy_version"] = kivy.__version__
    except:
        info["kivy_version"] = "Not available"
        
    # Add bleak version if available
    try:
        import bleak
        info["bleak_version"] = bleak.__version__
    except:
        info["bleak_version"] = "Not available"
    
    return info

def log_startup_info():
    """Log platform and environment information at startup"""
    info = get_platform_info()
    
    log_info("=" * 50)
    log_info("HR Monitor App Starting")
    log_info("=" * 50)
    log_info(f"Platform: {info['system']} {info['release']} ({info['version']})")
    log_info(f"Machine: {info['machine']} - Processor: {info['processor']}")
    log_info(f"Python: {info['python_version']}")
    log_info(f"Kivy: {info['kivy_version']}")
    log_info(f"Bleak: {info['bleak_version']}")
    log_info("=" * 50)

def inject_exception_handler():
    """Set up global exception handler to log unhandled exceptions"""
    original_hook = sys.excepthook
    
    def exception_hook(exc_type, exc_value, traceback_obj):
        log_error(f"Unhandled {exc_type.__name__}: {exc_value}")
        log_error("".join(traceback.format_exception(exc_type, exc_value, traceback_obj)))
        return original_hook(exc_type, exc_value, traceback_obj)
    
    sys.excepthook = exception_hook