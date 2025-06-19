import logging
import multiprocessing as mp
import queue
import time
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class ICAProcessService(QObject):
    """
    Service for managing a dedicated ICA process.

    This service creates and manages a persistent process that handles all ICA-related
    operations including computation, visualization, and export operations.
    """

    # Signals for communication with UI
    ica_computed = pyqtSignal(bool, dict, str)  # success, results, message
    visualization_ready = pyqtSignal(bool, str)  # success, message
    export_progress = pyqtSignal(int, str)  # percent, status
    export_completed = pyqtSignal(bool, str)  # success, message

    def __init__(self) -> None:
        """Initialize the ICA process service."""
        super().__init__()

        # Process management
        self._ica_process: Optional[mp.Process] = None
        self._command_queue: Optional[mp.Queue] = None
        self._response_queue: Optional[mp.Queue] = None
        self._is_initialized = False

        # Communication timer
        self._communication_timer: Optional[QTimer] = None

        # Current ICA results
        self._current_ica_results = None

        # Visualization state
        self._visualization_active = False
        self._current_colormap = "viridis"

    def initialize(self) -> bool:
        """Initialize the dedicated ICA process."""
        try:
            if self._is_initialized:
                return True

            # Create communication queues
            self._command_queue = mp.Queue()
            self._response_queue = mp.Queue()

            # Start the dedicated ICA process
            self._ica_process = mp.Process(
                target=_ica_worker_process,
                args=(self._command_queue, self._response_queue),
            )
            self._ica_process.start()

            # Start communication timer to check responses
            self._communication_timer = QTimer()
            self._communication_timer.timeout.connect(self._check_responses)
            self._communication_timer.start(50)  # Check every 50ms

            self._is_initialized = True
            logging.info("ICA process service initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Error initializing ICA process service: {e}")
            return False

    def compute_ica(
        self, ica_data: Any, params: Dict[str, Any], sampling_rate: float
    ) -> None:
        """Request ICA computation in the dedicated process."""
        if not self._is_initialized or self._command_queue is None:
            self.ica_computed.emit(False, {}, "ICA process not initialized")
            return

        try:
            command = {
                "type": "compute_ica",
                "data": ica_data,
                "params": params,
                "sampling_rate": sampling_rate,
            }
            self._command_queue.put(command)

        except Exception as e:
            logging.error(f"Error sending ICA computation request: {e}")
            self.ica_computed.emit(False, {}, f"Error sending request: {str(e)}")

    def visualize_ica(
        self,
        ica_components: Dict[str, Any],
        sampling_rate: float,
        colormap: str = "viridis",
    ) -> None:
        """Request ICA visualization in the dedicated process."""
        if not self._is_initialized or self._command_queue is None:
            self.visualization_ready.emit(False, "ICA process not initialized")
            return

        try:
            # Determine if this should be an update or new visualization
            is_realtime = ica_components.get("realtime", False)

            if is_realtime and self._visualization_active:
                # Real-time update to existing visualization
                command = {
                    "type": "update_visualization",
                    "ica_components": ica_components,
                    "sampling_rate": sampling_rate,
                    "colormap": colormap,
                }
            else:
                # New visualization (either manual request or first real-time)
                command = {
                    "type": "visualize_ica",
                    "ica_components": ica_components,
                    "sampling_rate": sampling_rate,
                    "colormap": colormap,
                }
                # Mark that visualization will be active
                self._visualization_active = True

            self._command_queue.put(command)
            self._current_colormap = colormap

        except Exception as e:
            logging.error(f"Error sending ICA visualization request: {e}")
            self.visualization_ready.emit(False, f"Error sending request: {str(e)}")

    def close_visualization(self) -> None:
        """Close the visualization dialog."""
        if not self._is_initialized or self._command_queue is None:
            return

        try:
            command = {"type": "close_visualization"}
            self._command_queue.put(command)
            self._visualization_active = False
        except Exception as e:
            logging.error(f"Error sending close visualization request: {e}")

    def export_ica_overview(
        self,
        ica_components: Dict[str, Any],
        colormap: str,
        sampling_rate: float,
        filename: str,
    ) -> None:
        """Request ICA overview export in the dedicated process."""
        if not self._is_initialized or self._command_queue is None:
            self.export_completed.emit(False, "ICA process not initialized")
            return

        try:
            command = {
                "type": "export_overview",
                "ica_components": ica_components,
                "colormap": colormap,
                "sampling_rate": sampling_rate,
                "filename": filename,
            }
            self._command_queue.put(command)

        except Exception as e:
            logging.error(f"Error sending ICA export overview request: {e}")
            self.export_completed.emit(False, f"Error sending request: {str(e)}")

    def export_ica_all(
        self,
        ica_components: Dict[str, Any],
        colormap: str,
        sampling_rate: float,
        directory: str,
    ) -> None:
        """Request export all ICA images in the dedicated process."""
        if not self._is_initialized or self._command_queue is None:
            self.export_completed.emit(False, "ICA process not initialized")
            return

        try:
            command = {
                "type": "export_all",
                "ica_components": ica_components,
                "colormap": colormap,
                "sampling_rate": sampling_rate,
                "directory": directory,
            }
            self._command_queue.put(command)

        except Exception as e:
            logging.error(f"Error sending ICA export all request: {e}")
            self.export_completed.emit(False, f"Error sending request: {str(e)}")

    def cancel_current_operation(self) -> None:
        """Cancel the current operation in the ICA process."""
        if not self._is_initialized or self._command_queue is None:
            return

        try:
            command = {"type": "cancel"}
            self._command_queue.put(command)
        except Exception as e:
            logging.error(f"Error sending cancel request: {e}")

    def get_current_ica_results(self) -> Optional[Dict[str, Any]]:
        """Get the current ICA results."""
        return self._current_ica_results

    def is_visualization_active(self) -> bool:
        """Check if visualization is currently active."""
        return self._visualization_active

    def _check_responses(self) -> None:
        """Check for responses from the ICA process."""
        if self._response_queue is None:
            return

        try:
            while not self._response_queue.empty():
                try:
                    response = self._response_queue.get_nowait()
                    self._handle_response(response)
                except queue.Empty:
                    break

        except Exception as e:
            logging.error(f"Error checking ICA process responses: {e}")

    def _handle_response(self, response: Dict[str, Any]) -> None:
        """Handle a response from the ICA process."""
        try:
            response_type = response.get("type", "unknown")

            if response_type == "ica_computed":
                success = response.get("success", False)
                if success:
                    self._current_ica_results = response.get("results", {})
                self.ica_computed.emit(
                    success, response.get("results", {}), response.get("message", "")
                )

            elif response_type == "visualization_ready":
                self.visualization_ready.emit(
                    response.get("success", False), response.get("message", "")
                )

            elif response_type == "visualization_updated":
                # Silently handle updates - no need to emit signal for updates
                pass

            elif response_type == "visualization_closed":
                self._visualization_active = False

            elif response_type == "export_progress":
                self.export_progress.emit(
                    response.get("percent", 0), response.get("status", "")
                )

            elif response_type == "export_completed":
                self.export_completed.emit(
                    response.get("success", False), response.get("message", "")
                )

            elif response_type == "error":
                logging.error(
                    f"ICA process error: {response.get('message', 'Unknown error')}"
                )

        except Exception as e:
            logging.error(f"Error handling ICA process response: {e}")

    def cleanup(self) -> None:
        """Clean up the ICA process service."""
        try:
            if self._communication_timer:
                self._communication_timer.stop()
                self._communication_timer = None

            if self._ica_process and self._ica_process.is_alive():
                # Send shutdown command
                try:
                    if self._command_queue is not None:
                        command = {"type": "shutdown"}
                        self._command_queue.put(command)

                    # Wait for graceful shutdown
                    self._ica_process.join(timeout=5)

                    if self._ica_process.is_alive():
                        self._ica_process.terminate()
                        self._ica_process.join(timeout=3)

                        if self._ica_process.is_alive():
                            self._ica_process.kill()
                except:
                    pass

            self._is_initialized = False
            self._visualization_active = False
            logging.info("ICA process service cleaned up")

        except Exception as e:
            logging.error(f"Error cleaning up ICA process service: {e}")


