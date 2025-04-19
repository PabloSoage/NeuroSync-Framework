import logging
import time
from typing import Dict, List, Any, Optional, Tuple
import os
import sys
import threading
import queue

import numpy as np

# Handle direct script execution
if __name__ == "__main__":
    # Add parent directory to path so relative imports work
    module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if (module_path not in sys.path):
        sys.path.insert(0, module_path)
    from eeg_processor.python.interfaces.collector_interface import CollectorInterface
else:
    # Normal import when used as part of the package
    from ..interfaces.collector_interface import CollectorInterface

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowPresets
from brainflow.data_filter import DataFilter
from brainflow.exit_codes import BrainFlowError, BrainFlowExitCodes


class EEGCollector(CollectorInterface):
    """
    Collector for EEG data using BrainFlow.

    This class handles the connection to EEG devices, data acquisition,
    and basic data management operations.
    """

    def __init__(
        self,
        board_id: int = BoardIds.SYNTHETIC_BOARD,
        params: Optional[BrainFlowInputParams] = None,
        preset: int = BrainFlowPresets.DEFAULT_PRESET,
    ):
        """
        Initialize the EEG collector.

        Args:
            board_id: ID of the board to connect to (default: SYNTHETIC_BOARD)
            params: Parameters for board initialization
            preset: Data preset to use (default: DEFAULT_PRESET)
        """
        BoardShim.enable_dev_board_logger()

        if params is None:
            params = BrainFlowInputParams()

        self.params = params
        self.board_id = board_id
        self.preset = preset
        self.board = BoardShim(self.board_id, self.params)
        self.is_streaming = False
        self.start_time = 0
        self.raw_data = None
        self.processed_data = None
        self.timestamps = []

        # Variables para la grabación continua
        self.recording = False
        self.recording_file = None
        self.processed_recording_file = None
        self.recording_thread = None
        self.recording_queue = queue.Queue()
        self.total_recorded_samples = 0
        self.recording_start_time = 0
        self.last_data_count = 0
        self.data_type = "raw"
        self.is_recording_both = False
        
        # Get available presets for this board
        try:
            self.available_presets = BoardShim.get_board_presets(self.board_id)
            logging.info(f"Available presets for board {self.board_id}: {self.available_presets}")
        except Exception as e:
            logging.warning(f"Could not get available presets: {e}")
            self.available_presets = [BrainFlowPresets.DEFAULT_PRESET]

        # Get board information
        try:
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id, self.preset)
            self.eeg_channels = BoardShim.get_eeg_channels(self.board_id, self.preset)
            self.timestamp_channel = BoardShim.get_timestamp_channel(self.board_id, self.preset)
            self.marker_channel = BoardShim.get_marker_channel(self.board_id, self.preset)
            
            # Get additional channel types if available
            try:
                self.exg_channels = BoardShim.get_exg_channels(self.board_id, self.preset)
            except:
                self.exg_channels = self.eeg_channels
                
            # Get other channel types
            self.channel_types = {
                'eeg': self.eeg_channels,
                'emg': self._get_channels_safely(BoardShim.get_emg_channels, "EMG"),
                'ecg': self._get_channels_safely(BoardShim.get_ecg_channels, "ECG"),
                'eog': self._get_channels_safely(BoardShim.get_eog_channels, "EOG"),
                'eda': self._get_channels_safely(BoardShim.get_eda_channels, "EDA"),
                'ppg': self._get_channels_safely(BoardShim.get_ppg_channels, "PPG"),
                'accel': self._get_channels_safely(BoardShim.get_accel_channels, "Accel"),
                'gyro': self._get_channels_safely(BoardShim.get_gyro_channels, "Gyro"),
                'temperature': self._get_channels_safely(BoardShim.get_temperature_channels, "Temperature"),
                'resistance': self._get_channels_safely(BoardShim.get_resistance_channels, "Resistance"),
                'other': self._get_channels_safely(BoardShim.get_other_channels, "Other"),
            }
            
            # Try to get EEG names if available
            try:
                self.eeg_names = BoardShim.get_eeg_names(self.board_id, self.preset)
                if isinstance(self.eeg_names, str):
                    self.eeg_names = self.eeg_names.split(',')
            except:
                self.eeg_names = [f"Channel {i}" for i in self.eeg_channels]
        except Exception as e:
            logging.error(f"Error initializing board information: {e}")
            raise
        
        # Get device name
        try:
            self.device_name = BoardShim.get_device_name(self.board_id)
        except:
            self.device_name = f"Board ID {self.board_id}"
            
        # Get number of rows
        try:
            self.num_rows = BoardShim.get_num_rows(self.board_id, self.preset)
        except:
            self.num_rows = 0

        logging.info(f"EEG Collector initialized with board_id: {self.board_id}, preset: {self.preset}")
        logging.info(f"Device: {self.device_name}, Sampling rate: {self.sampling_rate}Hz")
        logging.info(f"EEG channels: {self.eeg_channels}")

    def _get_channels_safely(self, channel_func, channel_type: str) -> List[int]:
        """
        Safely get channels of a specific type, handling exceptions.
        
        Args:
            channel_func: The BoardShim function to call
            channel_type: The type of channel (for logging)
            
        Returns:
            List of channel indices
        """
        try:
            channels = channel_func(self.board_id, self.preset)
            return channels
        except Exception as e:
            logging.debug(f"No {channel_type} channels available: {e}")
            return []

    def prepare_session(self) -> None:
        """
        Prepare the session for data collection.
        """
        try:
            self.board.prepare_session()
            logging.info("EEG session prepared")
        except BrainFlowError as e:
            if e.exit_code == BrainFlowExitCodes.BOARD_NOT_CREATED_ERROR.value:
                logging.error("Board was not created. Check your parameters.")
            elif e.exit_code == BrainFlowExitCodes.ANOTHER_BOARD_IS_CREATED_ERROR.value:
                logging.error("Another board is already created in the same process.")
            else:
                logging.error(f"Error preparing session: {e}")
            raise

    def start_stream(self, buffer_size: int = 450000) -> None:
        """
        Start streaming EEG data.
        
        Args:
            buffer_size: Size of the buffer for data
        """
        if not self.is_streaming:
            self.board.start_stream(buffer_size)
            self.is_streaming = True
            self.start_time = int(round(time.time() * 1000))  # Current time in ms
            logging.info(f"EEG stream started with buffer size {buffer_size}")
        else:
            logging.warning("Stream already running")

    def stop_stream(self) -> None:
        """
        Stop streaming EEG data.
        """
        if self.is_streaming:
            self.board.stop_stream()
            self.is_streaming = False
            logging.info("EEG stream stopped")
        else:
            logging.warning("No stream to stop")

    def release_session(self) -> None:
        """
        Release resources after the session is finished.
        """
        if self.is_streaming:
            self.stop_stream()
        self.board.release_session()
        logging.info("EEG session released")

    def get_data(
        self, num_samples: Optional[int] = None
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Get collected EEG data.

        Args:
            num_samples: Number of samples to get, all data if None

        Returns:
            Tuple containing the EEG data and timestamps in ms
        """
        if not self.is_streaming:
            logging.warning("Stream not running, no data available")
            return np.array([]), []

        try:
            if (num_samples is None):
                # Get all data and keep it in the buffer
                data = self.board.get_board_data(preset=self.preset)
            else:
                # Get latest num_samples samples
                data = self.board.get_current_board_data(num_samples, preset=self.preset)

            # Get timestamps from the data
            try:
                timestamps = data[self.timestamp_channel].tolist()
                # If board doesn't provide timestamps, generate them
                if not timestamps or len(timestamps) == 0:
                    current_time = int(round(time.time() * 1000))
                    timestamps = list(
                        range(self.start_time, current_time, int(1000 / self.sampling_rate))
                    )[-data.shape[1]:]
            except Exception as e:
                logging.error(f"Error getting timestamps: {e}")
                timestamps = []

            self.raw_data = data
            self.timestamps = timestamps

            return data, timestamps
        except Exception as e:
            logging.error(f"Error getting data: {e}")
            return np.array([]), []

    def save_data(self, filename: str, data_type: str = "raw") -> None:
        """
        Save collected data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to save ('raw' or 'processed')
        """
        try:
            data = None
            if data_type == "raw" and self.raw_data is not None:
                data = self.raw_data
            elif data_type == "processed" and self.processed_data is not None:
                data = self.processed_data
            else:
                logging.warning(f"No {data_type} data available to save")
                return

            # Para archivos CSV, usar nuestro formato con cabeceras
            if filename.endswith(".csv"):
                # Crear el directorio si no existe
                os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
                
                with open(filename, 'w', newline='') as file:
                    # Escribir metadatos
                    header = [
                        f"# EEG Recording - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"# Board: {self.device_name} (ID: {self.board_id})",
                        f"# Preset: {self.preset}",
                        f"# Sampling Rate: {self.sampling_rate} Hz",
                        f"# Data Type: {data_type}",
                        f"# Channels: {data.shape[0]}",
                        f"# Samples: {data.shape[1]}",
                        f"# Duration: {data.shape[1]/self.sampling_rate:.2f} seconds",
                    ]
                    
                    # Generar nombres de columnas
                    column_names = []
                    for i in range(data.shape[0]):
                        # Identificar tipo de canal y asignar nombre descriptivo
                        if hasattr(self, 'timestamp_channel') and i == self.timestamp_channel:
                            column_names.append("Timestamp")
                        elif hasattr(self, 'marker_channel') and i == self.marker_channel:
                            column_names.append("Marker")
                        elif i in self.channel_types.get('eeg', []):
                            # Intentar usar nombre de canal EEG si está disponible
                            eeg_index = self.channel_types['eeg'].index(i)
                            if hasattr(self, 'eeg_names') and eeg_index < len(self.eeg_names):
                                column_names.append(f"EEG_{self.eeg_names[eeg_index]}")
                            else:
                                column_names.append(f"EEG_{eeg_index}")
                        elif i in self.channel_types.get('emg', []):
                            emg_index = self.channel_types['emg'].index(i)
                            column_names.append(f"EMG_{emg_index}")
                        elif i in self.channel_types.get('ecg', []):
                            ecg_index = self.channel_types['ecg'].index(i)
                            column_names.append(f"ECG_{ecg_index}")
                        elif i in self.channel_types.get('eog', []):
                            eog_index = self.channel_types['eog'].index(i)
                            column_names.append(f"EOG_{eog_index}")
                        elif i in self.channel_types.get('eda', []):
                            eda_index = self.channel_types['eda'].index(i)
                            column_names.append(f"EDA_{eda_index}")
                        elif i in self.channel_types.get('ppg', []):
                            ppg_index = self.channel_types['ppg'].index(i)
                            column_names.append(f"PPG_{ppg_index}")
                        elif i in self.channel_types.get('accel', []):
                            accel_index = self.channel_types['accel'].index(i)
                            accel_names = ['X', 'Y', 'Z']
                            axis_name = accel_names[accel_index % 3] if accel_index < 3 else accel_index
                            column_names.append(f"ACCEL_{axis_name}")
                        elif i in self.channel_types.get('gyro', []):
                            gyro_index = self.channel_types.get('gyro').index(i)
                            gyro_names = ['X', 'Y', 'Z']
                            axis_name = gyro_names[gyro_index % 3] if gyro_index < 3 else gyro_index
                            column_names.append(f"GYRO_{axis_name}")
                        elif i in self.channel_types.get('temperature', []):
                            temp_index = self.channel_types['temperature'].index(i)
                            column_names.append(f"TEMP_{temp_index}")
                        elif i in self.channel_types.get('resistance', []):
                            res_index = self.channel_types['resistance'].index(i)
                            column_names.append(f"RES_{res_index}")
                        else:
                            # Nombre genérico para canales no identificados
                            column_names.append(f"CH_{i}")
                    
                    # Añadir la línea de nombres de columnas al encabezado
                    header.append("# Column names: " + ", ".join(column_names))
                    
                    # Escribir las líneas de cabecera con saltos de línea
                    for line in header:
                        file.write(line + '\n')
                    
                    # Escribir cada muestra como una fila en el CSV
                    for i in range(data.shape[1]):  # Para cada columna (muestra)
                        sample = data[:, i]  # Esta es una muestra con todos los canales
                        line = ','.join(str(val) for val in sample)
                        file.write(line + '\n')
                
                logging.info(f"{data_type} data saved to {filename}")
            else:
                # Para otros formatos, usar el writer de BrainFlow
                DataFilter.write_file(data, filename, "w")
                logging.info(f"{data_type} data saved to {filename}")
        except Exception as e:
            logging.error(f"Error saving data: {e}")

    def get_board_info(self) -> Dict[str, Any]:
        """
        Get information about the connected EEG board.

        Returns:
            Dictionary with board information
        """
        info = {
            "board_id": self.board_id,
            "board_name": self.device_name,
            "sampling_rate": self.sampling_rate,
            "preset": self.preset,
            "available_presets": self.available_presets,
            "eeg_channels": self.eeg_channels,
            "eeg_names": self.eeg_names,
            "timestamp_channel": self.timestamp_channel,
            "marker_channel": self.marker_channel,
            "num_rows": self.num_rows,
        }
        
        # Add channel type information if available
        for ch_type, channels in self.channel_types.items():
            if channels:
                info[f"{ch_type}_channels"] = channels
        
        return info

    def insert_marker(self, marker_value: float) -> None:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert
        """
        if self.is_streaming:
            # Insertar el marcador con el valor especificado
            self.board.insert_marker(marker_value, preset=self.preset)
            
            # Añadir un pequeño retraso para asegurar que el marcador se registre
            # antes de la próxima captura de datos por parte de get_current_board_data
            time.sleep(0.01)
            
            logging.info(f"Marker {marker_value} inserted at channel {self.marker_channel}")
        else:
            logging.warning("Cannot insert marker: stream not running")

    def get_eeg_channels(self) -> List[int]:
        """
        Get the EEG channel indices.

        Returns:
            List of EEG channel indices
        """
        return self.eeg_channels

    def get_channel_by_type(self, channel_type: str) -> List[int]:
        """
        Get channels of a specific type.
        
        Args:
            channel_type: Type of channels to get ('eeg', 'emg', 'ecg', etc.)
            
        Returns:
            List of channel indices
        """
        if channel_type in self.channel_types:
            return self.channel_types[channel_type]
        else:
            logging.warning(f"Unknown channel type: {channel_type}")
            return []

    def set_processed_data(self, data: np.ndarray) -> None:
        """
        Set processed data after signal processing.

        Args:
            data: Processed EEG data
        """
        self.processed_data = data
        
    def add_streamer(self, streamer_params: str) -> None:
        """
        Add a streamer to stream data.
        
        Args:
            streamer_params: Parameters for the streamer
        """
        if self.is_streaming:
            logging.warning("Cannot add streamer while streaming")
            return
            
        try:
            self.board.add_streamer(streamer_params, self.preset)
            logging.info(f"Added streamer with parameters: {streamer_params}")
        except Exception as e:
            logging.error(f"Error adding streamer: {e}")
            
    def delete_streamer(self, streamer_params: str) -> None:
        """
        Delete a streamer.
        
        Args:
            streamer_params: Parameters for the streamer to delete
        """
        try:
            self.board.delete_streamer(streamer_params, self.preset)
            logging.info(f"Deleted streamer with parameters: {streamer_params}")
        except Exception as e:
            logging.error(f"Error deleting streamer: {e}")
            
    def get_board_data_count(self) -> int:
        """
        Get the current number of samples in the buffer.
        
        Returns:
            Number of samples in the buffer
        """
        try:
            count = self.board.get_board_data_count(self.preset)
            return count
        except Exception as e:
            logging.error(f"Error getting board data count: {e}")
            return 0
            
    def config_board(self, config: str) -> str:
        """
        Send configuration to the board.
        
        Args:
            config: Configuration string to send
            
        Returns:
            Response from the board
        """
        try:
            response = self.board.config_board(config)
            logging.info(f"Board configured with: {config}")
            return response
        except Exception as e:
            logging.error(f"Error configuring board: {e}")
            return ""
    
    def set_preset(self, preset: int) -> bool:
        """
        Change the current preset.
        
        Args:
            preset: New preset value
            
        Returns:
            Success status
        """
        if preset not in self.available_presets:
            logging.warning(f"Preset {preset} not available for this board")
            return False
            
        try:
            self.preset = preset
            # Update board information for the new preset
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id, self.preset)
            self.eeg_channels = BoardShim.get_eeg_channels(self.board_id, self.preset)
            self.timestamp_channel = BoardShim.get_timestamp_channel(self.board_id, self.preset)
            self.marker_channel = BoardShim.get_marker_channel(self.board_id, self.preset)
            
            logging.info(f"Preset changed to {preset}")
            logging.info(f"New sampling rate: {self.sampling_rate}Hz")
            logging.info(f"New EEG channels: {self.eeg_channels}")
            
            return True
        except Exception as e:
            logging.error(f"Error changing preset: {e}")
            return False

    def start_continuous_recording(self, filename: str, data_type: str = "raw") -> None:
        """
        Iniciar la grabación continua de datos en un archivo CSV.
        
        Args:
            filename: Ruta del archivo donde guardar los datos
            data_type: Tipo de datos a guardar ('raw', 'processed' o 'both')
        """
        if self.recording:
            logging.warning("La grabación ya está en curso")
            return
        
        try:
            self.data_type = data_type
            self.is_recording_both = (data_type == "both")
            
            # Para el caso de 'both', creamos dos archivos diferentes
            if data_type == "both":
                # Crear nombres de archivo para raw y processed
                base_name, extension = os.path.splitext(filename)
                self.raw_filename = f"{base_name}_raw{extension}"
                self.processed_filename = f"{base_name}_processed{extension}"
                
                # Iniciar grabación de datos raw
                self._start_file_recording(self.raw_filename, "raw")
                
                # Iniciar grabación de datos processed
                self._start_file_recording(self.processed_filename, "processed")
                
                logging.info(f"Grabación continua dual iniciada en {self.raw_filename} y {self.processed_filename}")
            else:
                # Caso estándar: un solo tipo de datos
                self._start_file_recording(filename, data_type)
                logging.info(f"Grabación continua iniciada en {filename}")
                
            # Inicializar variables de grabación
            self.recording = True
            self.total_recorded_samples = 0
            self.recording_start_time = time.time()
            self.last_data_count = self.get_board_data_count()
            
            # Iniciar thread de grabación
            self.recording_thread = threading.Thread(
                target=self._recording_thread_func,
                daemon=True
            )
            self.recording_thread.start()
            
        except Exception as e:
            logging.error(f"Error al iniciar la grabación continua: {e}")
            if hasattr(self, 'recording_file') and self.recording_file is not None:
                self.recording_file.close()
                self.recording_file = None
            if hasattr(self, 'processed_recording_file') and self.processed_recording_file is not None:
                self.processed_recording_file.close()
                self.processed_recording_file = None
            raise
            
    def _start_file_recording(self, filename: str, data_type: str) -> None:
        """
        Inicia la grabación en un archivo específico con los metadatos correctos.
        
        Args:
            filename: Ruta del archivo donde guardar los datos
            data_type: Tipo de datos ('raw' o 'processed')
        """
        # Crear el directorio si no existe
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Abrir el archivo y escribir la cabecera
        file_handle = open(filename, 'w', newline='')
        
        # Escribir metadatos iniciales
        header = [
            f"# EEG Recording - {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Board: {self.device_name} (ID: {self.board_id})",
            f"# Preset: {self.preset}",
            f"# Sampling Rate: {self.sampling_rate} Hz",
            f"# Data Type: {data_type}",
            f"# Channels: {self.num_rows}",
            f"# Samples: 0",  # Placeholder que actualizaremos al final
            f"# Duration: 0.00 seconds",  # Placeholder que actualizaremos al final
        ]
        
        # Añadir nombres de columnas usando la lógica avanzada
        column_names = []
        for i in range(self.num_rows):
            # Identificar tipo de canal y asignar nombre descriptivo
            if hasattr(self, 'timestamp_channel') and i == self.timestamp_channel:
                column_names.append("Timestamp")
            elif hasattr(self, 'marker_channel') and i == self.marker_channel:
                column_names.append("Marker")
            elif i in self.channel_types.get('eeg', []):
                # Intentar usar nombre de canal EEG si está disponible
                eeg_index = self.channel_types['eeg'].index(i)
                if hasattr(self, 'eeg_names') and eeg_index < len(self.eeg_names):
                    column_names.append(f"EEG_{self.eeg_names[eeg_index]}")
                else:
                    column_names.append(f"EEG_{eeg_index}")
            elif i in self.channel_types.get('emg', []):
                emg_index = self.channel_types['emg'].index(i)
                column_names.append(f"EMG_{emg_index}")
            elif i in self.channel_types.get('ecg', []):
                ecg_index = self.channel_types['ecg'].index(i)
                column_names.append(f"ECG_{ecg_index}")
            elif i in self.channel_types.get('eog', []):
                eog_index = self.channel_types['eog'].index(i)
                column_names.append(f"EOG_{eog_index}")
            elif i in self.channel_types.get('eda', []):
                eda_index = self.channel_types['eda'].index(i)
                column_names.append(f"EDA_{eda_index}")
            elif i in self.channel_types.get('ppg', []):
                ppg_index = self.channel_types['ppg'].index(i)
                column_names.append(f"PPG_{ppg_index}")
            elif i in self.channel_types.get('accel', []):
                accel_index = self.channel_types['accel'].index(i)
                accel_names = ['X', 'Y', 'Z']
                axis_name = accel_names[accel_index % 3] if accel_index < 3 else accel_index
                column_names.append(f"ACCEL_{axis_name}")
            elif i in self.channel_types.get('gyro', []):
                gyro_index = self.channel_types['gyro'].index(i)
                gyro_names = ['X', 'Y', 'Z']
                axis_name = gyro_names[gyro_index % 3] if gyro_index < 3 else gyro_index
                column_names.append(f"GYRO_{axis_name}")
            elif i in self.channel_types.get('temperature', []):
                temp_index = self.channel_types['temperature'].index(i)
                column_names.append(f"TEMP_{temp_index}")
            elif i in self.channel_types.get('resistance', []):
                res_index = self.channel_types['resistance'].index(i)
                column_names.append(f"RES_{res_index}")
            else:
                # Nombre genérico para canales no identificados
                column_names.append(f"CH_{i}")
        
        # Añadir la línea de nombres de columnas al encabezado
        header.append(", ".join(column_names))
        
        # Escribir las líneas de cabecera con saltos de línea
        for line in header:
            file_handle.write(line + '\n')
            
        # Almacenar el manejador de archivo según el tipo de datos
        if data_type == "raw":
            self.recording_file = file_handle
        elif data_type == "processed":
            self.processed_recording_file = file_handle

    def _recording_thread_func(self) -> None:
        """
        Función ejecutada en un thread separado para la grabación continua.
        Monitorea nuevos datos y los escribe al archivo.
        """
        try:
            # Mantener un seguimiento del último conteo de datos procesado
            last_count = self.last_data_count
            
            while self.recording:
                # Obtener conteo actual de datos en el buffer
                current_count = self.get_board_data_count()
                
                # Si hay nuevos datos disponibles
                if current_count > last_count:
                    # Calcular cuántas nuevas muestras tenemos
                    new_samples = current_count - last_count
                    
                    # Obtener datos raw (siempre necesarios para ambos tipos)
                    raw_data = self.board.get_current_board_data(new_samples, preset=self.preset)
                    
                    # Escribir datos raw si corresponde
                    if self.data_type == "raw" or self.data_type == "both":
                        self._write_data_to_file(raw_data, "raw")
                    
                    # Escribir datos procesados si corresponde
                    if self.data_type == "processed" or self.data_type == "both":
                        # Para datos procesados, usar los datos procesados si están disponibles
                        if self.processed_data is not None and self.processed_data.shape[1] >= new_samples:
                            processed_data = self.processed_data[:, -new_samples:]
                        else:
                            # Si no hay datos procesados, usar los datos crudos como fallback
                            processed_data = raw_data
                            
                        self._write_data_to_file(processed_data, "processed")
                    
                    # Actualizar el contador de muestras y el último conteo
                    self.total_recorded_samples += new_samples
                    last_count = current_count
                
                # Pausa breve para no saturar la CPU
                time.sleep(0.1)
                
        except Exception as e:
            logging.error(f"Error en el thread de grabación: {e}")
    
    def _write_data_to_file(self, data: np.ndarray, data_type: str) -> None:
        """
        Escribe los datos en el archivo correspondiente.
        
        Args:
            data: Datos a escribir
            data_type: Tipo de datos ('raw' o 'processed')
        """
        # Seleccionar el archivo correcto
        file_handle = None
        if data_type == "raw":
            file_handle = self.recording_file
        elif data_type == "processed":
            file_handle = self.processed_recording_file
            
        if file_handle is None:
            return
            
        # Verificar si hay marcadores en los datos
        if hasattr(self, 'marker_channel') and self.marker_channel < data.shape[0]:
            # Comprobar valores distintos de cero en el canal de marcadores
            markers = data[self.marker_channel]
            non_zero_markers = markers[markers != 0]
            if len(non_zero_markers) > 0:
                logging.info(f"Detected markers in {data_type} data: {non_zero_markers}")
        
        # Escribir cada muestra como una fila en el CSV
        for i in range(data.shape[1]):  # Para cada columna (muestra)
            sample = data[:, i]  # Esta es una muestra con todos los canales
            
            # Imprimir log si hay un marcador en esta muestra
            if hasattr(self, 'marker_channel') and self.marker_channel < len(sample):
                if sample[self.marker_channel] != 0:
                    logging.info(f"Writing marker value {sample[self.marker_channel]} to {data_type} CSV")
            
            line = ','.join(str(val) for val in sample)
            file_handle.write(line + '\n')
            
        # Hacer flush para asegurar que los datos se escriban en el disco
        file_handle.flush()

    def stop_continuous_recording(self) -> None:
        """
        Detener la grabación continua y cerrar el archivo.
        """
        if not self.recording:
            logging.warning("No hay grabación activa para detener")
            return
        
        try:
            # Marcar como no grabando para detener el thread
            self.recording = False
            
            # Esperar a que termine el thread
            if self.recording_thread is not None:
                self.recording_thread.join(timeout=2.0)  # Esperar máximo 2 segundos
            
            # Calcular duración real
            recording_duration = time.time() - self.recording_start_time
            
            # Cerrar y actualizar el archivo raw si está activo
            if hasattr(self, 'recording_file') and self.recording_file is not None:
                self._finalize_recording_file(self.recording_file, recording_duration)
                self.recording_file = None
                
            # Cerrar y actualizar el archivo processed si está activo
            if hasattr(self, 'processed_recording_file') and self.processed_recording_file is not None:
                self._finalize_recording_file(self.processed_recording_file, recording_duration)
                self.processed_recording_file = None
                
            logging.info(f"Grabación completada: {self.total_recorded_samples} muestras en {recording_duration:.2f} segundos")
        
        except Exception as e:
            logging.error(f"Error al detener la grabación continua: {e}")
            # Intentar cerrar todos los archivos abiertos
            if hasattr(self, 'recording_file') and self.recording_file is not None:
                try:
                    self.recording_file.close()
                except:
                    pass
                self.recording_file = None
                
            if hasattr(self, 'processed_recording_file') and self.processed_recording_file is not None:
                try:
                    self.processed_recording_file.close()
                except:
                    pass
                self.processed_recording_file = None
            raise
        
        finally:
            # Reiniciar variables
            self.recording = False
            self.is_recording_both = False
            self.recording_thread = None
            self.recording_queue = queue.Queue()
            
    def _finalize_recording_file(self, file_handle, recording_duration):
        """
        Finaliza un archivo de grabación actualizando sus metadatos.
        
        Args:
            file_handle: Manejador del archivo a finalizar
            recording_duration: Duración de la grabación en segundos
        """
        # Guardar el nombre del archivo para reabrirlo después
        filename = file_handle.name
        
        # Cerrar el archivo que está en modo escritura
        file_handle.close()
        
        # Reabrir el archivo en modo lectura+escritura
        with open(filename, 'r', encoding='utf-8') as file:
            # Leer todo el contenido del archivo
            content = file.readlines()
        
        # Reabrir el archivo en modo escritura para actualizar los metadatos
        with open(filename, 'w', encoding='utf-8') as file:
            # Reescribir el archivo con los metadatos actualizados
            for i, line in enumerate(content):
                if i == 6:  # Línea de samples
                    file.write(f"# Samples: {self.total_recorded_samples}\n")
                elif i == 7:  # Línea de duración
                    file.write(f"# Duration: {recording_duration:.2f} seconds\n")
                else:
                    file.write(line)

