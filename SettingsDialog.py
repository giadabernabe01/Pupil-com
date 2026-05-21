import json
import os
import copy
from PyQt5 import QtWidgets, QtCore, QtGui

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, params_file="parameters.json", current_device="gazepoint"):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni globali")
        self.resize(500,400)
        self.params_file = params_file
        self.current_params = self.load_params()
        self.current_device = current_device # Store the current device

        # Italian translations
        self.translations = {
            "constriction": "Costrizione Pupillare",
            "gui": "Interfaccia",
            "yn_widget":"Sì o No",
            "keyboard_widget": "Tastiera",
            "testing_widget": "Testing",
            "active_fps": "FPS Attivi",
            "short_constr_dur": "Durata Costrizione Breve",
            "long_constr_dur": "Durata Costrizione Lunga",
            "threshold": "Soglia",
            "initialization_dur": "Tempo Inizializzazione",
            "scan_interval_dur": "Intervallo Scansione",
            "cooldown_dur": "Tempo Cooldown",
            "max_loops": "Cicli Massimi",
            "extra_trigger_dur": "Durata Costrizione Extra-Lunga",
            "short_tasl_dur": "Durata Richiesta Breve",
            "long_task_dur": "Durata Richiesta Lunga",
            "far_interval_dur": "Durata Richiesta Lontano",
            "game_widget": "Gioco",
            "shuttle_speed": "Velocità astronave",
            "planet_speed_base": "Velocità base pianeta",
            "lives": "Numero vite",
            "training_widget": "Training",
            "calibration_widget": "Calibrazione",
            "task_dur": "Durata richiesta"
        }

        main_layout = QtWidgets.QVBoxLayout()

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Dictionary to store all input widgets
        # Key = (section, key), Value = QDoubleSpinBox
        self.inputs = {}

        # Dynamic tab generation
        self.general_tab = QtWidgets.QWidget()
        self.general_layout = QtWidgets.QVBoxLayout()
        self.general_tab.setLayout(self.general_layout)
        self.tabs.addTab(self.general_tab, "Impostazioni generali")

        # 2. ADDED DEVICE SWITCHER UI to the top of General tab
        dev_group = QtWidgets.QGroupBox("Dispositivo Attivo")
        dev_layout = QtWidgets.QVBoxLayout()
        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.addItem("GP3 (Gazepoint)", "gazepoint")
        self.device_combo.addItem("Occhiale (Pupil Core)", "pupil_core")
        
        # Set dropdown to match current device
        if self.current_device == "pupil_core":
            self.device_combo.setCurrentIndex(1)
        else:
            self.device_combo.setCurrentIndex(0)
            
        dev_layout.addWidget(self.device_combo)
        dev_group.setLayout(dev_layout)
        self.general_layout.addWidget(dev_group)

        # Loop through json and build tabs
        for section, keys in self.current_params.items():
            if section in ["constriction", "gui"]:
                parent_layout = self.general_layout
                group_title = section.upper()
            else:
                new_tab = QtWidgets.QWidget()
                new_layout = QtWidgets.QVBoxLayout()
                new_tab.setLayout(new_layout)
                tab_title = self.translations.get(section, section.replace("_", " ").title())
                self.tabs.addTab(new_tab, tab_title)
                parent_layout = new_layout
                group_title = "Parametri"
            
            #Create a GroupBox for visual grouping
            group_box = QtWidgets.QGroupBox(group_title)
            form_layout = QtWidgets.QFormLayout()

            for key, value in keys.items():
                # clean up the label name
                fallback_text = key.replace("_", " ").title()
                label_text = self.translations.get(key, fallback_text)
                label = QtWidgets.QLabel(label_text)

                if isinstance(value, int) and not isinstance(value, bool):
                    # It's an integer! Create a standard QSpinBox
                    spin_box = QtWidgets.QSpinBox()
                    spin_box.setRange(0, 10000) # Adjust max limit as needed
                    spin_box.setValue(value)
                    
                elif isinstance(value, float):
                    # It's a float! Create a QDoubleSpinBox
                    spin_box = QtWidgets.QDoubleSpinBox()
                    spin_box.setRange(0.0, 10000.0)
                    if key == "threshold":
                        spin_box.setSingleStep(0.05) # Finer control for threshold
                    else:
                        spin_box.setSingleStep(0.1)  # Default for other floats like durations
                    spin_box.setValue(value)
                    
                else:
                    continue
                
                # Store it so it can be retrieved later
                self.inputs[(section, key)] = spin_box
                
                form_layout.addRow(label, spin_box)
            
            group_box.setLayout(form_layout)
            parent_layout.addWidget(group_box)
            
            # Add a stretch to push items to the top
            if section not in ["constriction", "gui"]:
                new_layout.addStretch()

        # Add stretch to General tab too
        self.general_layout.addStretch()

        # SAVE / CANCEL BUTTONS
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.save_and_close)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)
        
        self.setLayout(main_layout)
        self.apply_styles()

    def load_params(self):
        """Safely load JSON, return empty dict if not found"""
        if not os.path.exists(self.params_file):
            return {}
        try:
            with open(self.params_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")
            return {}

    def save_and_close(self):
        """Read inputs and write back to JSON safely"""
        
        # 1. DEEPCOPY prevents the deletion of text/boolean settings!
        new_data = copy.deepcopy(self.current_params)

        for (section, key), widget in self.inputs.items():
            if section not in new_data:
                new_data[section] = {}
            
            # 2. Extract value based on the widget type
            if isinstance(widget, QtWidgets.QCheckBox):
                new_data[section][key] = widget.isChecked()
            elif isinstance(widget, QtWidgets.QLineEdit):
                new_data[section][key] = widget.text()
            else:
                new_data[section][key] = widget.value() # For Spinboxes

        try:
            with open(self.params_file, "w") as f:
                json.dump(new_data, f, indent=4)
            print("Settings saved successfully.")
            self.accept()
        except Exception as e:
            print(f"Error saving JSON: {e}")

    # 3. ADDED this function so main.py can read the choice
    def get_selected_device(self):
        return self.device_combo.currentData()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #aaa; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #0078d7; color: white; font-weight: bold; }
            QGroupBox { color: #0078d7; font-weight: bold; border: 1px solid #555; margin-top: 20px; border-radius: 5px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { color: white; font-size: 14px; }
            QDoubleSpinBox, QSpinBox { background-color: #444; color: white; padding: 5px; border: 1px solid #555; border-radius: 3px; }
            QDoubleSpinBox:focus, QSpinBox:focus { border: 1px solid #0078d7; }
            QComboBox { background-color: #444; color: white; padding: 5px; border: 1px solid #555; border-radius: 3px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #444; color: white; selection-background-color: #0078d7; }
        """)