def _ica_worker_process(command_queue: mp.Queue, response_queue: mp.Queue) -> None:
    """
    Worker process for ICA operations.

    This process handles all ICA computations, visualizations, and exports
    in a separate process to avoid blocking the main UI.
    """
    try:
        # Configure matplotlib for Qt use in the worker process
        import sys
        import os

        import matplotlib

        matplotlib.use("Qt5Agg")
        import matplotlib.pyplot as plt
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
        import numpy as np

        # Create a QApplication for this process (needed for Qt widgets)
        app = QApplication(sys.argv)

        # Apply dark theme to this process
        _apply_dark_theme_to_process(app)

        # Process state
        current_dialog = None
        current_operation = None
        dialog_check_timer = None

        def check_dialog_status() -> None:
            """Check if dialog is still alive and notify main process if closed."""
            nonlocal current_dialog
            if current_dialog is not None:
                try:
                    if not current_dialog.isVisible():
                        # Dialog was closed
                        current_dialog = None
                        response_queue.put(
                            {"type": "visualization_closed", "success": True}
                        )
                        if dialog_check_timer:
                            dialog_check_timer.stop()
                except:
                    # Dialog object is invalid, consider it closed
                    current_dialog = None
                    response_queue.put(
                        {"type": "visualization_closed", "success": True}
                    )
                    if dialog_check_timer:
                        dialog_check_timer.stop()

        # Timer to check dialog status
        dialog_check_timer = QTimer()
        dialog_check_timer.timeout.connect(check_dialog_status)

        # Main process loop
        while True:
            try:
                # Check for commands
                if not command_queue.empty():
                    command = command_queue.get()
                    command_type = command.get("type", "unknown")

                    if command_type == "shutdown":
                        break

                    elif command_type == "cancel":
                        current_operation = None

                    elif command_type == "close_visualization":
                        if current_dialog:
                            current_dialog.close()
                            current_dialog = None
                        if dialog_check_timer and dialog_check_timer.isActive():
                            dialog_check_timer.stop()
                        response_queue.put(
                            {"type": "visualization_closed", "success": True}
                        )

                    elif command_type == "compute_ica":
                        current_operation = "compute_ica"
                        _handle_ica_computation(command, response_queue)
                        current_operation = None

                    elif command_type == "visualize_ica":
                        current_operation = "visualize_ica"
                        ica_components = command.get("ica_components", {})
                        is_realtime = ica_components.get("realtime", False)

                        # For real-time, if dialog exists, update it; otherwise create new
                        if is_realtime and current_dialog is not None:
                            # Update existing dialog
                            try:
                                colormap = command.get("colormap", "viridis")
                                current_dialog.update_visualization(
                                    ica_components, colormap
                                )
                                response_queue.put(
                                    {
                                        "type": "visualization_updated",
                                        "success": True,
                                        "message": "Real-time ICA visualization updated",
                                    }
                                )
                            except Exception as e:
                                # If update fails, create new dialog
                                current_dialog = _handle_ica_visualization(
                                    command, response_queue
                                )
                                if current_dialog and not dialog_check_timer.isActive():
                                    dialog_check_timer.start(1000)  # Check every second
                        else:
                            # Create new dialog (manual request or first real-time)
                            if current_dialog:
                                current_dialog.close()
                                current_dialog = None

                            current_dialog = _handle_ica_visualization(
                                command, response_queue
                            )

                            # Start monitoring dialog if it was created successfully
                            if current_dialog:
                                if not dialog_check_timer.isActive():
                                    dialog_check_timer.start(1000)  # Check every second

                        current_operation = None

                    elif command_type == "update_visualization":
                        current_operation = "update_visualization"
                        if current_dialog:
                            try:
                                ica_components = command["ica_components"]
                                colormap = command.get("colormap", "viridis")
                                current_dialog.update_visualization(
                                    ica_components, colormap
                                )
                                response_queue.put(
                                    {
                                        "type": "visualization_updated",
                                        "success": True,
                                        "message": "ICA visualization updated",
                                    }
                                )
                            except Exception as e:
                                response_queue.put(
                                    {
                                        "type": "visualization_updated",
                                        "success": False,
                                        "message": f"Error updating visualization: {str(e)}",
                                    }
                                )
                        else:
                            # No dialog exists, create new one (fallback)
                            current_dialog = _handle_ica_visualization(
                                command, response_queue
                            )
                            if current_dialog and not dialog_check_timer.isActive():
                                dialog_check_timer.start(1000)
                        current_operation = None

                    elif command_type == "export_overview":
                        current_operation = "export_overview"
                        _handle_ica_export_overview(command, response_queue)
                        current_operation = None

                    elif command_type == "export_all":
                        current_operation = "export_all"
                        _handle_ica_export_all(command, response_queue)
                        current_operation = None

                # Process Qt events
                app.processEvents()
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage

            except Exception as e:
                response_queue.put(
                    {
                        "type": "error",
                        "message": f"Error in ICA worker process: {str(e)}",
                    }
                )

        # Cleanup
        if dialog_check_timer and dialog_check_timer.isActive():
            dialog_check_timer.stop()
        if current_dialog:
            current_dialog.close()
        app.quit()

    except Exception as e:
        response_queue.put(
            {"type": "error", "message": f"Fatal error in ICA worker process: {str(e)}"}
        )


