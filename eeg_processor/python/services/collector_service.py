import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple, Union, Deque
from collections import deque

import numpy as np

from .data_access_service import DataAccessService
from ..collectors.board_configuration import BoardConfiguration
from ..collectors.eeg_collector import EEGCollector


class CollectorService:
    """
    Service for managing EEG data collection.

    This class provides an interface for connecting to EEG boards,
    streaming data, and managing the collector state.
    """

    def __init__(self) -> None:
        """Initialize the collector service."""
        self.collector: Optional[EEGCollector] = None
        self.is_streaming = False

        # Background data fetch thread
        self._data_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Sample rate metrics - REDISEÑADO COMPLETAMENTE
        self._sample_window_size = 5.0  # Ventana de 5 segundos para calcular la tasa media
        self._samples_timestamps: Deque[float] = deque(maxlen=1000)  # Marca de tiempo de las últimas 1000 muestras
        self._last_sample_count = 0
        self._current_sample_rate = 0.0
        self._last_timestamp = 0
        self._last_reported_time = 0
        self._report_interval = 0.5  # Actualizar la tasa cada 0.5 segundos

    def connect_to_board(
        self, board_id: int, params: Dict[str, Any], preset: int
    ) -> bool:
        """
        Connect to an EEG board.

        Args:
            board_id: ID of the board to connect to
            params: Dictionary of connection parameters
            preset: Data preset to use

        Returns:
            True if connection was successful, False otherwise
        """
        try:
            # Create input parameters from dictionary
            board_params = BoardConfiguration.create_input_params(board_id, params)

            # Create collector
            self.collector = EEGCollector(board_id, board_params, preset)
            if self.collector:
                self.collector.prepare_session()
                logging.info(f"Connected to board {board_id}")

                # Update metadata in DataAccessService
                data_access = DataAccessService.get_instance()

                # Update metadata with complete board info
                device_info = self.collector.get_device_info()

                # Update metadata with device info
                data_access.update_metadata(
                    {
                        "sampling_rate": device_info.get("sampling_rate", 0),
                        "eeg_channels": device_info.get("eeg_channels", []),
                        "channel_names": device_info.get("eeg_names", []),
                        "num_channels": len(device_info.get("eeg_channels", [])),
                        "board_id": device_info.get("board_id", -1),
                        "board_name": device_info.get("board_name", ""),
                        "streaming": False,
                        "board_info": device_info,  # Store the complete info
                    }
                )

            return True
        except Exception as e:
            logging.error(f"Connection error: {e}")
            self.collector = None
            return False

    def disconnect_from_board(self) -> bool:
        """
        Disconnect from the current board.

        Returns:
            True if disconnection was successful, False otherwise
        """
        if not self.collector:
            return True

        try:
            if self.is_streaming:
                self.stop_stream()

            self.collector.release_session()
            self.collector = None
            logging.info("Disconnected from board")
            return True
        except Exception as e:
            logging.error(f"Disconnection error: {e}")
            return False

    def start_stream(self, buffer_size: int = 450000) -> bool:
        """
        Start streaming data from the board.

        Args:
            buffer_size: Size of the buffer for data

        Returns:
            True if stream started successfully, False otherwise
        """
        if not self.collector:
            return False

        try:
            self.collector.start_stream(buffer_size)
            self.is_streaming = True

            # Update streaming status in DataAccessService
            data_access = DataAccessService.get_instance()
            data_access.update_metadata({"streaming": True})

            # Start background data retrieval thread
            self._stop_event.clear()
            self._data_thread = threading.Thread(target=self._data_loop, daemon=True)
            self._data_thread.start()

            logging.info("Stream started")
            return True
        except Exception as e:
            logging.error(f"Stream start error: {e}")
            return False

    def stop_stream(self) -> bool:
        """
        Stop streaming data from the board.

        Returns:
            True if stream stopped successfully, False otherwise
        """
        if not self.collector or not self.is_streaming:
            return False

        try:
            self.collector.stop_stream()
            self.is_streaming = False

            # Update streaming status in DataAccessService
            data_access = DataAccessService.get_instance()
            data_access.update_metadata({"streaming": False})

            # Stop background data retrieval thread
            self._stop_event.set()
            if self._data_thread:
                self._data_thread.join()

            logging.info("Stream stopped")
            return True
        except Exception as e:
            logging.error(f"Stream stop error: {e}")
            return False

    def get_board_data(
        self, num_samples: Optional[int] = None
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Get collected data from the board.

        Args:
            num_samples: Number of samples to get, all data if None

        Returns:
            Tuple containing the data and timestamps in ms
        """
        if not self.collector or not self.is_streaming:
            return np.array([]), []

        try:
            data, timestamps = self.collector.get_data(num_samples)

            # Update the DataAccessService with the new data
            data_access = DataAccessService.get_instance()
            data_access.update_data(data, timestamps)

            return data, timestamps
        except Exception as e:
            logging.error(f"Data retrieval error: {e}")
            return np.array([]), []

    def get_board_info(self) -> Dict[str, Any]:
        """
        Get information about the connected board.

        Returns:
            Dictionary with board information
        """
        if not self.collector:
            return {}

        try:
            return self.collector.get_board_info()
        except Exception as e:
            logging.error(f"Board info retrieval error: {e}")
            return {}

    def insert_marker(self, marker_value: Union[int, float]) -> bool:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert

        Returns:
            True if marker was inserted successfully, False otherwise
        """
        if not self.collector or not self.is_streaming:
            return False

        try:
            self.collector.insert_marker(marker_value)
            return True
        except Exception as e:
            logging.error(f"Marker insertion error: {e}")
            return False

    def set_processed_data(self, data: np.ndarray) -> bool:
        """
        Set processed data after signal processing.

        Args:
            data: Processed data

        Returns:
            True if data was set successfully, False otherwise
        """
        if not self.collector:
            return False

        try:
            self.collector.set_processed_data(data)
            return True
        except Exception as e:
            logging.error(f"Setting processed data error: {e}")
            return False

    def add_streamer(self, streamer_params: str) -> bool:
        """
        Add a streamer to stream data.

        Args:
            streamer_params: Parameters for the streamer

        Returns:
            True if streamer was added successfully, False otherwise
        """
        if not self.collector:
            return False

        try:
            self.collector.add_streamer(streamer_params)
            return True
        except Exception as e:
            logging.error(f"Adding streamer error: {e}")
            return False

    def remove_streamer(self, streamer_params: str) -> bool:
        """
        Remove a streamer.

        Args:
            streamer_params: Parameters for the streamer to remove

        Returns:
            True if streamer was removed successfully, False otherwise
        """
        if not self.collector:
            return False

        try:
            self.collector.delete_streamer(streamer_params)
            return True
        except Exception as e:
            logging.error(f"Removing streamer error: {e}")
            return False

    def get_eeg_channels(self) -> List[int]:
        """
        Get the EEG channels from the current board.

        Returns:
            List of EEG channel indices
        """
        if not self.collector:
            return []

        try:
            return self.collector.get_eeg_channels()
        except Exception as e:
            logging.error(f"Getting EEG channels error: {e}")
            return []

    def get_channel_by_type(self, channel_type: str) -> List[int]:
        """
        Get channels of a specific type.

        Args:
            channel_type: Type of channels to get ('eeg', 'emg', etc.)

        Returns:
            List of channel indices
        """
        if not self.collector:
            return []

        try:
            return self.collector.get_channel_by_type(channel_type)
        except Exception as e:
            logging.error(f"Getting channels by type error: {e}")
            return []

    def get_sampling_rate(self) -> int:
        """
        Get the sampling rate of the current board.

        Returns:
            Sampling rate in Hz
        """
        if not self.collector:
            return 0

        try:
            return self.collector.sampling_rate
        except Exception as e:
            logging.error(f"Getting sampling rate error: {e}")
            return 0

    def config_device(self, config: str) -> str:
        """
        Send configuration to the device.

        Args:
            config: Configuration string to send

        Returns:
            Response from the device
        """
        if not self.collector:
            return ""

        try:
            return self.collector.config_device(config)
        except Exception as e:
            logging.error(f"Device configuration error: {e}")
            return ""

    def set_preset(self, preset: int) -> bool:
        """
        Change the current preset.

        Args:
            preset: New preset value

        Returns:
            True if preset was set successfully, False otherwise
        """
        if not self.collector:
            return False

        try:
            return self.collector.set_preset(preset)
        except Exception as e:
            logging.error(f"Setting preset error: {e}")
            return False

    def is_connected(self) -> bool:
        """
        Check if a board is connected.

        Returns:
            True if board is connected, False otherwise
        """
        return self.collector is not None

    def is_streaming_active(self) -> bool:
        """
        Check if the board is streaming data.

        Returns:
            True if board is streaming, False otherwise
        """
        return self.is_streaming

    def cleanup(self) -> None:
        """Clean up resources when closing the application."""
        # Ensure background thread is stopped
        self._stop_event.set()

    def get_current_sample_rate(self) -> float:
        """
        Get the current measured sample rate.

        Returns:
            Current sample rate in Hz
        """
        return self._current_sample_rate

    def _data_loop(self) -> None:
        """Background loop to fetch data and update DataAccessService."""
        data_access = DataAccessService.get_instance()

        # Reset metrics
        self._last_sample_count = 0
        self._current_sample_rate = 0.0
        self._samples_timestamps.clear()
        self._last_timestamp = time.time()
        self._last_reported_time = self._last_timestamp
        
        # Variables para el procesamiento de datos
        min_event_interval = 0.04  # 40ms (~25Hz update rate)
        last_event_time = 0
        accumulated_data = None
        accumulated_timestamps = []
        
        # Conseguir la información del muestreo
        expected_sampling_rate = 0
        if self.collector:
            try:
                expected_sampling_rate = self.collector.sampling_rate
            except:
                expected_sampling_rate = 250  # Default fallback

        while not self._stop_event.is_set() and self.collector and self.is_streaming:
            try:
                current_time = time.time()
                
                # Obtener datos disponibles
                try:
                    # Esto devuelve el número de muestras en el buffer interno
                    available_count = self.collector.get_board_data_count()
                except Exception as e:
                    logging.debug(f"Error getting board data count: {e}")
                    available_count = 0
                
                # Procesar datos solo si hay nuevos disponibles
                if available_count > self._last_sample_count:
                    # Solo capturar las nuevas muestras (no todas las del buffer)
                    new_samples = available_count - self._last_sample_count
                    self._last_sample_count = available_count
                    
                    # Obtener los nuevos datos
                    data, timestamps = self.collector.get_data(new_samples)
                    
                    if data.size > 0 and data.shape[1] > 0:
                        # Actualizar las métricas de frecuencia de muestreo
                        samples_received = data.shape[1]
                        
                        # Registrar la marca de tiempo para cada nueva muestra (aproximado)
                        now = time.time()
                        interval = (now - self._last_timestamp) / samples_received if samples_received > 0 else 0
                        
                        for i in range(samples_received):
                            self._samples_timestamps.append(now - (samples_received - i - 1) * interval)
                        
                        self._last_timestamp = now
                        
                        # Calcular tasa de muestreo real - solo actualizar cada _report_interval segundos
                        if current_time - self._last_reported_time >= self._report_interval:
                            self._update_sample_rate(current_time)
                            self._last_reported_time = current_time
                        
                        # Actualizar el servicio de datos
                        data_access.update_data(data, timestamps)
                        
                        # Acumular datos para envío de eventos
                        if accumulated_data is None:
                            accumulated_data = data
                            accumulated_timestamps = timestamps
                        else:
                            # Concatenar solo si las formas son compatibles
                            if data.shape[0] == accumulated_data.shape[0]:
                                accumulated_data = np.concatenate((accumulated_data, data), axis=1)
                                accumulated_timestamps.extend(timestamps)
                            else:
                                # Si las formas no coinciden, usar solo los nuevos datos
                                accumulated_data = data
                                accumulated_timestamps = timestamps
                        
                        # Enviar evento con los datos acumulados (limitado por frecuencia)
                        if current_time - last_event_time >= min_event_interval and accumulated_data is not None:
                            try:
                                from ..core.event_system import dispatch_throttled, EventType
                                
                                dispatch_throttled(
                                    EventType.DATA_UPDATED,
                                    {"data": accumulated_data, "timestamps": accumulated_timestamps},
                                    source="collector_service",
                                    min_interval=min_event_interval,
                                )
                                
                                # Reiniciar buffers después de enviar
                                accumulated_data = None
                                accumulated_timestamps = []
                                last_event_time = current_time
                            except Exception as e:
                                logging.debug(f"Error dispatching data event: {e}")
                
                # Determinar tiempo de espera dinámico basado en la tasa de muestreo
                sleep_time = 0.01  # Valor base: 10ms
                
                if expected_sampling_rate > 0:
                    # Ajustar tiempo de espera basado en la tasa esperada
                    # Si esperamos 250Hz, son 4ms por muestra, esperar ~2ms
                    ideal_sleep = 2.0 / expected_sampling_rate
                    
                    if available_count > new_samples * 2:  # Si estamos acumulando muchas muestras
                        sleep_time = min(0.001, ideal_sleep * 0.25)  # Dormir menos - máximo 1ms
                    elif new_samples > 0:  # Si hay nuevas muestras, usar tiempo ideal
                        sleep_time = ideal_sleep * 0.5  # La mitad del intervalo ideal
                    else:  # Si no hay nuevas muestras
                        sleep_time = ideal_sleep  # Esperar un intervalo completo
                
                time.sleep(sleep_time)
                    
            except Exception as e:
                logging.error(f"Error in data loop: {e}")
                time.sleep(0.1)  # Esperar más tiempo en caso de error
    
    def _update_sample_rate(self, current_time: float) -> None:
        """
        Actualiza la tasa de muestreo basada en las marcas de tiempo registradas.
        
        Args:
            current_time: Tiempo actual para calcular la ventana
        """
        # Necesitamos al menos dos muestras para calcular una tasa
        if len(self._samples_timestamps) < 2:
            self._current_sample_rate = 0.0
            return
        
        # Encontrar muestras dentro de la ventana de tiempo
        window_start = current_time - self._sample_window_size
        samples_in_window = [ts for ts in self._samples_timestamps if ts >= window_start]
        
        # Calcular tasa basada en muestras dentro de la ventana
        if len(samples_in_window) >= 2:
            # Calcular usando la primera y última muestra en la ventana
            time_span = samples_in_window[-1] - samples_in_window[0]
            if time_span > 0:
                # Restar 1 porque necesitamos el número de intervalos, no de puntos
                sample_count = len(samples_in_window) - 1
                rate = sample_count / time_span
                
                # Limitar a valores razonables (1-1000Hz)
                rate = max(1.0, min(1000.0, rate))
                self._current_sample_rate = rate
                
                # Actualizar los metadatos
                try:
                    DataAccessService.get_instance().update_metadata({
                        "actual_sample_rate": self._current_sample_rate
                    })
                except Exception as e:
                    logging.debug(f"Error updating sample rate metadata: {e}")
                
                logging.debug(f"Sample rate: {self._current_sample_rate:.2f} Hz ({len(samples_in_window)} samples in {time_span:.2f}s)")
        else:
            # No hay suficientes muestras en la ventana
            self._current_sample_rate = 0.0
    
    def _reset_connection_state(self) -> bool:
        """
        Reset internal connection state forcefully.
        Used as a backup mechanism to ensure disconnection is properly reflected.
        """
        try:
            self.collector = None
            self._reset_internal_state()
            logging.info("Collector service connection state reset")
            return True
        except Exception as e:
            logging.error(f"Error resetting collector state: {e}")
            return False

    def _reset_internal_state(self) -> None:
        """Reset all internal state variables to disconnected values."""
        try:
            # Reset any internal state variables
            if hasattr(self, "_active_collector_id"):
                self._active_collector_id = None
            if hasattr(self, "_collectors") and isinstance(self._collectors, dict):
                self._collectors.clear()
            # Add any otras variables de estado internas que necesiten ser reiniciadas
        except Exception as e:
            logging.error(f"Error resetting internal state: {e}")
