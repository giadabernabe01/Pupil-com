from PyQt5 import QtWidgets, QtCore, QtGui

class StartupWidget(QtWidgets.QWidget):
    # UPDATE: Signals now send the device string as well!
    login_confirmed = QtCore.pyqtSignal(str, str) # (subject_name, device_type)
    skip_confirmed = QtCore.pyqtSignal(str)       # (device_type)

    def __init__(self):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignCenter)
        
        self.selected_device = None # Tracks the user's choice

        # --- TITLE ---
        title = QtWidgets.QLabel("BENVENUTO")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        self.layout.addWidget(title)

        # --- DEVICE SELECTION ---
        dev_label = QtWidgets.QLabel("Quale dispositivo stai utilizzando?")
        dev_label.setStyleSheet("font-size: 18px; color: white;")
        self.layout.addWidget(dev_label, alignment=QtCore.Qt.AlignCenter)

        self.dev_layout = QtWidgets.QHBoxLayout()
        self.dev_layout.setSpacing(15)
        
        # Device Buttons
        self.btn_occhiale = QtWidgets.QPushButton("Occhiale (Pupil Core)")
        self.btn_occhiale.setCheckable(True)
        self.btn_occhiale.setFixedSize(200, 60)
        
        self.btn_gp3 = QtWidgets.QPushButton("GP3 (Gazepoint)")
        self.btn_gp3.setCheckable(True)
        self.btn_gp3.setFixedSize(200, 60)
        
        # Styles for the checkable buttons to make the selection obvious
        dev_btn_style = """
            QPushButton {
                background-color: #444; color: #aaa; border: 2px solid #555;
            }
            QPushButton:checked {
                background-color: #28a745; color: white; border: 2px solid white; font-weight: bold;
            }
        """
        self.btn_occhiale.setStyleSheet(dev_btn_style)
        self.btn_gp3.setStyleSheet(dev_btn_style)
        
        # Group them so only one can be checked at a time
        self.dev_group = QtWidgets.QButtonGroup()
        self.dev_group.addButton(self.btn_occhiale)
        self.dev_group.addButton(self.btn_gp3)
        self.dev_group.setExclusive(True)
        
        # Connect clicks to logic
        self.btn_occhiale.clicked.connect(lambda: self.set_device("pupil_core"))
        self.btn_gp3.clicked.connect(lambda: self.set_device("gazepoint"))
        
        self.dev_layout.addWidget(self.btn_occhiale)
        self.dev_layout.addWidget(self.btn_gp3)
        
        self.layout.addLayout(self.dev_layout)
        
        # Hidden Error Label
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: #ff4444; font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.error_label, alignment=QtCore.Qt.AlignCenter)

        self.layout.addSpacing(20)

        # --- NAME INPUT ---
        instr_1 = QtWidgets.QLabel("Inserisci il nome del soggetto:")
        self.layout.addWidget(instr_1, alignment=QtCore.Qt.AlignCenter)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Nome")
        self.name_input.setStyleSheet("padding: 10px; font-size: 16px; color: white; background-color: #444; border: 1px solid #666")
        self.name_input.setFixedWidth(400)
        self.name_input.setFixedHeight(50)
        self.name_input.returnPressed.connect(self.on_confirm)
        self.layout.addWidget(self.name_input, alignment=QtCore.Qt.AlignCenter)

        self.layout.addSpacing(20)

        # --- ACTION BUTTONS ---
        self.confirm_button = QtWidgets.QPushButton("Conferma e inizia")
        self.confirm_button.setFixedWidth(400)
        self.confirm_button.clicked.connect(self.on_confirm)
        self.layout.addWidget(self.confirm_button, alignment=QtCore.Qt.AlignCenter)

        self.skip_button = QtWidgets.QPushButton("Salta")
        self.skip_button.setFixedWidth(400)
        self.skip_button.setStyleSheet("background-color: #444; color: #888; margin-top: 10px")
        # Route skip through a validation function first
        self.skip_button.clicked.connect(self.on_skip) 
        self.layout.addWidget(self.skip_button, alignment=QtCore.Qt.AlignCenter)

        self.setLayout(self.layout)

    def set_device(self, device_name):
        self.selected_device = device_name
        self.error_label.setText("") # Clear the error if they finally pick one!

    def on_confirm(self):
        # 1. Check if device is selected
        if not self.selected_device:
            self.error_label.setText("Errore: Seleziona un dispositivo per continuare!")
            return
            
        # 2. Check if name is provided
        name = self.name_input.text().strip()
        if name:
            clean_name = name.replace(" ", "")
            self.login_confirmed.emit(clean_name, self.selected_device)
        else:
            self.name_input.setPlaceholderText("Inserisci un nome valido.")
            self.error_label.setText("Errore: Inserisci un nome o premi 'Salta'.")

    def on_skip(self):
        # Check if device is selected before allowing skip
        if not self.selected_device:
            self.error_label.setText("Errore: Seleziona un dispositivo per continuare!")
            return
            
        self.skip_confirmed.emit(self.selected_device)