"""
Configuration module for the CLI.

This module contains shared configuration and state used across CLI components.
"""

import time
import sys
import os
import asyncio
import threading
from typing import Optional, List, Dict, Any

from ..core.event_system import EventType, subscribe, unsubscribe
from ..data_access_api import InputDataAPI
from ..interaction_api import InputCollectorAPI

# Global state variables
headless_mode = False
headless_app = None
gui_mode = False

def set_gui_mode(enabled: bool):
    """Set whether CLI is running alongside GUI."""
    global gui_mode
    gui_mode = enabled

def get_gui_mode() -> bool:
    """Check if CLI is running alongside GUI."""
    global gui_mode
    return gui_mode

class HeadlessInputCollector:
    """
    Headless version of Input Collector for CLI use.
    
    This class initializes the core components needed to run the Input Collector
    without a GUI, making it usable via CLI.
    """
    
    def __init__(self):
        """Initialize the headless input collector."""
        # Import inside method to avoid circular imports
        from rich.console import Console
        self.console = Console()
        
        self.console.print("[yellow]Initializing headless input collector...[/yellow]")
        
        # Initialize components in the right order
        self._setup_components()
        self._connect_components()
        self._initialize_apis()
        
        self.console.print("[green]Headless input collector initialized successfully[/green]")
    
    def _setup_components(self):
        """Set up the core components needed for the input collector."""
        from ..collectors import CollectorManager
        from ..logging import LoggingManager
        from ..processing import EventProcessor
        from ..app import AppCoordinator
        from ..ui import UIManager, VisualizerManager
        
        # Create components (similar to GUI version but without actual UI rendering)
        self.collector_manager = CollectorManager()
        self.event_processor = EventProcessor()
        self.logging_manager = LoggingManager()
        
        # Create minimal UI manager that provides the API interface but no actual UI
        self.ui_manager = UIManager(None)  # Pass None as parent since we have no QWidget
        self.ui_manager.headless_mode = True  # Signal that we're in headless mode
        
        # Create visualizer manager with no actual visualizers
        self.visualizer_manager = self._create_visualizer_manager()
        
        # Create app coordinator last since it depends on all other components
        self.app_coordinator = AppCoordinator(
            self.collector_manager,
            self.ui_manager,
            self.logging_manager,
            self.event_processor
        )
    
    def _create_visualizer_manager(self):
        """Create a minimal visualizer manager for headless mode."""
        from ..ui import VisualizerManager
        
        # Create headless visualizer manager
        visualizer_manager = VisualizerManager(None)  # No parent widget
        visualizer_manager.headless_mode = True
        
        return visualizer_manager
        
    def _connect_components(self):
        """Connect signals between components."""
        # Since we're not using Qt signals in headless mode,
        # we'll use direct method calls where needed
        
        # Register the basic tracked keys
        self.tracked_keys = [
            "w", "a", "s", "d", "q", "e", "f", "m", "c", "b", "1", "2", "3", "4",
            "Key.space", "Key.shift", "Key.media_play_pause", "Button.left", "Button.right",
        ]
        
        # Initialize app coordinator with tracked keys
        self.app_coordinator.initialize(self.tracked_keys)
    
    def _initialize_apis(self):
        """Initialize the APIs."""
        # Initialize the interaction API with application components
        InputCollectorAPI.initialize(
            self.app_coordinator,
            self.ui_manager,
            self.logging_manager,
            self.collector_manager,
            self.event_processor
        )
        
        # Data Access API is automatically initialized with DataAccessService
    
    def shutdown(self):
        """Clean up resources."""
        try:
            # Stop any active collectors
            if hasattr(self, 'collector_manager'):
                self.collector_manager.stop_capture()
            
            # Close any log files
            if hasattr(self, 'logging_manager'):
                self.logging_manager.close_all()
        except Exception as e:
            print(f"Error during headless shutdown: {e}")

def init_headless_mode():
    """Initialize headless mode for CLI application."""
    global headless_mode, headless_app
    
    headless_mode = True
    if headless_app is None:
        headless_app = HeadlessInputCollector()
    
    return headless_app

# Thread management
cli_running = threading.Event()

def set_cli_running(running: bool):
    """Set whether the CLI is currently running."""
    if running:
        cli_running.set()
    else:
        cli_running.clear()

def is_cli_running() -> bool:
    """Check if the CLI is currently running."""
    return cli_running.is_set()

def wait_for_cli_exit(timeout: float = None):
    """Wait for the CLI to exit."""
    return not cli_running.wait(timeout)
