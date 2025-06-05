class VisualizerManager(QObject):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__()
        # ...existing init...
        self.ps4_controller_viz = PS4ControllerVisualizer(parent)

        # existing connections
        self._setup_keyboard_connections()
        self.mouse_buttons_selector.button_toggled.connect(self.button_toggled)

        # new: forward PS4 selection clicks too
        self.ps4_controller_viz.button_toggled.connect(self.button_toggled)

    # ...existing code unchanged...
