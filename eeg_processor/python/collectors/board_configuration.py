import logging
import os

# Import the interface
import sys
from typing import Dict, List, Tuple, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interfaces.board_interface import BoardInterface

from brainflow.board_shim import (
    BoardShim,
    BrainFlowInputParams,
    BoardIds,
    BrainFlowPresets,
)


class BrainFlowBoardConfiguration(BoardInterface):
    """
    BrainFlow implementation of board configuration management.
    """

    def __init__(self) -> None:
        """
        Initialize the BrainFlow board configuration manager.
        """
        # Initialize brainflow logger if needed
        BoardShim.enable_dev_board_logger()

        # Store presets for easier access
        self.presets = {
            "DEFAULT": BrainFlowPresets.DEFAULT_PRESET.value,
            "AUXILIARY": BrainFlowPresets.AUXILIARY_PRESET.value,
            "ANCILLARY": BrainFlowPresets.ANCILLARY_PRESET.value,
        }

    def get_all_boards(self) -> List[Tuple[str, int]]:
        """
        Get a list of all available boards.

        Returns:
            List of tuples containing (board_name, board_id)
        """
        boards = []
        # Add special boards first for easier access
        special_boards = [
            ("Synthetic Board", BoardIds.SYNTHETIC_BOARD.value),
            ("Playback File Board", BoardIds.PLAYBACK_FILE_BOARD.value),
            ("Streaming Board", BoardIds.STREAMING_BOARD.value),
        ]
        boards.extend(special_boards)

        # Add remaining boards from BoardIds
        for attr in dir(BoardIds):
            if attr.startswith("__"):
                continue

            try:
                board_id = getattr(BoardIds, attr)
                # Skip if not an integer or already added
                if not isinstance(board_id, int) or any(
                    b[1] == board_id for b in special_boards
                ):
                    continue

                # Get board name safely
                try:
                    board_name = BoardShim.get_device_name(board_id)
                    boards.append((board_name, board_id))
                except Exception as e:
                    # If we can't get the name, use the attribute name
                    boards.append((attr.replace("_", " ").title(), board_id))
            except Exception as e:
                logging.debug(f"Error processing board ID {attr}: {e}")

        return boards

    def get_board_groups(self) -> Dict[str, List[Tuple[str, int]]]:
        """
        Get boards grouped by type.

        Returns:
            Dictionary with board types as keys and lists of (board_name, board_id) as values
        """
        all_boards = self.get_all_boards()

        # Define groups with more categories
        groups: Dict[str, List[Tuple[str, int]]] = {
            "Special/Synthetic": [],
            "OpenBCI": [],
            "Muse": [],
            "Neurosity": [],
            "g.tec": [],
            "ANT Neuro": [],
            "NeuroMD": [],
            "OYMotion": [],
            "FreeEEG": [],
            "Mentalab": [],
            "EmotiBit": [],
            "Other Hardware": [],
            "Undocumented": [],
        }

        # Special handling for synthetic, playback and streaming boards
        special_board_ids = [
            BoardIds.SYNTHETIC_BOARD.value,
            BoardIds.PLAYBACK_FILE_BOARD.value,
            BoardIds.STREAMING_BOARD.value,
        ]

        for board_name, board_id in all_boards:
            board_name_lower = board_name.lower()

            if board_id in special_board_ids:
                groups["Special/Synthetic"].append((board_name, board_id))
            elif (
                "openbci" in board_name_lower
                or "cyton" in board_name_lower
                or "ganglion" in board_name_lower
            ):
                groups["OpenBCI"].append((board_name, board_id))
            elif "muse" in board_name_lower:
                groups["Muse"].append((board_name, board_id))
            elif (
                "neurosity" in board_name_lower
                or "notion" in board_name_lower
                or "crown" in board_name_lower
            ):
                groups["Neurosity"].append((board_name, board_id))
            elif (
                "g.tec" in board_name_lower
                or "unicorn" in board_name_lower
                or "gtec" in board_name_lower
            ):
                groups["g.tec"].append((board_name, board_id))
            elif "ant" in board_name_lower or "eego" in board_name_lower:
                groups["ANT Neuro"].append((board_name, board_id))
            elif (
                "brainbit" in board_name_lower
                or "callibri" in board_name_lower
                or "neuromd" in board_name_lower
            ):
                groups["NeuroMD"].append((board_name, board_id))
            elif "gforce" in board_name_lower or "oymotion" in board_name_lower:
                groups["OYMotion"].append((board_name, board_id))
            elif "freeeeg" in board_name_lower:
                groups["FreeEEG"].append((board_name, board_id))
            elif "explore" in board_name_lower or "mentalab" in board_name_lower:
                groups["Mentalab"].append((board_name, board_id))
            elif "emotibit" in board_name_lower:
                groups["EmotiBit"].append((board_name, board_id))
            elif any(name in board_name_lower for name in [
                "enophone", "brainalive", "pieeg", "neuropawn", "knight", "biolistener"
            ]):
                groups["Other Hardware"].append((board_name, board_id))
            elif any(name in board_name_lower for name in [
                "galea", "ntl", "aavaa"
            ]):
                groups["Undocumented"].append((board_name, board_id))
            else:
                groups["Other Hardware"].append((board_name, board_id))

        return groups

    def get_board_requirements(self, board_id: int) -> Dict[str, bool]:
        """
        Get the parameters required for a specific board.

        Args:
            board_id: ID of the board

        Returns:
            Dictionary with parameters as keys and boolean indicating if required
        """
        requirements = {
            "serial_port": False,
            "mac_address": False,
            "ip_address": False,
            "ip_port": False,
            "other_info": False,
            "serial_number": False,
            "file": False,
            "master_board": False,
            "timeout": False,
        }

        # Define requirements based on supported_boards.txt documentation
        if board_id == BoardIds.SYNTHETIC_BOARD.value:
            # Synthetic board doesn't need any parameters
            requirements.pop("timeout")
            return requirements

        if board_id == BoardIds.PLAYBACK_FILE_BOARD.value:
            requirements["file"] = True  # Required: full path to recorded file
            requirements["master_board"] = True  # Required: board ID of device used to create files
            requirements.pop("timeout")
            return requirements

        if board_id == BoardIds.STREAMING_BOARD.value:
            requirements["ip_address"] = True  # Required: multicast address
            requirements["ip_port"] = True  # Required: port number
            requirements["master_board"] = True  # Required: board ID of the device
            requirements.pop("timeout")
            return requirements

        # Use specific Board IDs for exact matching - Documented boards
        try:
            # OpenBCI Cyton - serial_port required
            if board_id == BoardIds.CYTON_BOARD.value:
                requirements["serial_port"] = True
                requirements.pop("timeout")
                return requirements

            # OpenBCI Cyton Daisy - serial_port required  
            elif board_id == BoardIds.CYTON_DAISY_BOARD.value:
                requirements["serial_port"] = True
                requirements.pop("timeout")
                return requirements

            # OpenBCI Ganglion (with dongle) - serial_port required, timeout optional
            elif board_id == BoardIds.GANGLION_BOARD.value:
                requirements["serial_port"] = True
                return requirements

            # OpenBCI Ganglion Native - no required parameters (auto-discovery)
            elif board_id == BoardIds.GANGLION_NATIVE_BOARD.value:
                requirements.pop("timeout")
                return requirements

            # OpenBCI WiFi boards - ip_port required, timeout optional
            elif board_id in [BoardIds.GANGLION_WIFI_BOARD.value, BoardIds.CYTON_WIFI_BOARD.value, BoardIds.CYTON_DAISY_WIFI_BOARD.value]:
                requirements["ip_port"] = True
                return requirements

            # BrainBit - timeout optional
            elif board_id == BoardIds.BRAINBIT_BOARD.value:
                return requirements

            # BrainBit BLED - serial_port required for dongle
            elif board_id == BoardIds.BRAINBIT_BLED_BOARD.value:
                requirements["serial_port"] = True
                requirements.pop("timeout")
                return requirements

            # Callibri boards - timeout optional
            elif board_id in [BoardIds.CALLIBRI_EEG_BOARD.value, BoardIds.CALLIBRI_EMG_BOARD.value, BoardIds.CALLIBRI_ECG_BOARD.value]:
                return requirements

            # Unicorn - no required parameters
            elif board_id == BoardIds.UNICORN_BOARD.value:
                requirements.pop("timeout")
                return requirements

            # Neurosity boards - no required parameters
            elif board_id in [BoardIds.NOTION_1_BOARD.value, BoardIds.NOTION_2_BOARD.value, BoardIds.CROWN_BOARD.value]:
                requirements.pop("timeout")
                return requirements

            # gForce boards - no required parameters
            elif board_id in [BoardIds.GFORCE_PRO_BOARD.value, BoardIds.GFORCE_DUAL_BOARD.value]:
                requirements.pop("timeout")
                return requirements

            # FreeEEG boards - serial_port required
            elif board_id in [BoardIds.FREEEEG32_BOARD.value, BoardIds.FREEEEG128_BOARD.value]:
                requirements["serial_port"] = True
                requirements.pop("timeout")
                return requirements

            # Muse BLED boards - serial_port required for dongle
            elif board_id in [BoardIds.MUSE_S_BLED_BOARD.value, BoardIds.MUSE_2_BLED_BOARD.value, BoardIds.MUSE_2016_BLED_BOARD.value]:
                requirements["serial_port"] = True
                requirements.pop("timeout")
                return requirements

            # Muse native boards - no required parameters (auto-discovery)
            elif board_id in [BoardIds.MUSE_S_BOARD.value, BoardIds.MUSE_2_BOARD.value, BoardIds.MUSE_2016_BOARD.value]:
                requirements.pop("timeout")
                return requirements

            # ANT Neuro boards - no required parameters
            elif board_id in [
                BoardIds.ANT_NEURO_EE_410_BOARD.value, BoardIds.ANT_NEURO_EE_411_BOARD.value,
                BoardIds.ANT_NEURO_EE_430_BOARD.value, BoardIds.ANT_NEURO_EE_211_BOARD.value,
                BoardIds.ANT_NEURO_EE_212_BOARD.value, BoardIds.ANT_NEURO_EE_213_BOARD.value,
                BoardIds.ANT_NEURO_EE_214_BOARD.value, BoardIds.ANT_NEURO_EE_215_BOARD.value,
                BoardIds.ANT_NEURO_EE_221_BOARD.value, BoardIds.ANT_NEURO_EE_222_BOARD.value,
                BoardIds.ANT_NEURO_EE_223_BOARD.value, BoardIds.ANT_NEURO_EE_224_BOARD.value,
                BoardIds.ANT_NEURO_EE_225_BOARD.value, BoardIds.ANT_NEURO_EE_511_BOARD.value
            ]:
                requirements.pop("timeout")
                return requirements

            # Enophone - no required parameters (can auto-discover paired devices)
            elif board_id == BoardIds.ENOPHONE_BOARD.value:
                requirements.pop("timeout")
                return requirements

            # BrainAlive - no required parameters (auto-discovery)
            elif board_id == BoardIds.BRAINALIVE_BOARD.value:
                requirements.pop("timeout")
                return requirements

            # Mentalab Explore boards - no required parameters (can auto-discover paired devices)
            elif board_id in [BoardIds.EXPLORE_4_CHAN_BOARD.value, BoardIds.EXPLORE_8_CHAN_BOARD.value]:
                requirements.pop("timeout")
                return requirements

            # Check for newer Explore boards if they exist
            elif hasattr(BoardIds, 'EXPLORE_PLUS_8_CHAN_BOARD') and board_id == BoardIds.EXPLORE_PLUS_8_CHAN_BOARD.value:
                requirements.pop("timeout")
                return requirements

            elif hasattr(BoardIds, 'EXPLORE_PLUS_32_CHAN_BOARD') and board_id == BoardIds.EXPLORE_PLUS_32_CHAN_BOARD.value:
                requirements.pop("timeout")
                return requirements

            # EmotiBit - no required parameters (auto-discovery)
            elif board_id == BoardIds.EMOTIBIT_BOARD.value:
                requirements.pop("timeout")
                return requirements

            # PiEEG - no required parameters (has defaults)
            elif board_id == BoardIds.PIEEG_BOARD.value:
                requirements.pop("timeout")
                return requirements

            # NeuroPawn Knight - serial_port required
            elif board_id == BoardIds.NEUROPAWN_KNIGHT_BOARD.value:
                requirements["serial_port"] = True
                requirements.pop("timeout")
                return requirements

            # BioListener - timeout optional (not in the original enum but mentioned in docs)
            elif hasattr(BoardIds, 'BIOLISTENER_BOARD') and board_id == BoardIds.BIOLISTENER_BOARD.value:
                return requirements

            # Undocumented boards - make educated guesses based on patterns
            # Galea boards (likely similar to other EEG boards)
            elif board_id in [getattr(BoardIds, attr, -999) for attr in ['GALEA_BOARD', 'GALEA_SERIAL_BOARD', 'GALEA_BOARD_V4', 'GALEA_SERIAL_BOARD_V4'] if hasattr(BoardIds, attr)]:
                # Serial variants likely need serial port
                if 'SERIAL' in [attr for attr in dir(BoardIds) if getattr(BoardIds, attr, -999) == board_id]:
                    requirements["serial_port"] = True
                requirements.pop("timeout")
                return requirements

            # NTL WiFi board (likely similar to other WiFi boards)
            elif hasattr(BoardIds, 'NTL_WIFI_BOARD') and board_id == BoardIds.NTL_WIFI_BOARD.value:
                requirements["ip_port"] = True
                return requirements

            # AAVAA board (unknown requirements)
            elif hasattr(BoardIds, 'AAVAA_V3_BOARD') and board_id == BoardIds.AAVAA_V3_BOARD.value:
                requirements.pop("timeout")
                return requirements

        except AttributeError:
            # Some board IDs might not exist in this version of BrainFlow
            pass

        # Fallback: try to determine requirements based on board name
        try:
            board_name = BoardShim.get_device_name(board_id).lower()

            # OpenBCI boards
            if "cyton" in board_name and "wifi" not in board_name:
                requirements["serial_port"] = True
                requirements.pop("timeout")
            elif "ganglion" in board_name and "native" not in board_name and "wifi" not in board_name:
                requirements["serial_port"] = True
            elif ("ganglion" in board_name or "cyton" in board_name) and "wifi" in board_name:
                requirements["ip_port"] = True
            elif "brainbit" in board_name and "bled" not in board_name:
                pass  # Keep timeout for BrainBit
            elif "callibri" in board_name:
                pass  # Keep timeout for Callibri
            elif "biolistener" in board_name:
                pass  # Keep timeout for BioListener
            elif "galea" in board_name and "serial" in board_name:
                requirements["serial_port"] = True
                requirements.pop("timeout")
            elif "wifi" in board_name:
                requirements["ip_port"] = True
            else:
                # Other boards with serial port requirements
                if any(name in board_name for name in ["freeeeg", "neuropawn", "knight", "serial"]):
                    requirements["serial_port"] = True
                elif "brainbit" in board_name and "bled" in board_name:
                    requirements["serial_port"] = True
                elif "muse" in board_name and "bled" in board_name:
                    requirements["serial_port"] = True
                
                # Remove timeout for boards that don't mention it
                requirements.pop("timeout")

        except Exception as e:
            logging.warning(
                f"Could not determine requirements for board ID {board_id}: {e}"
            )
            # Default: remove timeout if we can't determine the board type
            requirements.pop("timeout")

        return requirements

    def create_board_params(
        self, board_id: int, params_dict: Dict[str, str]
    ) -> BrainFlowInputParams:
        """
        Create BrainFlowInputParams from a dictionary of parameters.

        Args:
            board_id: ID of the board
            params_dict: Dictionary with parameter values

        Returns:
            Configured BrainFlowInputParams object
        """
        input_params = BrainFlowInputParams()

        # Set all provided parameters
        if "serial_port" in params_dict and params_dict["serial_port"]:
            input_params.serial_port = params_dict["serial_port"]

        if "mac_address" in params_dict and params_dict["mac_address"]:
            input_params.mac_address = params_dict["mac_address"]

        if "ip_address" in params_dict and params_dict["ip_address"]:
            input_params.ip_address = params_dict["ip_address"]

        if "ip_port" in params_dict and params_dict["ip_port"]:
            if (
                isinstance(params_dict["ip_port"], str)
                and params_dict["ip_port"].isdigit()
            ):
                input_params.ip_port = int(params_dict["ip_port"])
            elif isinstance(params_dict["ip_port"], int):
                input_params.ip_port = params_dict["ip_port"]

        if "other_info" in params_dict and params_dict["other_info"]:
            input_params.other_info = params_dict["other_info"]

        if "serial_number" in params_dict and params_dict["serial_number"]:
            input_params.serial_number = params_dict["serial_number"]

        if "file" in params_dict and params_dict["file"]:
            input_params.file = params_dict["file"]

        if "master_board" in params_dict and params_dict["master_board"]:
            try:
                master_board = params_dict["master_board"]
                if isinstance(master_board, int):
                    input_params.master_board = master_board
                else:
                    input_params.master_board = int(master_board)
            except:
                pass  # Ignore if we can't set master board

        if "timeout" in params_dict and params_dict["timeout"]:
            try:
                timeout = params_dict["timeout"]
                if isinstance(timeout, int):
                    input_params.timeout = timeout
                else:
                    input_params.timeout = int(timeout)
            except:
                pass  # Ignore if we can't set timeout

        return input_params

    def get_preset_info(self) -> Dict[int, str]:
        """
        Get information about available presets.

        Returns:
            Dictionary mapping preset values to descriptions
        """
        return {
            BrainFlowPresets.DEFAULT_PRESET.value: "Default data (usually EEG)",
            BrainFlowPresets.AUXILIARY_PRESET.value: "Auxiliary data (accel, gyro, etc.)",
            BrainFlowPresets.ANCILLARY_PRESET.value: "Ancillary data (PPG, temperature, etc.)",
        }

    def get_board_description(
        self, board_id: int, preset: Optional[int] = None
    ) -> Dict:
        """
        Get detailed description of a board.

        Args:
            board_id: ID of the board
            preset: Data preset to use

        Returns:
            Dictionary with board description
        """
        if preset is None:
            preset = BrainFlowPresets.DEFAULT_PRESET.value

        try:
            # Use get_board_descr as recommended in the error message
            description = BoardShim.get_board_descr(board_id, preset)
            return description
        except Exception as e:
            logging.debug(f"Error getting board description: {e}")

            # Return minimal description based on device name
            try:
                name = BoardShim.get_device_name(board_id)
            except:
                name = f"Board ID {board_id}"

            # Create a minimal description dictionary
            minimal_desc = {"name": name, "board_id": board_id, "preset": preset}

            # For special boards add additional information
            if board_id == BoardIds.SYNTHETIC_BOARD.value:
                minimal_desc["sampling_rate"] = 250
                minimal_desc["eeg_channels"] = [0, 1, 2, 3]
                minimal_desc["eeg_names"] = ["Fp1", "Fp2", "C3", "C4"]

            # For playback and streaming boards
            elif board_id == BoardIds.PLAYBACK_FILE_BOARD.value:
                minimal_desc["sampling_rate"] = (
                    250  # Default, will be overridden by file
                )
                minimal_desc["eeg_channels"] = [0, 1, 2, 3]  # Example channels
                minimal_desc["eeg_names"] = ["CH1", "CH2", "CH3", "CH4"]

            elif board_id == BoardIds.STREAMING_BOARD.value:
                minimal_desc["sampling_rate"] = (
                    250  # Default, will be determined by master board
                )
                minimal_desc["eeg_channels"] = [0, 1, 2, 3]  # Example channels
                minimal_desc["eeg_names"] = ["CH1", "CH2", "CH3", "CH4"]

            return minimal_desc

    def get_protocol_types(self) -> Dict[int, str]:
        """
        Get information about available IP protocol types.

        Returns:
            Dictionary mapping protocol type values to descriptions
        """
        # Import IpProtocolTypes here to avoid circular imports
        try:
            from brainflow.board_shim import IpProtocolTypes

            return {
                IpProtocolTypes.NO_IP_PROTOCOL.value: "No Protocol",
                IpProtocolTypes.UDP.value: "UDP",
                IpProtocolTypes.TCP.value: "TCP",
            }
        except:
            # If IpProtocolTypes is not available in this version
            return {0: "No Protocol", 1: "UDP", 2: "TCP"}


