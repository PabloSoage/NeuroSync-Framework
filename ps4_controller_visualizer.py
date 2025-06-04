import sys
import json
import time
import struct
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sdl2
import sdl2.ext

# Try to import hidapi for direct PS4 controller access
try:
    import hid
    HID_AVAILABLE = True
except ImportError:
    HID_AVAILABLE = False
    print("Warning: hidapi not available. Install with: pip install hidapi")
    print("Accelerometer, gyroscope, and touchpad will have limited functionality.")

class PS4ControllerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(800, 600)
        self.button_states = {}
        self.stick_positions = {'left': (0, 0), 'right': (0, 0)}
        self.trigger_values = {'left': 0, 'right': 0}
        self.accelerometer = {'x': 0, 'y': 0, 'z': 0}
        self.gyroscope = {'x': 0, 'y': 0, 'z': 0}
        self.touchpad = {'active': False, 'x': 0, 'y': 0, 'touch_id': 0}
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
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
        
        # Draw touchpad with touch position
        self.draw_touchpad(painter, 300, 180)
        
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

    def draw_touchpad(self, painter, x, y):
        touchpad_rect = QRect(x, y, 200, 100)
        
        # Base touchpad color
        base_color = QColor(100, 100, 100) if self.button_states.get('touchpad', False) else QColor(80, 80, 80)
        painter.setBrush(QBrush(base_color))
        painter.drawRoundedRect(touchpad_rect, 5, 5)
        
        # Draw touch point if active
        if self.touchpad['active']:
            touch_x = x + int(self.touchpad['x'] * 200 / 1920)  # PS4 touchpad is 1920x942
            touch_y = y + int(self.touchpad['y'] * 100 / 942)
            
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.drawEllipse(touch_x - 5, touch_y - 5, 10, 10)
            
            # Draw touch coordinates
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(x + 5, y + 15, f"Touch: ({self.touchpad['x']}, {self.touchpad['y']})")
            painter.setPen(QPen(QColor(40, 40, 40), 3))
        
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
        self.hid_device = None
        self.controller_widget = PS4ControllerWidget()
        self.setup_ui()
        self.setup_sdl()
        self.setup_hid()
        self.setup_timer()
        
    def setup_ui(self):
        self.setWindowTitle("PS4 Controller Visualizer")
        self.setGeometry(100, 100, 1400, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        
        # Left side - Controller visualization
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("PS4 Controller"))
        left_panel.addWidget(self.controller_widget)
        
        # Connection status
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        left_panel.addWidget(self.status_label)
        
        # Sensor data
        self.sensor_widget = QWidget()
        self.sensor_layout = QVBoxLayout(self.sensor_widget)
        self.accel_label = QLabel("Accelerometer: X=0, Y=0, Z=0")
        self.gyro_label = QLabel("Gyroscope: X=0, Y=0, Z=0")
        self.touchpad_label = QLabel("Touchpad: Not active")
        self.sensor_layout.addWidget(QLabel("Sensor Data:"))
        self.sensor_layout.addWidget(self.accel_label)
        self.sensor_layout.addWidget(self.gyro_label)
        self.sensor_layout.addWidget(self.touchpad_label)
        left_panel.addWidget(self.sensor_widget)
        
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
        sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)
        
    def setup_hid(self):
        if not HID_AVAILABLE:
            return
            
        # PS4 Controller VID:PID
        self.ps4_vid = 0x054C
        self.ps4_pids = [0x05C4, 0x09CC, 0x0BA0]  # Different PS4 controller variants
        
    def connect_hid_controller(self):
        if not HID_AVAILABLE:
            return False
            
        try:
            for pid in self.ps4_pids:
                devices = hid.enumerate(self.ps4_vid, pid)
                for device_info in devices:
                    if device_info['interface_number'] == 0:  # Use the first interface
                        self.hid_device = hid.device()
                        self.hid_device.open_path(device_info['path'])
                        self.hid_device.set_nonblocking(1)
                        return True
        except Exception as e:
            print(f"HID connection error: {e}")
            
        return False
        
    def parse_ps4_report(self, data):
        # Convert list to bytes if necessary
        if isinstance(data, list):
            data = bytes(data)
        
        if len(data) < 64:
            return
            
        # PS4 controller report structure (simplified)
        # Touchpad data is at different offsets depending on report type
        if data[0] == 0x01:  # Standard input report
            # Touchpad data starts around byte 33
            touchpad_data = data[33:43]
            
            # Parse touchpad
            if len(touchpad_data) >= 9:
                touch_active = (touchpad_data[0] & 0x80) == 0
                if touch_active:
                    touch_id = touchpad_data[0] & 0x7F
                    touch_x = touchpad_data[1] | ((touchpad_data[2] & 0x0F) << 8)
                    touch_y = ((touchpad_data[2] & 0xF0) >> 4) | (touchpad_data[3] << 4)
                    
                    prev_touchpad = self.controller_widget.touchpad.copy()
                    self.controller_widget.touchpad = {
                        'active': True,
                        'x': touch_x,
                        'y': touch_y,
                        'touch_id': touch_id
                    }
                    
                    if not prev_touchpad['active'] or prev_touchpad['x'] != touch_x or prev_touchpad['y'] != touch_y:
                        self.log_event("touchpad", {
                            "active": True,
                            "x": touch_x,
                            "y": touch_y,
                            "touch_id": touch_id
                        })
                else:
                    if self.controller_widget.touchpad['active']:
                        self.controller_widget.touchpad['active'] = False
                        self.log_event("touchpad", {"active": False})
            
            # Parse accelerometer and gyroscope (bytes 13-24)
            if len(data) >= 25:
                # Accelerometer (3 x 16-bit signed)
                accel_x = struct.unpack('<h', data[13:15])[0]
                accel_y = struct.unpack('<h', data[15:17])[0] 
                accel_z = struct.unpack('<h', data[17:19])[0]
                
                # Gyroscope (3 x 16-bit signed)
                gyro_x = struct.unpack('<h', data[19:21])[0]
                gyro_y = struct.unpack('<h', data[21:23])[0]
                gyro_z = struct.unpack('<h', data[23:25])[0]
                
                prev_accel = self.controller_widget.accelerometer.copy()
                prev_gyro = self.controller_widget.gyroscope.copy()
                
                # Convert to g-force (approximate)
                self.controller_widget.accelerometer = {
                    'x': accel_x / 8192.0,
                    'y': accel_y / 8192.0,
                    'z': accel_z / 8192.0
                }
                
                # Convert to degrees/second (approximate)
                self.controller_widget.gyroscope = {
                    'x': gyro_x / 1024.0,
                    'y': gyro_y / 1024.0,
                    'z': gyro_z / 1024.0
                }
                
                # Log significant changes
                accel_threshold = 0.1
                gyro_threshold = 5.0
                
                if (abs(self.controller_widget.accelerometer['x'] - prev_accel['x']) > accel_threshold or
                    abs(self.controller_widget.accelerometer['y'] - prev_accel['y']) > accel_threshold or
                    abs(self.controller_widget.accelerometer['z'] - prev_accel['z']) > accel_threshold):
                    self.log_event("accelerometer", self.controller_widget.accelerometer)
                    
                if (abs(self.controller_widget.gyroscope['x'] - prev_gyro['x']) > gyro_threshold or
                    abs(self.controller_widget.gyroscope['y'] - prev_gyro['y']) > gyro_threshold or
                    abs(self.controller_widget.gyroscope['z'] - prev_gyro['z']) > gyro_threshold):
                    self.log_event("gyroscope", self.controller_widget.gyroscope)

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_controller)
        self.timer.start(16)  # ~60 FPS
        
    def connect_controller(self):
        num_joysticks = sdl2.SDL_NumJoysticks()
        for i in range(num_joysticks):
            if sdl2.SDL_IsGameController(i):
                self.controller = sdl2.SDL_GameControllerOpen(i)
                if self.controller:
                    name = sdl2.SDL_GameControllerName(self.controller).decode()
                    self.status_label.setText(f"Status: Connected - {name}")
                    self.status_label.setStyleSheet("color: green; font-weight: bold;")
                    self.log_event("controller_connected", {"name": name, "index": i})
                    
                    # Try to connect HID for advanced features
                    if self.connect_hid_controller():
                        self.status_label.setText(f"Status: Connected - {name} (HID Enhanced)")
                    
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
            self.controller = None
            if self.hid_device:
                self.hid_device.close()
                self.hid_device = None
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.log_event("controller_disconnected", {})
            return
            
        # Read HID data for sensors and touchpad
        if self.hid_device:
            try:
                data = self.hid_device.read(64)
                if data and len(data) > 0:  # Check if data is not empty
                    self.parse_ps4_report(data)
            except Exception as e:
                # Reduce error spam by only logging unique errors
                if not hasattr(self, '_last_hid_error') or self._last_hid_error != str(e):
                    print(f"HID read error: {e}")
                    self._last_hid_error = str(e)

        # Read button states
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
            'touchpad': sdl2.SDL_CONTROLLER_BUTTON_MISC1
        }
        
        changed_buttons = {}
        for button_name, sdl_button in button_mapping.items():
            current_state = bool(sdl2.SDL_GameControllerGetButton(self.controller, sdl_button))
            previous_state = self.controller_widget.button_states.get(button_name, False)
            
            if current_state != previous_state:
                changed_buttons[button_name] = current_state
                
            self.controller_widget.button_states[button_name] = current_state
            
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
        
        # Update sensor display
        accel = self.controller_widget.accelerometer
        gyro = self.controller_widget.gyroscope
        touchpad = self.controller_widget.touchpad
        
        self.accel_label.setText(f"Accelerometer: X={accel['x']:.3f}g, Y={accel['y']:.3f}g, Z={accel['z']:.3f}g")
        self.gyro_label.setText(f"Gyroscope: X={gyro['x']:.1f}°/s, Y={gyro['y']:.1f}°/s, Z={gyro['z']:.1f}°/s")
        
        if touchpad['active']:
            self.touchpad_label.setText(f"Touchpad: Active - X={touchpad['x']}, Y={touchpad['y']}")
        else:
            self.touchpad_label.setText("Touchpad: Not active")
        
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
        if self.controller:
            sdl2.SDL_GameControllerClose(self.controller)
        if self.hid_device:
            self.hid_device.close()
        sdl2.SDL_Quit()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PS4ControllerApp()
    window.show()
    sys.exit(app.exec_())
