"""
PS4 controller visualization module.

Provides a widget for visualizing PS4 controller state.
"""
import json
import time
import os
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple

from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QRect, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QTransform, QFont, QCursor

from ..interfaces import InputData
from .visualizer_base import BaseVisualizer


class PS4ControllerVisualizer(BaseVisualizer):
    """
    Widget that visualizes the PS4 controller state.
    
    This class renders the PS4 controller with visual feedback for buttons,
    analog sticks, and trigger states.
    """
    
    # Signal for edit mode
    key_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None) -> None:
        """Initialize the PS4 controller visualizer."""
        super().__init__(parent)
        
        # Controller state
        self.button_states = {}
        self.stick_positions = {'left': (0, 0), 'right': (0, 0)}
        self.trigger_values = {'left': 0, 'right': 0}
        
        # Visualization settings
        self.image_mode = True  # Use images vs drawn controller
        self.images_loaded = False
        self.images = {}
        self.base_image = None
        
        # Get positions file path
        self.positions_file = Path(__file__).parent / 'ps4' / 'controller_positions.json'
        
        # Ensure parent directories exist
        os.makedirs(Path(__file__).parent / 'ps4', exist_ok=True)
        
        # Edit mode state
        self._edit_mode = False
        self.selected_item = None
        self.drag_start = None
        
        # Define element groups for grouped movement
        self.element_groups = {
            'action_buttons': ['X_pressed', 'Circle_pressed', 'Square_pressed', 'Triangle_pressed'],
            'dpad': ['dpad_up', 'dpad_down', 'dpad_left', 'dpad_right'],
            'sticks': ['left_stick_pressed', 'right_stick_pressed', 'stick_released'],
            'triggers': ['left_trigger_pressed', 'right_trigger_pressed'],
            'center_buttons': ['share_pressed', 'options_pressed', 'ps_pressed', 'touchpad_pressed'],
            'bumpers': ['bumper_pressed']
        }
        
        # Set controller-specific settings
        self.supported_collectors = ["ps4_controller"]
        
        # Load controller images with a timer to allow UI to initialize
        QTimer.singleShot(100, self.load_images)
        
        # Set a reasonable minimum size
        self.setMinimumSize(800, 600)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
    
    def load_images(self) -> None:
        """Load PS4 controller images."""
        try:
            assets_path = Path(__file__).parent / 'ps4' / 'pngs'
            
            if not assets_path.exists():
                print(f"PS4 controller assets path not found: {assets_path}")
                # Create the directory structure
                os.makedirs(assets_path, exist_ok=True)
                print(f"Created directory: {assets_path}")
                self.image_mode = False
                return
                
            # Load base controller image
            base_path = assets_path / 'controller_base.png'
            if base_path.exists():
                self.base_image = QPixmap(str(base_path))
                self.setMinimumSize(self.base_image.width(), self.base_image.height())
                self.resize(self.base_image.width() + 20, self.base_image.height() + 20)
            else:
                print(f"PS4 controller base image not found: {base_path}")
                self.image_mode = False
                return
            
            # Load positions from JSON if available
            image_mapping = self.load_positions_from_json()
            
            # Load images
            for key, info in image_mapping.items():
                img_path = assets_path / info['file']
                if img_path.exists():
                    pixmap = QPixmap(str(img_path))
                    # Convert position list to tuple
                    pos = tuple(info['pos']) if info['pos'] is not None else None
                    self.images[key] = {'pixmap': pixmap, 'pos': pos}
                else:
                    print(f"PS4 controller image not found: {img_path}")
            
            if self.base_image and len(self.images) > 0:
                self.images_loaded = True
                print(f"Loaded {len(self.images)} PS4 controller images")
            else:
                print("Failed to load sufficient PS4 controller images, using fallback mode")
                self.image_mode = False
                
        except Exception as e:
            print(f"Error loading PS4 controller images: {e}")
            import traceback
            traceback.print_exc()
            self.images_loaded = False
            self.image_mode = False
    
    def load_positions_from_json(self) -> Dict[str, Any]:
        """
        Load positions from JSON file.
        
        Returns:
            Dict[str, Any]: Dictionary mapping image keys to position information
        """
        try:
            if self.positions_file.exists():
                with open(self.positions_file, 'r') as f:
                    positions = json.load(f)
                    print(f"Loaded PS4 controller positions from {self.positions_file}")
                    return positions
            else:
                print(f"PS4 controller positions file not found: {self.positions_file}, using defaults")
                # Auto-create the positions file with defaults
                defaults = self.get_default_positions()
                try:
                    os.makedirs(self.positions_file.parent, exist_ok=True)
                    with open(self.positions_file, 'w') as f:
                        json.dump(defaults, f, indent=2)
                    print(f"Created default positions file: {self.positions_file}")
                except Exception as e:
                    print(f"Error creating default positions file: {e}")
                return defaults
        except Exception as e:
            print(f"Error loading PS4 controller positions: {e}")
            return self.get_default_positions()
    
    def get_default_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Return default hardcoded positions.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping image keys to default position information
        """
        return {
            'X_pressed': {'file': 'X_pressed.png', 'pos': [627, 273]},
            'Circle_pressed': {'file': 'Circle_pressed.png', 'pos': [685, 216]},
            'Square_pressed': {'file': 'Square_pressed.png', 'pos': [569, 216]},
            'Triangle_pressed': {'file': 'Triangle_pressed.png', 'pos': [627, 158]},
            'share_pressed': {'file': 'share_pressed.png', 'pos': [226, 141]},
            'options_pressed': {'file': 'options_pressed.png', 'pos': [550, 141]},
            'ps_pressed': {'file': 'ps_pressed.png', 'pos': [381, 337]},
            'touchpad_pressed': {'file': 'touchpad_pressed.png', 'pos': [271, 120]},
            'bumper_pressed': {'file': 'bumper_pressed.png', 'pos': [110, 94]},
            'left_trigger_pressed': {'file': 'left_trigger_pressed.png', 'pos': [109, 0]},
            'right_trigger_pressed': {'file': 'right_trigger_pressed.png', 'pos': [598, 0]},
            'left_stick_pressed': {'file': 'left_stick_pressed.png', 'pos': [228, 307]},
            'right_stick_pressed': {'file': 'right_stick_pressed.png', 'pos': [484, 308]},
            'stick_released': {'file': 'stick_released.png', 'pos': [228, 307]},
            'dpad_up': {'file': 'dpad_up.png', 'pos': [136, 183]},
            'dpad_down': {'file': 'dpad_down.png', 'pos': [136, 256]},
            'dpad_left': {'file': 'dpad_left.png', 'pos': [94, 227]},
            'dpad_right': {'file': 'dpad_right.png', 'pos': [164, 227]},
        }
    
    def save_positions_to_json(self) -> bool:
        """
        Save current positions to JSON file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            positions = {}
            for key, data in self.images.items():
                if data['pos'] is not None:
                    positions[key] = {
                        'file': f"{key}.png",
                        'pos': list(data['pos'])  # Convert tuples to lists for JSON serialization
                    }
            
            # Make sure directory exists
            os.makedirs(self.positions_file.parent, exist_ok=True)
            
            with open(self.positions_file, 'w') as f:
                json.dump(positions, f, indent=2)
            print(f"PS4 controller positions saved to {self.positions_file}")
            return True
        except Exception as e:
            print(f"Error saving PS4 controller positions: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update(self, input_data: Optional[InputData] = None) -> None:
        """
        Update the visualization based on input data.
        
        Args:
            input_data: Input event data containing controller state information
        """
        if not input_data:
            # Just repaint with current state
            self.repaint()
            return
            
        # Only process events from PS4 controller
        if input_data.event_type in ["button_press", "button_release"]:
            # Update button state
            if hasattr(input_data, 'key') and input_data.key:
                self.button_states[input_data.key] = (input_data.event_type == "button_press")
                
        elif input_data.event_type == "axis_motion":
            # Update stick or trigger state
            if hasattr(input_data, 'key') and input_data.key:
                if input_data.key == "Left_Stick_X" and hasattr(input_data, 'rel_x') and hasattr(input_data, 'rel_y'):
                    self.stick_positions['left'] = (input_data.rel_x, input_data.rel_y)
                elif input_data.key == "Right_Stick_X" and hasattr(input_data, 'rel_x') and hasattr(input_data, 'rel_y'):
                    self.stick_positions['right'] = (input_data.rel_x, input_data.rel_y)
                elif input_data.key == "Left_Trigger" and hasattr(input_data, 'rel_x'):
                    self.trigger_values['left'] = int(input_data.rel_x * 32767)
                elif input_data.key == "Right_Trigger" and hasattr(input_data, 'rel_x'):
                    self.trigger_values['right'] = int(input_data.rel_x * 32767)

        # Repaint with updated state
        self.repaint()
    
    def force_update(self) -> None:
        """Force a complete redraw of the visualization."""
        self.repaint()
    
    def toggle_edit_mode(self) -> bool:
        """
        Toggle edit mode.
        
        Returns:
            bool: New edit mode state
        """
        # Just call set_edit_mode with the opposite state
        self.set_edit_mode(not self._edit_mode)
        # Return the current state after toggling
        return self._edit_mode
    
    def set_edit_mode(self, enabled: bool) -> None:
        """
        Enable or disable edit mode.
        
        Args:
            enabled: Whether edit mode should be enabled
        """
        # Don't do anything if images aren't loaded
        if enabled and not self.images_loaded:
            print("Cannot enter edit mode - images not loaded")
            QMessageBox.warning(
                self,
                "Edit Mode Not Available",
                "Cannot enter edit mode because controller images are not properly loaded."
            )
            self._edit_mode = False
            return
        
        print(f"PS4ControllerVisualizer: set_edit_mode({enabled}) - Previous state: {self._edit_mode}")
            
        # Set the state to the requested value
        self._edit_mode = enabled
        self.selected_item = None
        self.drag_start = None
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        
        # Force a complete repaint - this ensures overlays show/hide immediately
        self.repaint()
        print(f"PS4ControllerVisualizer: Edit mode now: {self._edit_mode}")

    def toggle_image_mode(self) -> bool:
        """
        Toggle between image mode and drawn mode.
        
        Returns:
            bool: New image mode state (True for image mode, False for drawn mode)
        """
        # Only toggle if images are loaded
        if self.images_loaded:
            self.image_mode = not self.image_mode
        else:
            # Set to drawn mode if images aren't loaded
            self.image_mode = False
        
        self.repaint()
        # Return the current mode state
        return self.image_mode
    
    def set_image_mode(self, use_image_mode: bool) -> bool:
        """
        Set the visualization mode directly.
        
        Args:
            use_image_mode: Whether to use image mode (True) or drawn mode (False)
        
        Returns:
            bool: Actual mode that was set
        """
        # Only set to image mode if images are loaded
        if use_image_mode and not self.images_loaded:
            self.image_mode = False
        else:
            # Otherwise set as requested
            self.image_mode = use_image_mode
        
        self.repaint()
        return self.image_mode
    
    def find_group_for_item(self, item_key: str) -> Optional[str]:
        """
        Find which group an item belongs to.
        
        Args:
            item_key: The item key to find
            
        Returns:
            Optional[str]: Group name or None if not found
        """
        for group_name, items in self.element_groups.items():
            if item_key in items:
                return group_name
        return None
    
    def move_group(self, group_name: str, delta_x: int, delta_y: int) -> None:
        """
        Move all items in a group by the same delta.
        
        Args:
            group_name: Name of the group to move
            delta_x: X-axis movement amount
            delta_y: Y-axis movement amount
        """
        if group_name in self.element_groups:
            for item_key in self.element_groups[group_name]:
                if item_key in self.images and self.images[item_key]['pos'] is not None:
                    old_pos = self.images[item_key]['pos']
                    new_pos = (old_pos[0] + delta_x, old_pos[1] + delta_y)
                    self.images[item_key]['pos'] = new_pos

    def mousePressEvent(self, event):
        """Handle mouse press events for edit mode and button selection."""
        if not self._edit_mode or not self.images_loaded:
            return super().mousePressEvent(event)
            
        if event.button() == Qt.LeftButton:
            # Find which overlay was clicked
            pos = event.pos()
            for key, data in self.images.items():
                if data['pos'] is not None:
                    pixmap_rect = QRect(data['pos'][0], data['pos'][1], 
                                      data['pixmap'].width(), data['pixmap'].height())
                    if pixmap_rect.contains(pos):
                        self.selected_item = key
                        self.drag_start = pos
                        self.repaint()  # Redraw to show selection
                        print(f"Selected item: {key}")
                        return
            
            # If we reach here, no item was clicked
            self.selected_item = None
            self.drag_start = None
            self.repaint()
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement events for drag operations in edit mode."""
        if not self._edit_mode or not self.selected_item or not self.drag_start:
            return super().mouseMoveEvent(event)
            
        current_pos = event.pos()
        delta_x = current_pos.x() - self.drag_start.x()
        delta_y = current_pos.y() - self.drag_start.y()
        
        # Check if we should move the group or individual item
        group = self.find_group_for_item(self.selected_item)
        
        try:
            if group and not QApplication.keyboardModifiers() & Qt.ShiftModifier:
                # Move entire group (default behavior)
                self.move_group(group, delta_x, delta_y)
            else:
                # Move individual item (when Shift is held)
                if self.selected_item in self.images and self.images[self.selected_item]['pos'] is not None:
                    old_pos = self.images[self.selected_item]['pos']
                    new_pos = (old_pos[0] + delta_x, old_pos[1] + delta_y)
                    self.images[self.selected_item]['pos'] = new_pos
        
            self.drag_start = current_pos
            self.repaint()
        except Exception as e:
            print(f"Error in mouseMoveEvent: {e}")
            import traceback
            traceback.print_exc()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events for edit mode."""
        if not self._edit_mode:
            return super().mouseReleaseEvent(event)
            
        if event.button() == Qt.LeftButton and self.selected_item:
            # Save the positions to JSON
            self.save_positions_to_json()
                
            # Reset drag state but keep selection
            self.drag_start = None
            self.repaint()  # Update to remove drag indicators
    
    def paintEvent(self, event):
        """Paint the PS4 controller visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.image_mode and self.images_loaded:
            self.paint_image_mode(painter)
        else:
            self.paint_drawn_mode(painter)
            
        # Draw edit mode overlays
        if self._edit_mode and self.images_loaded:
            self.paint_edit_overlays(painter)
    
    def paint_edit_overlays(self, painter):
        """Draw edit mode visual aids."""
        try:
            # Draw bounding boxes around all overlays
            for key, data in self.images.items():
                if data['pos'] is not None:
                    rect = QRect(data['pos'][0], data['pos'][1],
                               data['pixmap'].width(), data['pixmap'].height())
                    
                    # Highlight selected item with green
                    if key == self.selected_item:
                        painter.setPen(QPen(QColor(0, 255, 0), 3))
                        painter.drawRect(rect)
                    # Draw red box around regular items
                    else:
                        painter.setPen(QPen(QColor(255, 0, 0), 1))
                        painter.drawRect(rect)
                    
                    # Show item name
                    painter.setPen(QPen(QColor(255, 255, 255)))
                    painter.setFont(QFont("Arial", 8))
                    painter.drawText(rect.topLeft() - QPoint(0, 5), key)
            
            # Draw blue dashed lines around groups
            painter.setPen(QPen(QColor(0, 0, 255, 128), 1, Qt.DashLine))
            for group_name, items in self.element_groups.items():
                rects = []
                for item_key in items:
                    if item_key in self.images and self.images[item_key]['pos'] is not None:
                        pos = self.images[item_key]['pos']
                        pixmap = self.images[item_key]['pixmap']
                        rects.append(QRect(pos[0], pos[1], pixmap.width(), pixmap.height()))
                
                if rects:
                    # Calculate union of all rectangles in the group
                    united = rects[0]
                    for rect in rects[1:]:
                        united = united.united(rect)
                    
                    # Draw group bounding box
                    painter.drawRect(united)
                    # Label the group
                    painter.setPen(QPen(QColor(50, 50, 255)))
                    painter.setFont(QFont("Arial", 10))
                    painter.drawText(united.topLeft() - QPoint(0, 10), group_name)
                    
            # Add edit mode instructions at the bottom center of the controller
            if self.base_image:
                # Calculate position for bottom center
                text_x = self.base_image.width() // 2 - 200  # Center text horizontally with wider margin
                text_y = self.base_image.height() - 40  # Place near bottom
                
                # Draw a semi-transparent background for better readability - INCREASED HEIGHT TO 45 PIXELS
                painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
                painter.setPen(Qt.NoPen)
                text_rect = QRect(text_x - 10, text_y - 20, 420, 45)  # Wider and taller rectangle
                painter.drawRoundedRect(text_rect, 5, 5)
                
                # Draw instructions text
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.setFont(QFont("Arial", 10, QFont.Bold))
                painter.drawText(text_rect, Qt.AlignCenter, "Edit Mode: Drag to move items, hold Shift for individual items")
            
        except Exception as e:
            print(f"Error in paint_edit_overlays: {e}")
            import traceback
            traceback.print_exc()

    def paint_image_mode(self, painter):
        """Paint using loaded images."""
        try:
            if not self.base_image:
                painter.setPen(QPen(QColor(255, 0, 0)))
                painter.drawText(10, 30, "Error: Base controller image not loaded")
                return
                
            # Draw base controller
            painter.drawPixmap(0, 0, self.base_image)
            
            # In edit mode, show all overlays
            if self._edit_mode:
                for key, data in self.images.items():
                    if data['pos'] is not None and key != 'stick_released':
                        painter.drawPixmap(data['pos'][0], data['pos'][1], data['pixmap'])
                
                # Special handling for right bumper (R1) in edit mode
                if 'bumper_pressed' in self.images:
                    bumper = self.images['bumper_pressed']['pixmap']
                    flipped_bumper = bumper.transformed(QTransform().scale(-1, 1))
                    # Position R1 at a fixed offset from L1
                    l1_pos = self.images['bumper_pressed']['pos']
                    r1_pos = (l1_pos[0] + 489, l1_pos[1])  # Offset for R1 position
                    painter.drawPixmap(r1_pos[0], r1_pos[1], flipped_bumper)
            else:
                # Normal mode - show only pressed buttons
                button_image_map = {
                    'cross': 'X_pressed',
                    'circle': 'Circle_pressed', 
                    'square': 'Square_pressed',
                    'triangle': 'Triangle_pressed',
                    'share': 'share_pressed',
                    'options': 'options_pressed',
                    'ps': 'ps_pressed',
                    'touchpad': 'touchpad_pressed',
                    'l1': 'bumper_pressed',
                    'dpad_up': 'dpad_up',
                    'dpad_down': 'dpad_down',
                    'dpad_left': 'dpad_left',
                    'dpad_right': 'dpad_right'
                }
                
                for button, image_key in button_image_map.items():
                    if self.button_states.get(button, False) and image_key in self.images:
                        img_data = self.images[image_key]
                        if img_data['pos'] is not None:
                            painter.drawPixmap(img_data['pos'][0], img_data['pos'][1], img_data['pixmap'])
                
                # Draw R1 (flipped bumper)
                if self.button_states.get('r1', False) and 'bumper_pressed' in self.images:
                    bumper = self.images['bumper_pressed']['pixmap']
                    flipped_bumper = bumper.transformed(QTransform().scale(-1, 1))
                    # Position R1 at a fixed offset from L1
                    l1_pos = self.images['bumper_pressed']['pos']
                    if l1_pos is not None:
                        r1_pos = (l1_pos[0] + 489, l1_pos[1]) # Offset for R1 position
                        painter.drawPixmap(r1_pos[0], r1_pos[1], flipped_bumper)
                
                # Draw analog sticks with movement
                self.draw_image_analog_sticks(painter)
                
                # Draw triggers with pressure
                self.draw_image_triggers(painter)
        except Exception as e:
            print(f"Error in paint_image_mode: {e}")
            import traceback
            traceback.print_exc()
            
            # Draw error message
            painter.setPen(QPen(QColor(255, 0, 0)))
            painter.drawText(10, 30, f"Error rendering controller: {str(e)}")
    
    def draw_image_analog_sticks(self, painter):
        """Draw analog sticks with images and movement."""
        try:
            stick_released_img = self.images.get('stick_released', {}).get('pixmap')
            left_pressed_img = self.images.get('left_stick_pressed', {}).get('pixmap')
            right_pressed_img = self.images.get('right_stick_pressed', {}).get('pixmap')
            
            # Skip if missing required images or positions
            if (not stick_released_img or 
                'left_stick_pressed' not in self.images or 
                'right_stick_pressed' not in self.images or
                self.images['left_stick_pressed']['pos'] is None or
                self.images['right_stick_pressed']['pos'] is None):
                return
            
            # Left stick position from JSON
            left_base_pos = self.images['left_stick_pressed']['pos']
            left_x, left_y = self.stick_positions['left']
            left_offset_x = int(left_x * 15)
            left_offset_y = int(left_y * 15)
            
            if self.button_states.get('left_stick', False) and left_pressed_img:
                painter.drawPixmap(left_base_pos[0] + left_offset_x, 
                                left_base_pos[1] + left_offset_y, left_pressed_img)
            elif stick_released_img:
                painter.drawPixmap(left_base_pos[0] + left_offset_x, 
                                left_base_pos[1] + left_offset_y, stick_released_img)
            
            # Right stick position from JSON
            right_base_pos = self.images['right_stick_pressed']['pos']
            right_x, right_y = self.stick_positions['right']
            right_offset_x = int(right_x * 15)
            right_offset_y = int(right_y * 15)
            
            if self.button_states.get('right_stick', False) and right_pressed_img:
                painter.drawPixmap(right_base_pos[0] + right_offset_x,
                                right_base_pos[1] + right_offset_y, right_pressed_img)
            elif stick_released_img:
                painter.drawPixmap(right_base_pos[0] + right_offset_x,
                                right_base_pos[1] + right_offset_y, stick_released_img)
        except Exception as e:
            print(f"Error in draw_image_analog_sticks: {e}")
            import traceback
            traceback.print_exc()
    
    def draw_image_triggers(self, painter):
        """Draw triggers with pressure-based transparency."""
        try:
            # Left trigger (L2) with position from JSON
            left_trigger_value = self.trigger_values['left'] / 32767.0
            if left_trigger_value > 0.01 and 'left_trigger_pressed' in self.images:
                trigger_img = self.images['left_trigger_pressed']['pixmap']
                if trigger_img:
                    pos = self.images['left_trigger_pressed']['pos']
                    if pos is not None:
                        # Create transparent version
                        temp_pixmap = QPixmap(trigger_img.size())
                        temp_pixmap.fill(Qt.transparent)
                        temp_painter = QPainter(temp_pixmap)
                        temp_painter.setOpacity(left_trigger_value)
                        temp_painter.drawPixmap(0, 0, trigger_img)
                        temp_painter.end()
                        
                        painter.drawPixmap(pos[0], pos[1], temp_pixmap)
            
            # Right trigger (R2) with position from JSON
            right_trigger_value = self.trigger_values['right'] / 32767.0
            if right_trigger_value > 0.01 and 'right_trigger_pressed' in self.images:
                trigger_img = self.images['right_trigger_pressed']['pixmap']
                if trigger_img:
                    pos = self.images['right_trigger_pressed']['pos']
                    if pos is not None:
                        # Create transparent version
                        temp_pixmap = QPixmap(trigger_img.size())
                        temp_pixmap.fill(Qt.transparent)
                        temp_painter = QPainter(temp_pixmap)
                        temp_painter.setOpacity(right_trigger_value)
                        temp_painter.drawPixmap(0, 0, trigger_img)
                        temp_painter.end()
                        
                        painter.drawPixmap(pos[0], pos[1], temp_pixmap)
        except Exception as e:
            print(f"Error in draw_image_triggers: {e}")
            import traceback
            traceback.print_exc()
    
    def paint_drawn_mode(self, painter):
        """Paint using drawn shapes (fallback method)."""
        try:
            # Draw controller base
            painter.setBrush(QBrush(QColor(60, 60, 60)))
            painter.setPen(QPen(QColor(40, 40, 40), 3))
            
            # Main controller body
            controller_rect = QRect(50, 150, 700, 400)
            painter.drawRoundedRect(controller_rect, 30, 30)
            
            # Draw handles
            left_handle = QRect(50, 350, 150, 200)
            right_handle = QRect(600, 350, 150, 200)
            painter.drawRoundedRect(left_handle, 20, 20)
            painter.drawRoundedRect(right_handle, 20, 20)
            
            # Draw touchpad - Fixed detection
            touchpad_rect = QRect(300, 180, 200, 100)
            color = QColor(0, 150, 255) if self.button_states.get('touchpad', False) else QColor(80, 80, 80)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(touchpad_rect, 5, 5)
            
            # Add touchpad label
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(touchpad_rect.center().x() - 30, touchpad_rect.center().y() + 5, "TOUCHPAD")
            painter.setPen(QPen(QColor(40, 40, 40), 3))
            
            # Draw D-pad
            self.draw_dpad(painter, 150, 250)
            
            # Draw action buttons (Triangle, Circle, X, Square)
            self.draw_action_buttons(painter, 580, 250)
            
            # Draw analog sticks
            self.draw_analog_stick(painter, 200, 380, 'left')
            self.draw_analog_stick(painter, 530, 380, 'right')
            
            # Draw shoulder buttons
            self.draw_shoulder_buttons(painter)
            
            # Draw triggers
            self.draw_triggers(painter)
            
            # Draw start/select buttons
            self.draw_start_select(painter)
            
            # Draw PS button
            ps_color = QColor(0, 100, 200) if self.button_states.get('ps', False) else QColor(40, 40, 40)
            painter.setBrush(QBrush(ps_color))
            painter.drawEllipse(375, 320, 50, 50)
        except Exception as e:
            print(f"Error in paint_drawn_mode: {e}")
            import traceback
            traceback.print_exc()
        
    def draw_dpad(self, painter, x, y):
        """Draw the D-pad with current state."""
        buttons = ['up', 'down', 'left', 'right']
        positions = [(x+25, y), (x+25, y+50), (x, y+25), (x+50, y+25)]
        sizes = [(25, 25), (25, 25), (25, 25), (25, 25)]
        
        for i, button in enumerate(buttons):
            color = QColor(0, 150, 0) if self.button_states.get(f'dpad_{button}', False) else QColor(80, 80, 80)
            painter.setBrush(QBrush(color))
            px, py = positions[i]
            w, h = sizes[i]
            painter.drawRect(px, py, w, h)
            
    def draw_action_buttons(self, painter, x, y):
        """Draw action buttons with current state."""
        buttons = [('triangle', '△'), ('circle', '○'), ('cross', '✕'), ('square', '□')]
        positions = [(x+25, y), (x+50, y+25), (x+25, y+50), (x, y+25)]
        
        for i, (button, symbol) in enumerate(buttons):
            px, py = positions[i]
            color = QColor(0, 150, 0) if self.button_states.get(button, False) else QColor(80, 80, 80)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(px, py, 25, 25)
            
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(px+8, py+18, symbol)
            painter.setPen(QPen(QColor(40, 40, 40), 3))
            
    def draw_analog_stick(self, painter, x, y, stick):
        """Draw an analog stick with current position."""
        # Base circle
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.drawEllipse(x, y, 60, 60)
        
        # Stick position
        stick_x, stick_y = self.stick_positions[stick]
        offset_x = int(stick_x * 15)  # Scale movement
        offset_y = int(stick_y * 15)
        
        color = QColor(0, 150, 0) if self.button_states.get(f'{stick}_stick', False) else QColor(120, 120, 120)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(x + 15 + offset_x, y + 15 + offset_y, 30, 30)
        
    def draw_shoulder_buttons(self, painter):
        """Draw shoulder buttons with current state."""
        # L1, R1
        l1_color = QColor(0, 150, 0) if self.button_states.get('l1', False) else QColor(80, 80, 80)
        r1_color = QColor(0, 150, 0) if self.button_states.get('r1', False) else QColor(80, 80, 80)
        
        painter.setBrush(QBrush(l1_color))
        painter.drawRect(100, 120, 80, 20)
        painter.setBrush(QBrush(r1_color))
        painter.drawRect(620, 120, 80, 20)
        
    def draw_triggers(self, painter):
        """Draw triggers with current pressure values."""
        # L2, R2 with analog values
        l2_intensity = int(self.trigger_values['left'] * 255 / 32767)
        r2_intensity = int(self.trigger_values['right'] * 255 / 32767)
        
        l2_color = QColor(0, l2_intensity, 0) if l2_intensity > 0 else QColor(80, 80, 80)
        r2_color = QColor(0, r2_intensity, 0) if r2_intensity > 0 else QColor(80, 80, 80)
        
        painter.setBrush(QBrush(l2_color))
        painter.drawRect(120, 90, 60, 20)
        painter.setBrush(QBrush(r2_color))
        painter.drawRect(620, 90, 60, 20)
        
    def draw_start_select(self, painter):
        """Draw Start/Select buttons with current state."""
        # Options and Share buttons
        options_color = QColor(0, 150, 0) if self.button_states.get('options', False) else QColor(80, 80, 80)
        share_color = QColor(0, 150, 0) if self.button_states.get('share', False) else QColor(80, 80, 80)
        
        painter.setBrush(QBrush(share_color))
        painter.drawRect(280, 220, 30, 15)
        painter.setBrush(QBrush(options_color))
        painter.drawRect(490, 220, 30, 15)
