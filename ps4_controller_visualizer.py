import sys
import json
import time
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sdl2
import sdl2.ext
import os
from pathlib import Path

class PS4ControllerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(800, 600)
        self.button_states = {}
        self.stick_positions = {'left': (0, 0), 'right': (0, 0)}
        self.trigger_values = {'left': 0, 'right': 0}
        self.image_mode = True
        self.images_loaded = False
        self.images = {}
        self.base_image = None
        self.edit_mode = False
        self.selected_item = None
        self.drag_start = None
        self.positions_file = Path(__file__).parent / 'ps4' / 'controller_positions.json'
        
        # Define element groups for grouped movement
        self.element_groups = {
            'action_buttons': ['X_pressed', 'Circle_pressed', 'Square_pressed', 'Triangle_pressed'],
            'dpad': ['dpad_up', 'dpad_down', 'dpad_left', 'dpad_right'],
            'sticks': ['left_stick_pressed', 'right_stick_pressed', 'stick_released'],
            'triggers': ['left_trigger_pressed', 'right_trigger_pressed'],
            'center_buttons': ['share_pressed', 'options_pressed', 'ps_pressed', 'touchpad_pressed'],
            'bumpers': ['bumper_pressed']
        }
        
        self.load_images()
        
    def load_positions_from_json(self):
        """Load positions from JSON file"""
        try:
            if self.positions_file.exists():
                with open(self.positions_file, 'r') as f:
                    positions = json.load(f)
                    print(f"Loaded positions from {self.positions_file}")
                    return positions
            else:
                print(f"Positions file not found: {self.positions_file}, using defaults")
                return self.get_default_positions()
        except Exception as e:
            print(f"Error loading positions: {e}")
            return self.get_default_positions()
    
    def get_default_positions(self):
        """Return default hardcoded positions"""
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
    
    def save_positions_to_json(self):
        """Save current positions to JSON file"""
        try:
            positions = {}
            for key, data in self.images.items():
                if data['pos'] is not None:
                    positions[key] = {
                        'file': f"{key}.png",
                        'pos': list(data['pos'])  # Convert tuples to lists for JSON serialization
                    }
            
            with open(self.positions_file, 'w') as f:
                json.dump(positions, f, indent=2)
            print(f"Positions saved to {self.positions_file}")
            return True
        except Exception as e:
            print(f"Error saving positions: {e}")
            return False

    def load_images(self):
        """Load PS4 controller images"""
        try:
            assets_path = Path(__file__).parent / 'ps4' / 'pngs'
            
            if not assets_path.exists():
                print(f"Assets path not found: {assets_path}")
                return
                
            # Load base controller image
            base_path = assets_path / 'controller_base.png'
            if base_path.exists():
                self.base_image = QPixmap(str(base_path))
                self.setFixedSize(self.base_image.width() + 20, self.base_image.height() + 20)
            
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
                    print(f"Image not found: {img_path}")
            
            if self.base_image and len(self.images) > 0:
                self.images_loaded = True
                print(f"Loaded {len(self.images)} controller images")
            else:
                print("Failed to load sufficient images, using fallback mode")
                
        except Exception as e:
            print(f"Error loading images: {e}")
            self.images_loaded = False
    
    def toggle_edit_mode(self):
        """Toggle edit mode on/off"""
        self.edit_mode = not self.edit_mode
        self.selected_item = None
        self.update()
        return self.edit_mode
    
    def find_group_for_item(self, item_key):
        """Find which group an item belongs to"""
        for group_name, items in self.element_groups.items():
            if item_key in items:
                return group_name
        return None
    
    def move_group(self, group_name, delta_x, delta_y):
        """Move all items in a group by the same delta"""
        if group_name in self.element_groups:
            for item_key in self.element_groups[group_name]:
                if item_key in self.images and self.images[item_key]['pos'] is not None:
                    old_pos = self.images[item_key]['pos']
                    new_pos = (old_pos[0] + delta_x, old_pos[1] + delta_y)
                    self.images[item_key]['pos'] = new_pos

    def mousePressEvent(self, event):
        if not self.edit_mode or not self.images_loaded:
            return
            
        if event.button() == Qt.LeftButton:
            # Find which overlay was clicked
            pos = event.pos()
            for key, data in self.images.items():
                if data['pos'] is not None:
                    pixmap_rect = QRect(data['pos'][0] + 5, data['pos'][1] + 5, 
                                    data['pixmap'].width(), data['pixmap'].height())
                    if pixmap_rect.contains(pos):
                        self.selected_item = key
                        self.drag_start = pos
                        break
    
    def mouseMoveEvent(self, event):
        if not self.edit_mode or not self.selected_item or not self.drag_start:
            return
            
        current_pos = event.pos()
        delta_x = current_pos.x() - self.drag_start.x()
        delta_y = current_pos.y() - self.drag_start.y()
        
        # Check if we should move the group or individual item
        group = self.find_group_for_item(self.selected_item)
        
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
        self.update()
    
    def mouseReleaseEvent(self, event):
        if not self.edit_mode:
            return
            
        if event.button() == Qt.LeftButton:
            self.selected_item = None
            self.drag_start = None

    def toggle_image_mode(self):
        """Toggle between image mode and drawn mode"""
        if self.images_loaded:
            self.image_mode = not self.image_mode
            self.update()
            return self.image_mode
        return False
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.image_mode and self.images_loaded:
            self.paint_image_mode(painter)
        else:
            self.paint_drawn_mode(painter)
            
        # Draw edit mode overlays
        if self.edit_mode and self.images_loaded:
            self.paint_edit_overlays(painter)
    
    def paint_edit_overlays(self, painter):
        """Draw edit mode visual aids"""
        # Draw bounding boxes around all overlays
        for key, data in self.images.items():
            if data['pos'] is not None:
                rect = QRect(data['pos'][0] + 5, data['pos'][1] + 5,
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
                    rects.append(QRect(pos[0] + 5, pos[1] + 5, pixmap.width(), pixmap.height()))
            
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

    def paint_image_mode(self, painter):
        """Paint using loaded images"""
        # Draw base controller
        if self.base_image:
            painter.drawPixmap(5, 5, self.base_image)
        
        # In edit mode, show all overlays
        if self.edit_mode:
            for key, data in self.images.items():
                if data['pos'] is not None and key != 'stick_released':
                    painter.drawPixmap(data['pos'][0] + 5, data['pos'][1] + 5, data['pixmap'])
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
                    # No offset correction needed when using JSON positions
                    painter.drawPixmap(img_data['pos'][0] + 5, img_data['pos'][1] + 5, img_data['pixmap'])
            
            # Draw R1 (flipped bumper)
            if self.button_states.get('r1', False) and 'bumper_pressed' in self.images:
                bumper = self.images['bumper_pressed']['pixmap']
                flipped_bumper = bumper.transformed(QTransform().scale(-1, 1))
                # Position R1 at a fixed offset from L1
                l1_pos = self.images['bumper_pressed']['pos']
                r1_pos = (l1_pos[0] + 489, l1_pos[1]) # Offset for R1 position
                painter.drawPixmap(r1_pos[0] + 5, r1_pos[1] + 5, flipped_bumper)
            
            # Draw analog sticks with movement
            self.draw_image_analog_sticks(painter)
            
            # Draw triggers with pressure
            self.draw_image_triggers(painter)
    
    def draw_image_analog_sticks(self, painter):
        """Draw analog sticks with images and movement"""
        stick_released_img = self.images.get('stick_released', {}).get('pixmap')
        left_pressed_img = self.images.get('left_stick_pressed', {}).get('pixmap')
        right_pressed_img = self.images.get('right_stick_pressed', {}).get('pixmap')
        
        # Left stick position from JSON
        left_base_pos = self.images['left_stick_pressed']['pos']
        left_x, left_y = self.stick_positions['left']
        left_offset_x = int(left_x * 15)
        left_offset_y = int(left_y * 15)
        
        if self.button_states.get('left_stick', False) and left_pressed_img:
            painter.drawPixmap(left_base_pos[0] + 5 + left_offset_x, 
                             left_base_pos[1] + 5 + left_offset_y, left_pressed_img)
        elif stick_released_img:
            painter.drawPixmap(left_base_pos[0] + 5 + left_offset_x, 
                             left_base_pos[1] + 5 + left_offset_y, stick_released_img)
        
        # Right stick position from JSON
        right_base_pos = self.images['right_stick_pressed']['pos']
        right_x, right_y = self.stick_positions['right']
        right_offset_x = int(right_x * 15)
        right_offset_y = int(right_y * 15)
        
        if self.button_states.get('right_stick', False) and right_pressed_img:
            painter.drawPixmap(right_base_pos[0] + 5 + right_offset_x,
                             right_base_pos[1] + 5 + right_offset_y, right_pressed_img)
        elif stick_released_img:
            painter.drawPixmap(right_base_pos[0] + 5 + right_offset_x,
                             right_base_pos[1] + 5 + right_offset_y, stick_released_img)
    
    def draw_image_triggers(self, painter):
        """Draw triggers with pressure-based transparency"""
        # Left trigger (L2) with position from JSON
        left_trigger_value = self.trigger_values['left'] / 32767.0
        if left_trigger_value > 0.01 and 'left_trigger_pressed' in self.images:
            trigger_img = self.images['left_trigger_pressed']['pixmap'].copy()
            pos = self.images['left_trigger_pressed']['pos']
            
            # Create transparent version
            temp_pixmap = QPixmap(trigger_img.size())
            temp_pixmap.fill(Qt.transparent)
            temp_painter = QPainter(temp_pixmap)
            temp_painter.setOpacity(left_trigger_value)
            temp_painter.drawPixmap(0, 0, trigger_img)
            temp_painter.end()
            
            painter.drawPixmap(pos[0] + 5, pos[1] + 5, temp_pixmap)
        
        # Right trigger (R2) with position from JSON
        right_trigger_value = self.trigger_values['right'] / 32767.0
        if right_trigger_value > 0.01 and 'right_trigger_pressed' in self.images:
            trigger_img = self.images['right_trigger_pressed']['pixmap'].copy()
            pos = self.images['right_trigger_pressed']['pos']
            
            # Create transparent version
            temp_pixmap = QPixmap(trigger_img.size())
            temp_pixmap.fill(Qt.transparent)
            temp_painter = QPainter(temp_pixmap)
            temp_painter.setOpacity(right_trigger_value)
            temp_painter.drawPixmap(0, 0, trigger_img)
            temp_painter.end()
            
            painter.drawPixmap(pos[0] + 5, pos[1] + 5, temp_pixmap)
    
    def paint_drawn_mode(self, painter):
        """Paint using drawn shapes (original method)"""
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
        
    def draw_dpad(self, painter, x, y):
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
        # L1, R1
        l1_color = QColor(0, 150, 0) if self.button_states.get('l1', False) else QColor(80, 80, 80)
        r1_color = QColor(0, 150, 0) if self.button_states.get('r1', False) else QColor(80, 80, 80)
        
        painter.setBrush(QBrush(l1_color))
        painter.drawRect(100, 120, 80, 20)
        painter.setBrush(QBrush(r1_color))
        painter.drawRect(620, 120, 80, 20)
        
    def draw_triggers(self, painter):
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
        # Options and Share buttons
        options_color = QColor(0, 150, 0) if self.button_states.get('options', False) else QColor(80, 80, 80)
        share_color = QColor(0, 150, 0) if self.button_states.get('share', False) else QColor(80, 80, 80)
        
        painter.setBrush(QBrush(share_color))
        painter.drawRect(280, 220, 30, 15)
        painter.setBrush(QBrush(options_color))
        painter.drawRect(490, 220, 30, 15)

class PS4ControllerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = None
        self.joystick = None
        self.controller_widget = PS4ControllerWidget()
        self.setup_ui()
        self.setup_sdl()
        self.setup_timer()
        
    def setup_ui(self):
        self.setWindowTitle("PS4 Controller Visualizer")
        self.setGeometry(100, 100, 1400, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        
        # Left side - Controller visualization
        left_panel = QVBoxLayout()
        
        # Control buttons panel
        control_panel = QHBoxLayout()
        
        # Toggle image mode button
        self.toggle_button = QPushButton("Switch to Drawn Mode" if self.controller_widget.image_mode else "Switch to Image Mode")
        self.toggle_button.clicked.connect(self.toggle_display_mode)
        if not self.controller_widget.images_loaded:
            self.toggle_button.setEnabled(False)
            self.toggle_button.setText("Images Not Available")
        control_panel.addWidget(self.toggle_button)
        
        # Edit mode button
        self.edit_button = QPushButton("Enter Edit Mode")
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        if not self.controller_widget.images_loaded:
            self.edit_button.setEnabled(False)
        control_panel.addWidget(self.edit_button)
        
        # Save positions button
        self.save_button = QPushButton("Save Positions")
        self.save_button.clicked.connect(self.save_positions)
        self.save_button.setEnabled(False)
        control_panel.addWidget(self.save_button)
        
        left_panel.addLayout(control_panel)
        
        # Instructions for edit mode
        self.instructions_label = QLabel("")
        self.instructions_label.setStyleSheet("color: blue;")
        left_panel.addWidget(self.instructions_label)
        
        # Controller widget
        left_panel.addWidget(QLabel("PS4 Controller"))
        left_panel.addWidget(self.controller_widget)
        
        # Connection status
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        left_panel.addWidget(self.status_label)
        
        # Mode status
        mode_text = "Image Mode" if self.controller_widget.image_mode else "Drawn Mode"
        if not self.controller_widget.images_loaded:
            mode_text += " (Images not loaded - using fallback)"
        self.mode_label = QLabel(f"Display Mode: {mode_text}")
        left_panel.addWidget(self.mode_label)
        
        # Right side - Log display
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Real-time Logs (JSON)"))
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMinimumWidth(500)
        self.log_display.setStyleSheet("background-color: black; color: green; font-family: monospace;")
        right_panel.addWidget(self.log_display)
        
        # Clear logs button
        clear_button = QPushButton("Clear Logs")
        clear_button.clicked.connect(self.clear_logs)
        right_panel.addWidget(clear_button)
        
        layout.addLayout(left_panel)
        layout.addLayout(right_panel)
        
    def setup_sdl(self):
        # Initialize with more subsystems for better sensor support
        sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER | sdl2.SDL_INIT_HAPTIC)
        
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller)
        self.timer.start(16)  # ~60 FPS
        
    def toggle_display_mode(self):
        """Toggle between image and drawn display modes"""
        new_mode = self.controller_widget.toggle_image_mode()
        mode_text = "Image Mode" if new_mode else "Drawn Mode"
        self.mode_label.setText(f"Display Mode: {mode_text}")
        self.toggle_button.setText("Switch to Drawn Mode" if new_mode else "Switch to Image Mode")
        
        # When switching to drawn mode, exit edit mode first if it's active
        if not new_mode and self.controller_widget.edit_mode:
            self.toggle_edit_mode()
            
        # Show/hide edit buttons based on mode
        self.edit_button.setVisible(new_mode)
        self.save_button.setVisible(new_mode)
        
        self.log_event("display_mode_changed", {"mode": mode_text})
    
    def toggle_edit_mode(self):
        """Toggle edit mode for positioning elements"""
        edit_mode = self.controller_widget.toggle_edit_mode()
        
        if edit_mode:
            self.edit_button.setText("Exit Edit Mode")
            self.save_button.setEnabled(True)
            self.instructions_label.setText(
                "Edit Mode: Drag elements to reposition them.\n"
                "By default, moving one element moves its entire group.\n"
                "Hold SHIFT while dragging to move individual elements."
            )
            self.log_event("edit_mode_enabled", {})
        else:
            self.edit_button.setText("Enter Edit Mode")
            self.save_button.setEnabled(False)
            self.instructions_label.setText("")
            self.log_event("edit_mode_disabled", {})
    
    def save_positions(self):
        """Save current positions to JSON file"""
        if self.controller_widget.save_positions_to_json():
            QMessageBox.information(self, "Success", "Positions saved successfully!")
            self.log_event("positions_saved", {"file": str(self.controller_widget.positions_file)})
        else:
            QMessageBox.warning(self, "Error", "Failed to save positions!")
        
    def connect_controller(self):
        num_joysticks = sdl2.SDL_NumJoysticks()
        for i in range(num_joysticks):
            if sdl2.SDL_IsGameController(i):
                self.controller = sdl2.SDL_GameControllerOpen(i)
                # Also open as joystick for raw access
                self.joystick = sdl2.SDL_JoystickOpen(i)
                if self.controller and self.joystick:
                    name = sdl2.SDL_GameControllerName(self.controller).decode()
                    self.status_label.setText(f"Status: Connected - {name}")
                    self.status_label.setStyleSheet("color: green; font-weight: bold;")
                    self.log_event("controller_connected", {"name": name, "index": i})
                    return True
        return False
        
    def update_controller(self):
        sdl2.SDL_PumpEvents()
        
        # Try to connect if not connected
        if not self.controller:
            self.connect_controller()
            return
            
        # Check if controller is still connected
        if not sdl2.SDL_GameControllerGetAttached(self.controller):
            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None
            self.controller = None
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.log_event("controller_disconnected", {})
            return
            
        # Read button states with improved touchpad detection
        button_mapping = {
            'triangle': sdl2.SDL_CONTROLLER_BUTTON_Y,
            'circle': sdl2.SDL_CONTROLLER_BUTTON_B,
            'cross': sdl2.SDL_CONTROLLER_BUTTON_A,
            'square': sdl2.SDL_CONTROLLER_BUTTON_X,
            'dpad_up': sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,
            'dpad_down': sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,
            'dpad_left': sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,
            'dpad_right': sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
            'l1': sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER,
            'r1': sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,
            'share': sdl2.SDL_CONTROLLER_BUTTON_BACK,
            'options': sdl2.SDL_CONTROLLER_BUTTON_START,
            'left_stick': sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK,
            'right_stick': sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK,
            'ps': sdl2.SDL_CONTROLLER_BUTTON_GUIDE,
        }
        
        changed_buttons = {}
        for button_name, sdl_button in button_mapping.items():
            current_state = bool(sdl2.SDL_GameControllerGetButton(self.controller, sdl_button))
            previous_state = self.controller_widget.button_states.get(button_name, False)
            
            if current_state != previous_state:
                changed_buttons[button_name] = current_state
                
            self.controller_widget.button_states[button_name] = current_state
        
        # Improved touchpad detection - try multiple methods
        touchpad_pressed = False
        
        # Method 1: Try MISC1 button (most common for PS4 touchpad)
        touchpad_pressed = bool(sdl2.SDL_GameControllerGetButton(self.controller, sdl2.SDL_CONTROLLER_BUTTON_MISC1))
        
        # Method 2: Try raw joystick button access for various common touchpad button indices
        if not touchpad_pressed and self.joystick:
            num_buttons = sdl2.SDL_JoystickNumButtons(self.joystick)
            # Try multiple button indices that could be the touchpad
            for button_idx in [13, 14, 15, 16, 17, 18]:
                if button_idx < num_buttons:
                    if sdl2.SDL_JoystickGetButton(self.joystick, button_idx):
                        # Double-check this isn't a D-pad false positive
                        # If any D-pad button is also pressed, ignore this detection
                        dpad_conflict = any([
                            self.controller_widget.button_states.get('dpad_up', False),
                            self.controller_widget.button_states.get('dpad_down', False),
                            self.controller_widget.button_states.get('dpad_left', False),
                            self.controller_widget.button_states.get('dpad_right', False)
                        ])
                        
                        if not dpad_conflict:
                            touchpad_pressed = True
                            break
        
        # Method 3: Try TOUCHPAD button directly if available
        if not touchpad_pressed:
            try:
                # Some SDL2 versions have this constant
                touchpad_pressed = bool(sdl2.SDL_GameControllerGetButton(self.controller, 15))  # Common touchpad button ID
            except:
                pass
        
        # Update touchpad state
        previous_touchpad = self.controller_widget.button_states.get('touchpad', False)
        if touchpad_pressed != previous_touchpad:
            changed_buttons['touchpad'] = touchpad_pressed
        self.controller_widget.button_states['touchpad'] = touchpad_pressed
            
        # Read analog sticks
        left_x = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_LEFTX) / 32767.0
        left_y = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_LEFTY) / 32767.0
        right_x = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTX) / 32767.0
        right_y = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTY) / 32767.0
        
        prev_left = self.controller_widget.stick_positions['left']
        prev_right = self.controller_widget.stick_positions['right']
        
        self.controller_widget.stick_positions['left'] = (left_x, left_y)
        self.controller_widget.stick_positions['right'] = (right_x, right_y)
        
        # Read triggers
        left_trigger = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT)
        right_trigger = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT)
        
        prev_left_trigger = self.controller_widget.trigger_values['left']
        prev_right_trigger = self.controller_widget.trigger_values['right']
        
        self.controller_widget.trigger_values['left'] = left_trigger
        self.controller_widget.trigger_values['right'] = right_trigger
        
        # Log changes
        if changed_buttons:
            self.log_event("button_change", changed_buttons)
            
        if abs(left_x - prev_left[0]) > 0.1 or abs(left_y - prev_left[1]) > 0.1:
            self.log_event("left_stick", {"x": left_x, "y": left_y})
            
        if abs(right_x - prev_right[0]) > 0.1 or abs(right_y - prev_right[1]) > 0.1:
            self.log_event("right_stick", {"x": right_x, "y": right_y})
            
        if abs(left_trigger - prev_left_trigger) > 1000:
            self.log_event("left_trigger", {"value": left_trigger / 32767.0})
            
        if abs(right_trigger - prev_right_trigger) > 1000:
            self.log_event("right_trigger", {"value": right_trigger / 32767.0})
        
        self.controller_widget.update()
        
    def log_event(self, event_type, data):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data
        }
        
        json_str = json.dumps(log_entry, indent=2)
        self.log_display.append(json_str)
        self.log_display.append("-" * 50)
        
        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def clear_logs(self):
        self.log_display.clear()
        
    def closeEvent(self, event):
        if self.joystick:
            sdl2.SDL_JoystickClose(self.joystick)
        if self.controller:
            sdl2.SDL_GameControllerClose(self.controller)
        sdl2.SDL_Quit()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PS4ControllerApp()
    window.show()
    sys.exit(app.exec_())