def _apply_dark_theme_to_process(app: Any) -> None:
    """Apply dark theme to the ICA process."""
    try:
        from ...utils.theme_manager import ThemeManager

        theme_manager = ThemeManager()
        theme_manager.apply_dark_theme(app)
    except Exception as e:
        # Fallback manual theme application
        dark_style = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QDialog {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QPushButton {
            background-color: #404040;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QComboBox {
            background-color: #404040;
            border: 1px solid #555555;
            padding: 3px;
        }
        QLabel {
            color: #ffffff;
        }
        """
        app.setStyleSheet(dark_style)


def _handle_ica_computation(command: Dict[str, Any], response_queue: mp.Queue) -> None:
    """Handle ICA computation in the worker process."""
    try:
        # Import processor
        from ...processors.signal_processor import SignalProcessor

        ica_data = command["data"]
        params = command["params"]
        sampling_rate = command["sampling_rate"]

        # Initialize processor with sampling rate
        processor = SignalProcessor(sampling_rate)

        # Compute ICA
        w, k, a, s = processor.perform_ica(ica_data, params["num_components"])

        if w is not None:
            ica_components = {
                "w": w,
                "k": k,
                "a": a,
                "s": s,
                "selected_channels": params["selected_channels"],
                "num_components": params["num_components"],
            }

            response_queue.put(
                {
                    "type": "ica_computed",
                    "success": True,
                    "results": ica_components,
                    "message": f"ICA computed successfully with {params['num_components']} components",
                }
            )
        else:
            response_queue.put(
                {
                    "type": "ica_computed",
                    "success": False,
                    "results": {},
                    "message": "ICA computation failed",
                }
            )

    except Exception as e:
        response_queue.put(
            {
                "type": "ica_computed",
                "success": False,
                "results": {},
                "message": f"Error computing ICA: {str(e)}",
            }
        )


def _handle_ica_visualization(command: Dict[str, Any], response_queue: mp.Queue) -> Any:
    """Handle ICA visualization in the worker process."""
    try:
        from ...ui.advanced.dialogs.ica_visualization_dialog import (
            ICAVisualizationDialog,
        )

        ica_components = command["ica_components"]
        sampling_rate = command["sampling_rate"]
        colormap = command.get("colormap", "viridis")

        # Create and show visualization dialog
        dialog = ICAVisualizationDialog(
            ica_components=ica_components, sampling_rate=sampling_rate, parent=None
        )

        # Set the colormap
        for i in range(dialog.colormap_combo.count()):
            if dialog.colormap_combo.itemData(i) == colormap:
                dialog.colormap_combo.setCurrentIndex(i)
                break

        dialog.show()

        response_queue.put(
            {
                "type": "visualization_ready",
                "success": True,
                "message": "ICA visualization dialog opened",
            }
        )

        return dialog

    except Exception as e:
        response_queue.put(
            {
                "type": "visualization_ready",
                "success": False,
                "message": f"Error creating ICA visualization: {str(e)}",
            }
        )
        return None


def _handle_ica_export_overview(
    command: Dict[str, Any], response_queue: mp.Queue
) -> None:
    """Handle ICA overview export in the worker process."""
    try:
        from ...services.ica.export_service import _export_enhanced_overview_worker

        # Create a new process for the actual export work
        export_queue: mp.Queue = mp.Queue()

        export_process = mp.Process(
            target=_export_enhanced_overview_worker, args=(command, export_queue)
        )
        export_process.start()

        # Monitor export progress
        while export_process.is_alive():
            if not export_queue.empty():
                result = export_queue.get()
                if result["type"] == "progress":
                    response_queue.put(
                        {
                            "type": "export_progress",
                            "percent": result["percent"],
                            "status": result["status"],
                        }
                    )
                elif result["type"] == "finished":
                    response_queue.put(
                        {
                            "type": "export_completed",
                            "success": result["success"],
                            "message": result["message"],
                        }
                    )
                    break
                elif result["type"] == "error":
                    response_queue.put(
                        {
                            "type": "export_completed",
                            "success": False,
                            "message": f"Export error: {result['error']}",
                        }
                    )
                    break
            time.sleep(0.1)

        export_process.join()

    except Exception as e:
        response_queue.put(
            {
                "type": "export_completed",
                "success": False,
                "message": f"Error in export overview: {str(e)}",
            }
        )


def _handle_ica_export_all(command: Dict[str, Any], response_queue: mp.Queue) -> None:
    """Handle export all ICA images in the worker process."""
    try:
        from ...services.ica.export_service import _export_enhanced_all_images_worker

        # Create a new process for the actual export work
        export_queue: mp.Queue = mp.Queue()

        export_process = mp.Process(
            target=_export_enhanced_all_images_worker, args=(command, export_queue)
        )
        export_process.start()

        # Monitor export progress
        while export_process.is_alive():
            if not export_queue.empty():
                result = export_queue.get()
                if result["type"] == "progress":
                    response_queue.put(
                        {
                            "type": "export_progress",
                            "percent": result["percent"],
                            "status": result["status"],
                        }
                    )
                elif result["type"] == "finished":
                    response_queue.put(
                        {
                            "type": "export_completed",
                            "success": result["success"],
                            "message": result["message"],
                        }
                    )
                    break
                elif result["type"] == "error":
                    response_queue.put(
                        {
                            "type": "export_completed",
                            "success": False,
                            "message": f"Export error: {result['error']}",
                        }
                    )
                    break
            time.sleep(0.1)

        export_process.join()

    except Exception as e:
        response_queue.put(
            {
                "type": "export_completed",
                "success": False,
                "message": f"Error in export all: {str(e)}",
            }
        )


def _handle_ica_visualization_update(
    dialog: Any, command: Dict[str, Any], response_queue: mp.Queue
) -> None:
    """Handle ICA visualization update for existing dialog."""
    try:
        ica_components = command["ica_components"]
        sampling_rate = command["sampling_rate"]
        colormap = command.get("colormap", "viridis")

        # Update the dialog with new components
        dialog.update_visualization(ica_components, colormap)

        response_queue.put(
            {
                "type": "visualization_updated",
                "success": True,
                "message": "ICA visualization updated",
            }
        )

    except Exception as e:
        response_queue.put(
            {
                "type": "visualization_updated",
                "success": False,
                "message": f"Error updating ICA visualization: {str(e)}",
            }
        )
