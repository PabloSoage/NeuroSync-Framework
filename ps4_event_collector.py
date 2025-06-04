import sdl2
import sdl2.ext
from PyQt5.QtCore import QObject, pyqtSignal

class PS4EventCollector(QObject):
    """Handles PS4 controller connection and event generation"""
    
    # Define signals for different event types
    button_changed = pyqtSignal(str, bool)
    stick_moved = pyqtSignal(str, float, float)
    trigger_changed = pyqtSignal(str, float)
    controller_connected = pyqtSignal(str, int)
    controller_disconnected = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.controller = None
        self.joystick = None
        self.button_states = {}
        self.stick_positions = {'left': (0, 0), 'right': (0, 0)}
        self.trigger_values = {'left': 0, 'right': 0}
        self.initialize_sdl()
        
    def initialize_sdl(self):
        """Initialize SDL for controller support"""
        sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER | sdl2.SDL_INIT_HAPTIC)
    
    def connect_controller(self):
        """Try to connect to a PS4 controller"""
        num_joysticks = sdl2.SDL_NumJoysticks()
        for i in range(num_joysticks):
            if sdl2.SDL_IsGameController(i):
                self.controller = sdl2.SDL_GameControllerOpen(i)
                # Also open as joystick for raw access
                self.joystick = sdl2.SDL_JoystickOpen(i)
                if self.controller and self.joystick:
                    name = sdl2.SDL_GameControllerName(self.controller).decode()
                    self.controller_connected.emit(name, i)
                    return True
        return False
    
    def update(self):
        """Update controller state and emit events for changes"""
        sdl2.SDL_PumpEvents()
        
        # Try to connect if not connected
        if not self.controller:
            self.connect_controller()
            return
            
        # Check if controller is still connected
        if not sdl2.SDL_GameControllerGetAttached(self.controller):
            self.disconnect()
            return
            
        self.process_button_inputs()
        self.process_stick_inputs()
        self.process_trigger_inputs()
    
    def process_button_inputs(self):
        """Process button inputs and emit events for changes"""
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
        
        for button_name, sdl_button in button_mapping.items():
            current_state = bool(sdl2.SDL_GameControllerGetButton(self.controller, sdl_button))
            previous_state = self.button_states.get(button_name, False)
            
            if current_state != previous_state:
                self.button_changed.emit(button_name, current_state)
                
            self.button_states[button_name] = current_state
        
        # Process touchpad button using multiple detection methods
        self.process_touchpad_button()
        
    def process_touchpad_button(self):
        """Detect touchpad press using various methods"""
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
                        dpad_conflict = any([
                            self.button_states.get('dpad_up', False),
                            self.button_states.get('dpad_down', False),
                            self.button_states.get('dpad_left', False),
                            self.button_states.get('dpad_right', False)
                        ])
                        
                        if not dpad_conflict:
                            touchpad_pressed = True
                            break
        
        # Method 3: Try TOUCHPAD button directly if available
        if not touchpad_pressed:
            try:
                # Some SDL2 versions have this constant
                touchpad_pressed = bool(sdl2.SDL_GameControllerGetButton(self.controller, 15))
            except:
                pass
        
        # Update touchpad state
        previous_touchpad = self.button_states.get('touchpad', False)
        if touchpad_pressed != previous_touchpad:
            self.button_changed.emit('touchpad', touchpad_pressed)
        self.button_states['touchpad'] = touchpad_pressed
    
    def process_stick_inputs(self):
        """Process analog stick inputs and emit events for significant changes"""
        left_x = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_LEFTX) / 32767.0
        left_y = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_LEFTY) / 32767.0
        right_x = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTX) / 32767.0
        right_y = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTY) / 32767.0
        
        prev_left = self.stick_positions['left']
        prev_right = self.stick_positions['right']
        
        self.stick_positions['left'] = (left_x, left_y)
        self.stick_positions['right'] = (right_x, right_y)
        
        # Emit signals for significant stick movements
        if abs(left_x - prev_left[0]) > 0.1 or abs(left_y - prev_left[1]) > 0.1:
            self.stick_moved.emit('left', left_x, left_y)
            
        if abs(right_x - prev_right[0]) > 0.1 or abs(right_y - prev_right[1]) > 0.1:
            self.stick_moved.emit('right', right_x, right_y)
    
    def process_trigger_inputs(self):
        """Process trigger inputs and emit events for significant changes"""
        left_trigger = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT)
        right_trigger = sdl2.SDL_GameControllerGetAxis(self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT)
        
        prev_left_trigger = self.trigger_values['left']
        prev_right_trigger = self.trigger_values['right']
        
        self.trigger_values['left'] = left_trigger
        self.trigger_values['right'] = right_trigger
        
        # Emit signals for significant trigger changes
        if abs(left_trigger - prev_left_trigger) > 1000:
            self.trigger_changed.emit('left', left_trigger / 32767.0)
            
        if abs(right_trigger - prev_right_trigger) > 1000:
            self.trigger_changed.emit('right', right_trigger / 32767.0)
    
    def disconnect(self):
        """Handle controller disconnection"""
        if self.joystick:
            sdl2.SDL_JoystickClose(self.joystick)
            self.joystick = None
        if self.controller:
            sdl2.SDL_GameControllerClose(self.controller)
            self.controller = None
        self.controller_disconnected.emit()
    
    def cleanup(self):
        """Clean up SDL resources"""
        self.disconnect()
        sdl2.SDL_Quit()
    
    def get_button_states(self):
        """Return current button states"""
        return self.button_states.copy()
    
    def get_stick_positions(self):
        """Return current stick positions"""
        return self.stick_positions.copy()
    
    def get_trigger_values(self):
        """Return current trigger values"""
        return self.trigger_values.copy()
