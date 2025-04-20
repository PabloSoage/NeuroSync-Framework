from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any


class BoardInterface(ABC):
    """
    Interface for device board configuration.
    """
    
    @abstractmethod
    def get_all_boards(self) -> List[Tuple[str, int]]:
        """
        Get a list of all available boards.
        
        Returns:
            List of tuples containing (board_name, board_id)
        """
        pass
    
    @abstractmethod
    def get_board_groups(self) -> Dict[str, List[Tuple[str, int]]]:
        """
        Get boards grouped by type.
        
        Returns:
            Dictionary with board types as keys and lists of (board_name, board_id) as values
        """
        pass
    
    @abstractmethod
    def get_board_requirements(self, board_id: Any) -> Dict[str, bool]:
        """
        Get the parameters required for a specific board.
        
        Args:
            board_id: ID of the board
            
        Returns:
            Dictionary with parameters as keys and boolean indicating if required
        """
        pass
    
    @abstractmethod
    def create_board_params(self, board_id: Any, params_dict: Dict[str, Any]) -> Any:
        """
        Create board input parameters from a dictionary.
        
        Args:
            board_id: ID of the board
            params_dict: Dictionary with parameter values
            
        Returns:
            Configured board parameters object
        """
        pass
    
    @abstractmethod
    def get_board_description(self, board_id: Any, preset: Any = None) -> Dict[str, Any]:
        """
        Get detailed description of a board.
        
        Args:
            board_id: ID of the board
            preset: Data preset to use
            
        Returns:
            Dictionary with board description
        """
        pass
