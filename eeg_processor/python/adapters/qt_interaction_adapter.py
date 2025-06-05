"""
Qt Interaction Adapter for synchronizing API changes with PyQt5 GUI.
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, QMetaObject, Qt, Q_ARG
from PyQt5.QtWidgets import QApplication

from ..core.event_system import EventSystem, EventType, Event


class QtInteractionAdapter(QObject):
    """
    Adapter to synchronize API interactions with Qt GUI components.

    This class listens to events from the event system and updates
    the corresponding Qt GUI elements.
    """

    def __init__(self, main_app):
        """
        Initialize the Qt interaction adapter.

        Args:
            main_app: Reference to the main EEGProcessorApp instance
        """
        super().__init__()
        self.main_app = main_app
        self.event_system = EventSystem.get_instance()

        # Subscribe to relevant events
        self._subscribe_to_events()

        logging.info("Qt interaction adapter initialized")

    def _subscribe_to_events(self):
        """Subscribe to events that need GUI updates."""
        # Connection events
        self.event_system.subscribe(EventType.BOARD_CONNECT, self._handle_board_connect)
        self.event_system.subscribe(
            EventType.BOARD_DISCONNECT, self._handle_board_disconnect
        )
        self.event_system.subscribe(EventType.STREAM_START, self._handle_stream_start)
        self.event_system.subscribe(EventType.STREAM_STOP, self._handle_stream_stop)

        # Processing events
        self.event_system.subscribe(EventType.FILTER_APPLY, self._handle_filter_apply)
        self.event_system.subscribe(
            EventType.VISUALIZATION_START, self._handle_visualization_start
        )
        self.event_system.subscribe(
            EventType.VISUALIZATION_STOP, self._handle_visualization_stop
        )

        # Recording events
        self.event_system.subscribe(
            EventType.RECORDING_START, self._handle_recording_start
        )
        self.event_system.subscribe(
            EventType.RECORDING_STOP, self._handle_recording_stop
        )

        # UI update events
        self.event_system.subscribe(
            EventType.UI_UPDATE_STATUS, self._handle_ui_update_status
        )
        self.event_system.subscribe(
            EventType.UI_UPDATE_CONTROLS, self._handle_ui_update_controls
        )

    def _safe_qt_call(self, method, *args):
        """
        Safely call a Qt method from any thread.

        Args:
            method: Method to call
            *args: Arguments for the method
        """
        try:
            if QApplication.instance() and hasattr(method, "__self__"):
                QMetaObject.invokeMethod(
                    method.__self__,
                    method.__name__,
                    Qt.QueuedConnection,
                    *[Q_ARG(type(arg), arg) for arg in args],
                )
            else:
                # Fallback for simple calls
                method(*args)
        except Exception as e:
            logging.error(f"Error in Qt call: {e}")

    def _handle_board_connect(self, event: Event):
        """Handle board connection events."""
        try:
            board_id = event.data.get("board_id")
            params = event.data.get("params", {})
            preset = event.data.get("preset", 0)

            # Update connection panel
            if hasattr(self.main_app, "connection_panel"):
                panel = self.main_app.connection_panel

                # Update board selection if provided
                if board_id is not None and hasattr(panel, "board_type_combo"):
                    self._safe_qt_call(
                        self._set_combo_by_data, panel.board_type_combo, board_id
                    )

                # Update preset if provided
                if hasattr(panel, "preset_combo"):
                    self._safe_qt_call(
                        self._set_combo_by_data, panel.preset_combo, preset
                    )

                # Update connection parameters
                if params and hasattr(panel, "_update_params_from_dict"):
                    self._safe_qt_call(panel._update_params_from_dict, params)

                # Update button states
                if hasattr(panel, "_update_connection_state"):
                    self._safe_qt_call(panel._update_connection_state, True)

            logging.info(f"GUI updated for board connection: {board_id}")

        except Exception as e:
            logging.error(f"Error handling board connect event: {e}")

    def _handle_board_disconnect(self, event: Event):
        """Handle board disconnection events."""
        try:
            # Extraer datos adicionales del evento
            force_update = event.data.get("force_ui_update", False)

            # Update connection panel
            if hasattr(self.main_app, "connection_panel"):
                panel = self.main_app.connection_panel

                # Siempre actualizar los controles
                if hasattr(panel, "_update_connection_state"):
                    self._safe_qt_call(panel._update_connection_state, False)

                # Forzar actualización adicional si se solicita
                if force_update and hasattr(panel, "disconnect_board"):
                    # Enviar una señal board_disconnected directamente
                    if hasattr(panel, "board_disconnected"):
                        self._safe_qt_call(lambda: panel.board_disconnected.emit())

                    # También actualizar texto de información de la placa
                    if hasattr(panel, "board_info_label"):
                        self._safe_qt_call(
                            panel.board_info_label.setText, "No board connected"
                        )

                # Asegurarnos que los botones de streaming estén en el estado correcto
                if hasattr(panel, "start_stream_btn"):
                    self._safe_qt_call(panel.start_stream_btn.setEnabled, False)
                if hasattr(panel, "stop_stream_btn"):
                    self._safe_qt_call(panel.stop_stream_btn.setEnabled, False)

            # También desactivar los paneles que dependen de la conexión
            if hasattr(self.main_app, "processing_panel"):
                self._safe_qt_call(
                    self.main_app.processing_panel.enable_processing, False
                )

            if hasattr(self.main_app, "recording_panel"):
                self._safe_qt_call(
                    self.main_app.recording_panel.enable_recording, False
                )

            # Actualizar el estado en collector_service de nuevo por si acaso
            try:
                from ..services.collector_service import CollectorService

                collector_service = CollectorService()
                collector_service._reset_connection_state()  # Llamar a un nuevo método que añadiremos
            except Exception as e_collector:
                logging.error(f"Error resetting collector state: {e_collector}")

            logging.info("GUI updated for board disconnection")

        except Exception as e:
            logging.error(f"Error handling board disconnect event: {e}")

    def _handle_stream_start(self, event: Event):
        """Handle stream start events."""
        try:
            # Update connection panel
            if hasattr(self.main_app, "connection_panel"):
                panel = self.main_app.connection_panel
                if hasattr(panel, "_update_streaming_state"):
                    self._safe_qt_call(panel._update_streaming_state, True)

            # Enable other panels
            if hasattr(self.main_app, "processing_panel"):
                self._safe_qt_call(
                    self.main_app.processing_panel.enable_processing, True
                )

            if hasattr(self.main_app, "recording_panel"):
                self._safe_qt_call(self.main_app.recording_panel.enable_recording, True)

            logging.info("GUI updated for stream start")

        except Exception as e:
            logging.error(f"Error handling stream start event: {e}")

    def _handle_stream_stop(self, event: Event):
        """Handle stream stop events."""
        try:
            # Update connection panel
            if hasattr(self.main_app, "connection_panel"):
                panel = self.main_app.connection_panel
                if hasattr(panel, "_update_streaming_state"):
                    self._safe_qt_call(panel._update_streaming_state, False)

            # Disable other panels
            if hasattr(self.main_app, "processing_panel"):
                self._safe_qt_call(
                    self.main_app.processing_panel.enable_processing, False
                )

            if hasattr(self.main_app, "recording_panel"):
                self._safe_qt_call(
                    self.main_app.recording_panel.enable_recording, False
                )

            logging.info("GUI updated for stream stop")

        except Exception as e:
            logging.error(f"Error handling stream stop event: {e}")

    def _handle_filter_apply(self, event: Event):
        """Handle filter application events."""
        try:
            filter_config = event.data.get("filter_config", {})

            # Update processing panel
            if hasattr(self.main_app, "processing_panel"):
                panel = self.main_app.processing_panel
                if hasattr(panel, "_update_filter_controls"):
                    self._safe_qt_call(panel._update_filter_controls, filter_config)

            logging.info("GUI updated for filter application")

        except Exception as e:
            logging.error(f"Error handling filter apply event: {e}")

    def _handle_visualization_start(self, event: Event):
        """Handle visualization start events."""
        try:
            viz_type = event.data.get("viz_type", "eeg")

            # Update connection panel visualization button
            if hasattr(self.main_app, "connection_panel"):
                panel = self.main_app.connection_panel
                if hasattr(panel, "update_visualization_button"):
                    self._safe_qt_call(panel.update_visualization_button, False)

            logging.info(f"GUI updated for {viz_type} visualization start")

        except Exception as e:
            logging.error(f"Error handling visualization start event: {e}")

    def _handle_visualization_stop(self, event: Event):
        """Handle visualization stop events."""
        try:
            # Update connection panel visualization button
            if hasattr(self.main_app, "connection_panel"):
                panel = self.main_app.connection_panel
                if hasattr(panel, "update_visualization_button"):
                    self._safe_qt_call(panel.update_visualization_button, True)

            logging.info("GUI updated for visualization stop")

        except Exception as e:
            logging.error(f"Error handling visualization stop event: {e}")

    def _handle_recording_start(self, event: Event):
        """Handle recording start events."""
        try:
            filename = event.data.get("filename", "")
            data_type = event.data.get("data_type", "raw")

            # Update recording panel
            if hasattr(self.main_app, "recording_panel"):
                panel = self.main_app.recording_panel
                if hasattr(panel, "_update_recording_state"):
                    self._safe_qt_call(
                        panel._update_recording_state, True, filename, data_type
                    )

            logging.info("GUI updated for recording start")

        except Exception as e:
            logging.error(f"Error handling recording start event: {e}")

    def _handle_recording_stop(self, event: Event):
        """Handle recording stop events."""
        try:
            # Update recording panel
            if hasattr(self.main_app, "recording_panel"):
                panel = self.main_app.recording_panel
                if hasattr(panel, "_update_recording_state"):
                    self._safe_qt_call(panel._update_recording_state, False)

            logging.info("GUI updated for recording stop")

        except Exception as e:
            logging.error(f"Error handling recording stop event: {e}")

    def _handle_ui_update_status(self, event: Event):
        """Handle UI status update events."""
        try:
            message = event.data.get("message", "")

            # Update main app status
            if hasattr(self.main_app, "show_status_message"):
                self._safe_qt_call(self.main_app.show_status_message, message)

            logging.debug(f"Status updated: {message}")

        except Exception as e:
            logging.error(f"Error handling UI status update: {e}")

    def _handle_ui_update_controls(self, event: Event):
        """Handle UI controls update events."""
        try:
            control_updates = event.data.get("controls", {})

            # Apply control updates
            for control_path, value in control_updates.items():
                self._update_control_value(control_path, value)

            logging.debug("Controls updated")

        except Exception as e:
            logging.error(f"Error handling UI controls update: {e}")

    def _set_combo_by_data(self, combo, data_value):
        """Set combo box selection by data value."""
        try:
            for i in range(combo.count()):
                if combo.itemData(i) == data_value:
                    combo.setCurrentIndex(i)
                    break
        except Exception as e:
            logging.error(f"Error setting combo value: {e}")

    def _update_control_value(self, control_path: str, value: Any):
        """
        Update a specific control value.

        Args:
            control_path: Path to the control (e.g., "connection_panel.board_type_combo")
            value: New value for the control
        """
        try:
            # Parse control path
            parts = control_path.split(".")
            obj = self.main_app

            # Navigate to the control
            for part in parts[:-1]:
                obj = getattr(obj, part, None)
                if obj is None:
                    return

            control_name = parts[-1]
            control = getattr(obj, control_name, None)

            if control is None:
                return

            # Update control based on type
            if hasattr(control, "setChecked"):
                self._safe_qt_call(control.setChecked, bool(value))
            elif hasattr(control, "setValue"):
                self._safe_qt_call(control.setValue, value)
            elif hasattr(control, "setText"):
                self._safe_qt_call(control.setText, str(value))
            elif hasattr(control, "setCurrentData"):
                self._safe_qt_call(control.setCurrentData, value)

        except Exception as e:
            logging.error(f"Error updating control {control_path}: {e}")
