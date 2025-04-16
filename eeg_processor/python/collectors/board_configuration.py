import logging
import os
from typing import Dict, List, Optional, Tuple

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowPresets


class BoardConfiguration:
    """
    Helper class to manage board configurations and provide information about available boards.
    """
    
    @staticmethod
    def get_all_boards() -> List[Tuple[str, int]]:
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
            if attr.startswith('__'):
                continue
                
            try:
                board_id = getattr(BoardIds, attr)
                # Skip if not an integer or already added
                if not isinstance(board_id, int) or any(b[1] == board_id for b in special_boards):
                    continue
                    
                # Get board name safely
                try:
                    board_name = BoardShim.get_device_name(board_id)
                    boards.append((board_name, board_id))
                except Exception as e:
                    # If we can't get the name, use the attribute name
                    boards.append((attr.replace('_', ' ').title(), board_id))
            except Exception as e:
                logging.debug(f"Error processing board ID {attr}: {e}")
                
        return boards

    @staticmethod
    def get_board_groups() -> Dict[str, List[Tuple[str, int]]]:
        """
        Get boards grouped by type.
        
        Returns:
            Dictionary with board types as keys and lists of (board_name, board_id) as values
        """
        all_boards = BoardConfiguration.get_all_boards()
        
        # Define groups
        groups = {
            "Special/Synthetic": [],
            "OpenBCI": [],
            "Muse": [],
            "Neurosity": [],
            "g.tec": [],
            "ANT Neuro": [],
            "Other": []
        }
        
        # Special handling for synthetic, playback and streaming boards
        special_board_ids = [BoardIds.SYNTHETIC_BOARD.value, BoardIds.PLAYBACK_FILE_BOARD.value, BoardIds.STREAMING_BOARD.value]
        
        for board_name, board_id in all_boards:
            board_name_lower = board_name.lower()
            
            if board_id in special_board_ids:
                groups["Special/Synthetic"].append((board_name, board_id))
            elif "openbci" in board_name_lower or "cyton" in board_name_lower or "ganglion" in board_name_lower:
                groups["OpenBCI"].append((board_name, board_id))
            elif "muse" in board_name_lower:
                groups["Muse"].append((board_name, board_id))
            elif "neurosity" in board_name_lower or "notion" in board_name_lower or "crown" in board_name_lower:
                groups["Neurosity"].append((board_name, board_id))
            elif "g.tec" in board_name_lower or "unicorn" in board_name_lower or "gtec" in board_name_lower:
                groups["g.tec"].append((board_name, board_id))
            elif "ant" in board_name_lower or "neuro" in board_name_lower:
                groups["ANT Neuro"].append((board_name, board_id))
            else:
                groups["Other"].append((board_name, board_id))
                
        return groups
        
    @staticmethod
    def get_board_requirements(board_id: int) -> Dict[str, bool]:
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
            "master_board": False
        }
        
        # Define requirements for special boards
        if board_id == BoardIds.SYNTHETIC_BOARD.value:
            # Synthetic board doesn't need any parameters
            return requirements
            
        if board_id == BoardIds.PLAYBACK_FILE_BOARD.value:
            requirements["file"] = True
            requirements["master_board"] = True
            return requirements
            
        if board_id == BoardIds.STREAMING_BOARD.value:
            requirements["ip_address"] = True
            requirements["ip_port"] = True
            requirements["master_board"] = True
            return requirements
            
        # Try to determine requirements based on board name or ID for other boards
        try:
            board_name = BoardShim.get_device_name(board_id).lower()
            
            # OpenBCI boards
            if "cyton" in board_name or "ganglion" in board_name:
                if "wifi" in board_name:
                    requirements["ip_address"] = True
                    requirements["ip_port"] = True
                else:
                    requirements["serial_port"] = True
                    
            # Bluetooth boards
            if "bled" in board_name or "muse" in board_name:
                requirements["mac_address"] = True
                
            # Unicorn board
            if "unicorn" in board_name:
                requirements["serial_number"] = True
                
        except Exception as e:
            logging.warning(f"Could not determine requirements for board ID {board_id}: {e}")
            
        return requirements
            
    @staticmethod
    def create_input_params(board_id: int, params_dict: Dict[str, str]) -> BrainFlowInputParams:
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
            if isinstance(params_dict["ip_port"], str) and params_dict["ip_port"].isdigit():
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
                
        return input_params
        
    @staticmethod
    def get_preset_info() -> Dict[int, str]:
        """
        Get information about available presets.
        
        Returns:
            Dictionary mapping preset values to descriptions
        """
        return {
            BrainFlowPresets.DEFAULT_PRESET.value: "Default data (usually EEG)",
            BrainFlowPresets.AUXILIARY_PRESET.value: "Auxiliary data (accel, gyro, etc.)",
            BrainFlowPresets.ANCILLARY_PRESET.value: "Ancillary data (PPG, temperature, etc.)"
        }
        
    @staticmethod
    def get_board_description(board_id: int, preset: int = BrainFlowPresets.DEFAULT_PRESET.value) -> Dict:
        """
        Get detailed description of a board.
        
        Args:
            board_id: ID of the board
            preset: Data preset to use
            
        Returns:
            Dictionary with board description
        """
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
            minimal_desc = {
                "name": name,
                "board_id": board_id,
                "preset": preset
            }
            
            # For special boards add additional information
            if board_id == BoardIds.SYNTHETIC_BOARD.value:
                minimal_desc["sampling_rate"] = 250
                minimal_desc["eeg_channels"] = [0, 1, 2, 3]
                minimal_desc["eeg_names"] = ["Fp1", "Fp2", "C3", "C4"]
                
            # For playback and streaming boards
            elif board_id == BoardIds.PLAYBACK_FILE_BOARD.value:
                minimal_desc["sampling_rate"] = 250  # Default, will be overridden by file
                minimal_desc["eeg_channels"] = [0, 1, 2, 3]  # Example channels
                minimal_desc["eeg_names"] = ["CH1", "CH2", "CH3", "CH4"]
            
            elif board_id == BoardIds.STREAMING_BOARD.value:
                minimal_desc["sampling_rate"] = 250  # Default, will be determined by master board
                minimal_desc["eeg_channels"] = [0, 1, 2, 3]  # Example channels
                minimal_desc["eeg_names"] = ["CH1", "CH2", "CH3", "CH4"]
                
            return minimal_desc

    @staticmethod
    def get_protocol_types() -> Dict[int, str]:
        """
        Get information about available IP protocol types.
        
        Returns:
            Dictionary mapping protocol type values to descriptions
        """
        return {
            IpProtocolTypes.NO_IP_PROTOCOL.value: "No Protocol",
            IpProtocolTypes.UDP.value: "UDP",
            IpProtocolTypes.TCP.value: "TCP"
        }