# Add static method wrappers for backward compatibility
class BoardConfiguration:
    """
    Static wrapper for BrainFlowBoardConfiguration for backward compatibility.
    """

    @staticmethod
    def get_all_boards() -> List[Tuple[str, int]]:
        """Static wrapper for backward compatibility."""
        instance = BrainFlowBoardConfiguration()
        return instance.get_all_boards()

    @staticmethod
    def get_board_groups() -> Dict[str, List[Tuple[str, int]]]:
        """Static wrapper for backward compatibility."""
        instance = BrainFlowBoardConfiguration()
        return instance.get_board_groups()

    @staticmethod
    def get_board_requirements(board_id: int) -> Dict[str, bool]:
        """Static wrapper for backward compatibility."""
        instance = BrainFlowBoardConfiguration()
        return instance.get_board_requirements(board_id)

    @staticmethod
    def create_input_params(
        board_id: int, params_dict: Dict[str, str]
    ) -> BrainFlowInputParams:
        """Static wrapper for backward compatibility."""
        instance = BrainFlowBoardConfiguration()
        return instance.create_board_params(board_id, params_dict)

    @staticmethod
    def get_preset_info() -> Dict[int, str]:
        """Static wrapper for backward compatibility."""
        instance = BrainFlowBoardConfiguration()
        return instance.get_preset_info()

    @staticmethod
    def get_board_description(
        board_id: int, preset: int = BrainFlowPresets.DEFAULT_PRESET.value
    ) -> Dict:
        """Static wrapper for backward compatibility."""
        instance = BrainFlowBoardConfiguration()
        return instance.get_board_description(board_id, preset)

    @staticmethod
    def get_protocol_types() -> Dict[int, str]:
        """Static wrapper for backward compatibility."""
        instance = BrainFlowBoardConfiguration()
        return instance.get_protocol_types()
