"""
Configuration module for the EEG Processor CLI.

This module contains shared configuration and state used across CLI components.
"""

from __future__ import annotations
import threading
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from ..data_access_api import EEGDataAPI
    from ..interaction_api import EEGProcessorInteractionAPI

# Global state for CLI operation
headless_mode = False
headless_app: Optional[Any] = None
gui_mode = False

# Track main thread for signal handling
_main_thread_id = threading.main_thread().ident

# Thread management
cli_running = threading.Event()


def set_gui_mode(enabled: bool) -> None:
    """Set whether CLI is running alongside GUI."""
    global gui_mode
    gui_mode = enabled


def get_gui_mode() -> bool:
    """Check if CLI is running alongside GUI."""
    global gui_mode
    return gui_mode


def is_main_thread() -> bool:
    """Check if currently running in the main thread."""
    return threading.current_thread().ident == _main_thread_id


def set_cli_running(running: bool) -> None:
    """Set whether the CLI is currently running."""
    if running:
        cli_running.set()
    else:
        cli_running.clear()


def is_cli_running() -> bool:
    """Check if the CLI is currently running."""
    return cli_running.is_set()


def wait_for_cli_exit(timeout: Optional[float] = None) -> bool:
    """Wait for the CLI to exit."""
    return not cli_running.wait(timeout)


class HeadlessEEGProcessor:
    """
    Headless version of EEG Processor for CLI use.

    This class initializes the core components needed to run the EEG Processor
    without a GUI, making it usable via CLI.
    """

    def __init__(self):
        """Initialize headless EEG processor."""
        from rich.console import Console
        
        self.console = Console()
        self.console.print("[yellow]Initializing headless EEG processor...[/yellow]")
        
        # Initialize components in the right order
        self._setup_services()
        self._initialize_apis()
        
        self.console.print("[green]Headless EEG processor initialized successfully[/green]")

    def _setup_services(self) -> None:
        """Set up the core services needed for the EEG processor."""
        # Import and initialize data access service
        from ..services.data_access_service import DataAccessService
        self.data_service = DataAccessService.get_instance()
        
        # Import and initialize interaction service
        from ..services.interaction_service import InteractionService
        self.interaction_service = InteractionService.get_instance()
        
        # Import and initialize collector service
        from ..services.collector_service import CollectorService
        self.collector_service = CollectorService.get_instance()

    def _initialize_apis(self) -> None:
        """Initialize the APIs."""
        # APIs are typically auto-initialized through services
        pass

    def shutdown(self) -> None:
        """Clean up resources."""
        try:
            # Stop any active collectors
            if hasattr(self, "collector_service"):
                self.collector_service.cleanup()
                
            # Clean up other services if needed
            if hasattr(self, "data_service"):
                # Data service cleanup
                pass
        except Exception as e:
            print(f"Error during headless shutdown: {e}")


def init_headless_mode() -> HeadlessEEGProcessor:
    """Initialize headless mode for CLI application."""
    global headless_mode, headless_app

    headless_mode = True
    if headless_app is None:
        headless_app = HeadlessEEGProcessor()

    return headless_app


def get_data_service():
    """Get data access service instance."""
    if headless_mode and headless_app:
        return headless_app.data_service
    else:
        try:
            from ..services.data_access_service import DataAccessService
            return DataAccessService.get_instance()
        except Exception:
            return None


def get_interaction_service():
    """Get interaction service instance."""
    if headless_mode and headless_app:
        return headless_app.interaction_service
    else:
        try:
            from ..services.interaction_service import InteractionService
            return InteractionService.get_instance()
        except Exception:
            return None


def get_collector_service():
    """Get collector service instance."""
    if headless_mode and headless_app:
        return headless_app.collector_service
    else:
        try:
            from ..services.collector_service import CollectorService
            return CollectorService.get_instance()
        except Exception:
            return None


def initialize_headless_mode() -> bool:
    """Initialize EEG processor in headless mode for CLI."""
    global headless_mode
    
    if headless_mode:
        return True
        
    try:
        init_headless_mode()
        print("EEG Processor initialized in headless mode")
        return True
    except Exception as e:
        print(f"Error initializing headless mode: {e}")
        return False


def cleanup_headless_mode() -> None:
    """Clean up headless mode resources."""
    global headless_mode, headless_app
    
    try:
        if headless_app:
            headless_app.shutdown()
            
        headless_app = None
        headless_mode = False
        
    except Exception as e:
        print(f"Error cleaning up headless mode: {e}")