import asyncio
import threading
from functools import wraps
from kivy.clock import Clock
import sys

def install_asyncio_loop():
    """
    Set up asyncio to work with Kivy's event loop.
    Call this once at the start of your application.
    
    Returns:
        asyncio.AbstractEventLoop: The event loop
    """
    print("Setting up asyncio event loop integration with Kivy...")
    
    # Create a new event loop if needed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            print("Existing event loop is closed. Creating a new one.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No event loop in this thread
        print("No existing event loop found. Creating a new one.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    print(f"Using event loop: {loop}")
    
    # Create a callback function for Kivy's clock to service the asyncio loop
    def _async_service(_):
        try:
            # Process a batch of tasks from the event loop
            loop.call_soon(loop.stop)
            loop.run_forever()
        except Exception as e:
            print(f"Asyncio error in event loop servicing: {e}")
            import traceback
            traceback.print_exc()
    
    # Schedule the callback to run at regular intervals (30 times per second)
    Clock.schedule_interval(_async_service, 1/30)
    print("Asyncio integration complete. Event loop will be serviced by Kivy Clock.")
    
    return loop

def run_async(coroutine):
    """
    Decorator to run a coroutine in the asyncio event loop.
    Can be used to make async functions callable from sync code.
    
    Args:
        coroutine: The coroutine function to run
        
    Returns:
        function: Wrapped function that returns a Task
    """
    @wraps(coroutine)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
            return asyncio.ensure_future(coroutine(*args, **kwargs))
        except Exception as e:
            print(f"Asyncio error in run_async: {e}")
            import traceback
            traceback.print_exc()
            return None
    return wrapper

def safe_create_task(coro):
    """
    Safely create an asyncio task, handling exceptions.
    
    Args:
        coro: The coroutine to schedule
        
    Returns:
        asyncio.Task or None: The created task or None if failed
    """
    try:
        loop = asyncio.get_event_loop()
        return asyncio.create_task(coro)
    except Exception as e:
        print(f"Error creating asyncio task: {e}")
        import traceback
        traceback.print_exc()
        return None