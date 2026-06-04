import sys
import time
import numpy as np
import zmq
import winsound
import subprocess
import os
import datetime
import json
import pandas as pd
import matplotlib.pyplot as plt
from msgpack import loads
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon
from collections import deque
from DataProcessing import AreaFilter, ConstrictionMonitor, GazepointReceiver, PupilLabsReceiver
from DriveUploader import create_drive_folder
import HelperClasses
from HelperClasses import SessionLogger, DataPlotter, DataSaver, TTSWorkerThread
from Calibration import CalibrationWidget
from ShuttleGame import GameWidget
from YNWidget import YNWidget
from Training import TrainingWidget
from KeyboardApp import KeyboardApp
from StartupScreen import StartupWidget
from SettingsDialog import SettingsDialog
from DigitalEye import DigitalEyeWidget

# ---------------------------------------------------------
# SUBJECT DATA HANDLER
# ---------------------------------------------------------
def get_subject_folder_name(base_path, subject_name):
    """Scans base_path for folders named subject_name_XX
    Returns the next sequence: subject_name_01, subject_name_02 etc """

    if not os.path.exists(base_path):
        os.makedirs(base_path)

    existing_folders = os.listdir(base_path)

    max_count = 0
    #found_any = False
    for folder in existing_folders:
        if folder.startswith(f"{subject_name}_"):
            try:
                remainder = folder[len(subject_name)+1:] 
                num_str = remainder.split("_")[0]

                if num_str.isdigit():
                    count = int(num_str)
                    if count > max_count:
                        max_count = count
            except ValueError:
                continue

    next_num = max_count + 1
    return f"{subject_name}_{next_num:02d}"

# ---------------------------------------------------------
# PARAMETERS LOADING AND HANDLING
# ---------------------------------------------------------
def load_parameters(filepath="parameters.json"):
    """Loads parameters or creates default ones if missing"""
    default_params = {
        "constriction": {
            "threshold": 0.75,
            "short_constr_dur": 0.5,
            "long_constr_dur": 3.0,
            "gp3_fps": 60,
            "pupilcore_fps": 125
        },
        "yn_widget": {
            "scan_interval_dur": 3.5,
            "cooldown_dur": 2.0,
            "initialization_dur": 3.0
        },
        "gui": {
            "scan_interval_dur": 3.5,
            "initialization_dur": 3.0
        }}
    if not os.path.exists(filepath):
        print(f"{filepath} not found. Creating default parameters.")
        with open(filepath, "w") as f:
            json.dump(default_params, f, indent=4)
        return default_params
    
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}. Using defaults")
        return default_params

# ---------------------------------------------------------
# MAIN MENU WIDGET
# ---------------------------------------------------------
class MainMenuWidget(QtWidgets.QWidget):
    def __init__(self, folder_path, params, device_type="gazepoint"):
        super().__init__()
        self.params = params
        self.device_type = device_type
        active_fps = self.params.get("active_fps", 60) 
        threshold = self.params["constriction"].get("threshold", 0.75)
        self.filter = AreaFilter(fps=active_fps, device_type=self.device_type)
        self.monitor = ConstrictionMonitor(fps=active_fps, thresh=threshold, device_type=self.device_type)
        self.logger = SessionLogger(folder_path, "MainMenu")
        self.saver = DataSaver(folder_path, "MainMenu")
        self.player = QMediaPlayer()
        self.last_spoken_index = -1
        self.system_armed = False

        gui_config = self.params.get("gui", {})
        self.t_scan = gui_config.get("scan_interval_dur", 3.5)
        self.t_init = gui_config.get("initialization_dur", 3.0)

        # MAIN LAYOUT
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- HEADER ---
        header_layout = QtWidgets.QHBoxLayout()
        
        # 1. Spacer to balance the layout
        left_dummy = QtWidgets.QWidget()
        left_dummy.setFixedSize(60, 1) 

        # 2. Centered Title
        self.label = QtWidgets.QLabel("MENÙ PRINCIPALE")
        # Use a dynamic font size calculation later if needed, but 26px is a good safe base
        self.label.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        
        # 3. Settings Button (Top Right)
        self.settings_btn = QtWidgets.QPushButton("⋮")
        self.settings_btn.setFixedSize(60, 50) # Touch friendly size
        self.settings_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                color: #aaaaaa;
                font-size: 45px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { color: white; }
        """)
        
        header_layout.addWidget(left_dummy)
        header_layout.addWidget(self.label)
        header_layout.addWidget(self.settings_btn)
        
        self.main_layout.addLayout(header_layout)

        # Add Digital Twin to Main Menu
        self.digital_eye = DigitalEyeWidget(device_type=self.device_type)
        self.main_layout.addWidget(self.digital_eye, alignment=QtCore.Qt.AlignCenter)

        #Add red fixation dot to Main Menu
        self.fixation_dot = QtWidgets.QLabel()
        self.fixation_dot.setFixedSize(16, 16)
        self.fixation_dot.setStyleSheet("background-color: red; border-radius: 8px;")
        self.main_layout.addWidget(self.fixation_dot, alignment=QtCore.Qt.AlignCenter)

        # --- STATUS LABELS ---
        status_layout = QtWidgets.QHBoxLayout()
        self.live_label = QtWidgets.QLabel("Segnale: In attesa...")
        self.live_label.setStyleSheet("font-size: 16px; color: #888888;")
        
        self.instruction_label = QtWidgets.QLabel("Inizializzazione...")
        self.instruction_label.setStyleSheet("font-size: 18px; color: #FFD700; font-weight: bold;")
        self.instruction_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        
        status_layout.addWidget(self.live_label)
        status_layout.addStretch()
        status_layout.addWidget(self.instruction_label)
        
        self.main_layout.addLayout(status_layout)

        # --- RESPONSIVE BUTTON GRID ---
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(15)

        # Initialize Buttons
        self.training_button = QtWidgets.QPushButton("TRAINING")
        self.yn_button = QtWidgets.QPushButton("SI O NO")
        self.keyboard_button = QtWidgets.QPushButton("TASTIERA")
        self.game_button = QtWidgets.QPushButton("GIOCO")
        #self.calibration_button = QtWidgets.QPushButton("CALIBRAZIONE")

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        for btn in [self.training_button, self.yn_button, self.keyboard_button, self.game_button]:
        #for btn in [self.training_button, self.yn_button, self.keyboard_button, self.game_button, self.calibration_button]:
            btn.setEnabled(False)
            btn.setSizePolicy(size_policy) # Apply the expanding policy
            btn.setMinimumHeight(80)       # Never smaller than 80px (Good for Touch)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #444; 
                    color: #888; 
                    border-radius: 10px; 
                    font-weight: bold;
                }
            """)

        # Row 1
        grid_layout.addWidget(self.training_button, 0, 0)
        grid_layout.addWidget(self.yn_button, 0, 1)

        # Row 2
        grid_layout.addWidget(self.keyboard_button, 1, 0)
        grid_layout.addWidget(self.game_button, 1, 1)

        # Row 3 (Full Width)
        #grid_layout.addWidget(self.calibration_button, 2, 0, 1, 2)

        # Add the grid to the main layout with a stretch factor equal to 1
        # This tells the layout: "Give the buttons as much space as possible"
        self.main_layout.addLayout(grid_layout, 1) 

        # --- SEPARATOR ---
        self.launch_divider = QtWidgets.QFrame()
        self.launch_divider.setFrameShape(QtWidgets.QFrame.HLine)
        self.launch_divider.setStyleSheet("color: #444; margin: 10px 0;")
        self.main_layout.addWidget(self.launch_divider)

        # --- FOOTER ---
        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setSpacing(15)

        self.launch_button = QtWidgets.QPushButton("Avvia dispositivo")
        self.launch_button.setMinimumHeight(60)
        self.launch_button.setStyleSheet("background-color: #333; color: #aaa; border: 1px solid #555;")
        self.launch_button.clicked.connect(self.launch_software)
        
        self.ready_btn = QtWidgets.QPushButton("Dispositivo pronto")
        self.ready_btn.setMinimumHeight(60)
        self.ready_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.ready_btn.clicked.connect(self.arm_system)

        footer_layout.addWidget(self.launch_button)
        footer_layout.addWidget(self.ready_btn)

        self.main_layout.addLayout(footer_layout)
        
        self.setLayout(self.main_layout)

        # Scanning setup
        self.scan_options = [
            self.training_button,
            self.yn_button, 
            self.keyboard_button, 
            self.game_button  
            #self.calibration_button
        ]
        self.current_index = 0
        self.scan_start_time = 0
        self.state = "INITIALIZATION"
        self.state_start_time = time.time()

        # Styles for active/inactive
        self.active_style = """
            background-color: #0078d7; 
            color: white; 
            font-weight: bold;
            border: 3px solid white;
            border-radius: 10px;
        """
        self.inactive_style = """
            background-color: #444; 
            color: #ccc;
            font-weight: bold;
            border-radius: 10px;
        """
        
        # Initial Check
        self.check_pupil_process()

    def end_session(self):
        """Saves the continuous Main Menu CSV to disk"""
        if hasattr(self, 'saver') and self.saver:
            self.saver.save_file()
            if self.logger: self.logger.log("MainMenu CSV aggiornato su disco.")


    def set_device_type(self, new_device):
        """Hot-swap of ui without recreating the widget"""
        self.device_type = new_device
        self.check_pupil_process()
        ready_text = "Dispositivo pronto"
        self.ready_btn.setText(ready_text)

    def arm_system(self):
        """Activates pupil tracking when system is armed"""
        self.system_armed = True
        self.ready_btn.hide()
        self.launch_button.hide()

        self.monitor.reset_monitor()

        self.instruction_label.setText("Sistema attivo")

        #self.calibration_button.setEnabled(True)
        self.yn_button.setEnabled(True)
        self.game_button.setEnabled(True)
        self.training_button.setEnabled(True)
        self.keyboard_button.setEnabled(True)

        if self.logger: self.logger.log("System Armed manually: Glasses ready.")

    def enable_menu(self):
        """ Called when Gazepoint is connected"""
        self.training_button.setEnabled(True)
        self.yn_button.setEnabled(True)
        self.game_button.setEnabled(True)
        #self.calibration_button.setEnabled(True)
        self.keyboard_button.setEnabled(True)
        
        self.training_button.setStyleSheet(self.inactive_style)
        self.yn_button.setStyleSheet(self.inactive_style)
        self.game_button.setStyleSheet(self.inactive_style)
        #self.calibration_button.setStyleSheet(self.inactive_style)
        self.keyboard_button.setStyleSheet(self.inactive_style)

        self.live_label.setText("Segnale: Connesso")

    def check_pupil_process(self):
        """Checks if the acquisition software is running and disables the button if true"""
        self.launch_button.show()
        try:
            output = subprocess.check_output("tasklist", shell = True).decode()
            if "Gazepoint.exe" in output or "pupil_capture.exe" in output:
                self.launch_button.setEnabled(False)
                self.launch_button.setText("Acquisizione attiva")
                self.launch_button.setStyleSheet("background-color: #444; color: white;")
            else:
                self.launch_button.setEnabled(True)
                self.launch_button.setText("Avvia dispositivo")
                self.launch_button.setStyleSheet("background-color: #444; color: white;")
        except:
            pass

    def synthetise_word(self,word):
        """Turns the word into a synthetised temporary .mp3 file to be read out loud by tts tool"""
        if hasattr(self, 'tts_thread') and self.tts_thread.isRunning():
            return
        self.player.setMedia(QMediaContent())
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        import glob
        for old_file in glob.glob(os.path.join(base_dir, "temp_speech_*.wav")):
            try:
                os.remove(old_file)
            except OSError:
                pass 
                
        unique_filename = f"temp_speech_{int(time.time() * 1000)}.wav"
        temp_audio_path = os.path.join(base_dir, unique_filename)
        self.tts_thread = TTSWorkerThread(word, temp_audio_path)
        self.tts_thread.audio_ready_signal.connect(self.play_sound)
        self.tts_thread.start()

    def play_sound(self,file_path):
        """Plays the audio file for the word that's just been written"""
        if os.path.exists(file_path):
            url = QUrl.fromLocalFile(file_path)
            content = QMediaContent(url)
            self.player.setMedia(content)
            self.player.play()
        else:
            print(f"File audio non trovato: {file_path}")

    def update_visual_scanning(self):
        elapsed = time.time() - self.scan_start_time
        if elapsed >= self.t_scan:
            self.scan_start_time = time.time()
            self.current_index = (self.current_index + 1) % len(self.scan_options)

        for i, btn in enumerate(self.scan_options):
            if i == self.current_index:
                btn.setStyleSheet(self.active_style)
                if self.current_index != getattr(self, 'last_spoken_index', -1):
                    word = btn.text()
                    self.synthetise_word(word)
                    self.last_spoken_index = self.current_index
            else:
                btn.setStyleSheet(self.inactive_style)

    def show_timeout_dialog(self):
        """Mette in pausa l'interfaccia e richiede l'intervento dell'utente."""
        
        # QMessageBox ferma automaticamente l'interazione con il resto della finestra
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Errore di Rilevamento")
        msg.setText("Il sistema non riesce a rilevare correttamente la pupilla.\nControlla l'inquadratura e clicca riprova.")
        
        btn_retry = msg.addButton("Riprova", QMessageBox.AcceptRole)
        msg.setStyleSheet("QLabel { color: white; font-size: 16px; } QPushButton { font-size: 16px; padding: 5px; }")
        
        # Execute popup
        msg.exec_()
        
        self.filter.reset()
        self.monitor.reset_monitor()
        self.state_start_time = time.time()
    
    def update_data(self, raw_area, raw_x=0, raw_y=0):
        #This function is called by MainWindow to update live label and digital eye
        if hasattr(self, 'digital_eye'):
            self.digital_eye.update_eye(raw_x, raw_y, raw_area)
        area = self.filter.area_filtering(raw_area)

        if self.filter.timeout_triggered:
            self.show_timeout_dialog()
            return
        
        val =  area if area is not None else 0.0
        self.live_label.setText(f"Area registrata: {val: .2f}") 

        current_thresh = self.monitor.current_sma_thresh
        exit_thresh = self.monitor.exit_thresh

        machine_status = "UNARMED"
        status = 0

        if not self.system_armed:
            self.instruction_label.setText("Premi DISPOSITIVO PRONTO per iniziare")
        else:
            status = self.monitor.constriction_detector(area)
            machine_status = f"ARMED_{self.state}"

            if not getattr(self, 'settings_open', False):
                # State Machine
                if self.state == "INITIALIZATION":
                    self.live_label.setText("Inizializzazione Menu... Guarda lontano")
                    self.monitor.baseline_collection(area)

                    # use inactive style for all
                    for btn in self.scan_options: btn.setStyleSheet(self.inactive_style)

                    if time.time() - self.state_start_time > self.t_init:
                        self.state = "SCANNING"
                        self.scan_start_time = time.time()
                        self.current_index = 0
                        self.live_label.setText("Menu Attivo: Seleziona l'opzione desiderata")

                elif self.state == "SCANNING":
                    self.update_visual_scanning()

                    # Trigger Logic
                    if status == 1:
                        selected_btn = self.scan_options[self.current_index]
                        print(f"Menu: Selezionato {selected_btn.text()}")

                        selected_btn.click()

                        self.state = "COOLDOWN"
                        self.state_start_time = time.time()

                elif self.state == "COOLDOWN":
                    remaining = self.t_init - (time.time() - self.state_start_time)
                    self.live_label.setText("Attendi {remaining: .1f}...")

                    self.monitor.constriction_detector(area)

                    if remaining <= 0:
                        # re-initialization
                        self.monitor.baseline_buffer.clear()
                        self.monitor.long_trigger_handled = False
                        self.monitor.short_trigger_handled = False
                        self.state = "INITIALIZATION"
                        self.state_start_time = time.time()
                        
                        # re-check process status
                        self.check_pupil_process()

        if hasattr(self, 'saver') and self.saver:
            self.saver.add_data(raw_area, val, current_thresh, exit_thresh, status, machine_status)                

    def launch_software(self):
        if self.device_type == "gazepoint":
            path = r"C:\Program Files (x86)\Gazepoint\Gazepoint\bin64\Gazepoint.exe"
        else:
            path = r"C:\Program Files (x86)\Pupil-Labs\Pupil v3.5.1\Pupil Capture v3.5.1\pupil_capture.exe"

        
        if os.path.exists(path):
            try:
                # Popen starts the app without freezing your Python GUI
                subprocess.Popen([path])
                self.launch_button.setText("Avvio in corso...")
                self.launch_button.setEnabled(False)

                self.logger.log(f"Software Started ({self.device_type})")
            except Exception as e:
                self.label.setText(f"Errore nell'avvio: {e}")
                self.logger.log(f"Error starting software: {e}")
        else:
            self.label.setText("Software non trovato. Controlla il percorso.")
            self.logger.log(f"Error: {self.device_type} path not found")

    def resizeEvent(self, event):
        """Scala dinamicamente il testo e aggiorna gli stili del visual scanner"""
        super().resizeEvent(event)
        
        # 1. Calcola la dimensione del font come percentuale dell'altezza della finestra
        window_height = self.height()
        button_font_size = max(14, int(window_height * 0.03))
        
        # 2. Aggiorna i template di stile aggiungendo il nuovo font-size dinamico
        self.active_style = f"""
            background-color: #0078d7; 
            color: white; 
            font-size: {button_font_size}px;
            font-weight: bold;
            border: 3px solid white;
            border-radius: 10px;
        """
        self.inactive_style = f"""
            background-color: #444; 
            color: #ccc;
            font-size: {button_font_size}px;
            font-weight: bold;
            border-radius: 10px;
        """
        
        # 3. Riapplica immediatamente gli stili ai bottoni per aggiornarli a schermo
        # Assicurandoci di rispettare quale bottone è attualmente "illuminato" dal visual scanner
        if hasattr(self, 'scan_options'):
            for i, btn in enumerate(self.scan_options):
                if hasattr(self, 'current_index') and i == self.current_index:
                    btn.setStyleSheet(self.active_style)
                else:
                    btn.setStyleSheet(self.inactive_style)

# ---------------------------------------------------------
# MAIN WINDOW WIDGET
# ---------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.params = load_parameters()
        self.setWindowTitle("Pupil-com")
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "Images", "Pupil-com_icon.ico")
            self.setWindowIcon(QIcon(icon_path))
        except:
            error_msg = "Icona non trovata. Controlla che 'Pupil-com_icon.ico' sia nella cartella Images."
            print(error_msg)
        self.resize(800,600)

        """self.shutdown_btn = QtWidgets.QPushButton("X", self)
        self.shutdown_btn.setFixedSize(50,40)
        self.shutdown_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))"""

        #self.shutdown_btn.setStyleSheet(
        """
            QPushButton {
                background-color: #ff4444; 
                color: white; 
                font-weight: bold;
                border: none;
                border-bottom-left-radius: 10px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """#)"""

        #self.shutdown_btn.clicked.connect(self.close)

        # Stack setup
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)

        # Startup Widget and connections
        self.startup_widget = StartupWidget()
        self.stack.addWidget(self.startup_widget) # index 0
        self.startup_widget.login_confirmed.connect(self.setup_subject_session)
        self.startup_widget.skip_confirmed.connect(self.setup_anonymous_session)
        #self.showFullScreen()

    def open_settings_window(self):
        # 1. TURN ON THE BLINDFOLD
        self.menu_widget.settings_open = True
        if hasattr(self.menu_widget, 'monitor'):
            self.menu_widget.monitor.reset_monitor()

        # Pass the currently active device into the dialog
        dialog = SettingsDialog(self, params_file="parameters.json", current_device=self.selected_device)

        # 2. FREEZE AND WAIT FOR USER
        result = dialog.exec_() # Script pauses here until dialog closes

        # 3. TURN OFF THE BLINDFOLD (Always runs, whether they hit Save or Cancel)
        self.menu_widget.settings_open = False

        # 4. PROCESS THE SETTINGS IF THEY HIT SAVE
        if result == QtWidgets.QDialog.Accepted:
            print("Reloading parameters...")
            self.params = load_parameters()
            
            gui_config = self.params.get("gui", {})
            self.menu_widget.t_scan = gui_config.get("scan_interval_dur", 3.5)
            self.menu_widget.t_init = gui_config.get("initialization_dur", 3.0)
            
            # --- EXTRACT MISSING VARIABLES FOR THE MONITOR ---
            constrict_config = self.params.get("constriction", {})
            self.short = constrict_config.get("short_constr_dur", 0.5)
            self.long = constrict_config.get("long_constr_dur", 3.0)

            # --- DEVICE HOT-SWAP LOGIC ---
            new_device = dialog.get_selected_device()
            
            if new_device != self.selected_device:
                if hasattr(self, "main_logger"):
                    self.main_logger.log(f"Switching device from {self.selected_device} to {new_device}")
                
                print(f"Switching device from {self.selected_device} to {new_device}")
                self.selected_device = new_device
                self.menu_widget.set_device_type(self.selected_device)
                
                # 1. Update the Active FPS in memory
                if self.selected_device == "gazepoint":
                    self.params["active_fps"] = self.params["constriction"].get("gp3_fps", 60)
                else:
                    self.params["active_fps"] = self.params["constriction"].get("pupilcore_fps", 125)
                    
                active_fps = self.params["active_fps"]
                threshold = self.params["constriction"].get("threshold", 0.75)
                
                # 2. Overwrite the MainMenu's filters with the new FPS parameters
                self.menu_widget.filter = AreaFilter(fps=active_fps, device_type=self.selected_device)
                self.menu_widget.monitor = ConstrictionMonitor(
                    fps=active_fps, 
                    thresh=threshold, 
                    device_type=self.selected_device, 
                    short_dur=self.short, 
                    long_dur=self.long
                )
                
                # 3. Stop the polling timer so it doesn't try to pull from a dying thread
                if hasattr(self, 'poll_timer'):
                    self.poll_timer.stop()

                # 4. Safely stop and destroy the old receiver thread
                if hasattr(self, 'receiver'):
                    self.receiver.stop() 
                    
                # 5. Instantiate the brand new hardware receiver
                if self.selected_device == "gazepoint":
                    self.receiver = GazepointReceiver()
                else:
                    self.receiver = PupilLabsReceiver()
                    
                # 6. Re-wire the successful connection signal to the UI
                self.receiver.connected_signal.connect(self.menu_widget.enable_menu)
                
                # 7. Reset Main Menu UI back to "Waiting for Connection" state
                self.menu_widget.live_label.setText("Segnale: In attesa...")
                self.menu_widget.check_pupil_process() # Checks if the correct background app is running
                
                for btn in self.menu_widget.scan_options:
                    btn.setEnabled(False)
                    btn.setStyleSheet(self.menu_widget.inactive_style)
                    
                # 8. Start the new thread and resume polling the queue!
                self.receiver.start()
                if hasattr(self, 'poll_timer'):
                    self.poll_timer.start(33) # Resume ~30 FPS UI updates

        # 5. FINAL RESET TO CLEAR GHOST INPUTS
        if hasattr(self.menu_widget, 'monitor'):
            self.menu_widget.monitor.reset_monitor()

            
    def setup_subject_session(self, subject_name, device_type):
        """Called when user enters a name"""
        self.selected_device = device_type
        device_suffix = "GP3" if device_type == "gazepoint" else "PL"

        # --- NEW LOGIC ---
        parent_path = HelperClasses.get_local_results_path()
        # Scan for existing folders inside the Experimental Results folder
        base_folder_name = get_subject_folder_name(parent_path, subject_name)
        
        folder_name = f"{base_folder_name}_{device_suffix}"
        # Set the local path inside the parent folder
        self.session_folder = os.path.join(parent_path, folder_name)
        # -----------------
        if HelperClasses.USE_DRIVE:
            try:
                # Create the sub-folder on Drive inside the 'Experimental Results' folder
                new_drive_id = create_drive_folder(folder_name, parent_id=HelperClasses.MAIN_DRIVE_FOLDER_ID)
                HelperClasses.set_session_drive_folder(new_drive_id)
                print("Drive folder created successfully!")
            except Exception as e:
                print(f"Could not create Drive folder (No internet?). Using main folder. Error: {e}")
                HelperClasses.set_session_drive_folder(HelperClasses.MAIN_DRIVE_FOLDER_ID)

        self.initialize_application()

    def setup_anonymous_session(self, device_type):
        # Create session folder
        self.selected_device = device_type
        device_suffix = "GP3" if device_type == "gazepoint" else "PL"

        # --- NEW LOGIC ---
        parent_path = HelperClasses.get_local_results_path()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        folder_name = f"{now_str}_{device_suffix}"
        self.session_folder = os.path.join(parent_path, folder_name)
        # -----------------
        if HelperClasses.USE_DRIVE:
            try:
                print(f"Creating Drive folder for {folder_name}...")
                new_drive_id = create_drive_folder(folder_name, parent_id=HelperClasses.MAIN_DRIVE_FOLDER_ID)
                HelperClasses.set_session_drive_folder(new_drive_id)
                print("Drive folder created successfully!")
            except Exception as e:
                print(f"Could not create Drive folder (No internet?). Using main folder. Error: {e}")
                HelperClasses.set_session_drive_folder(HelperClasses.MAIN_DRIVE_FOLDER_ID)

        self.initialize_application()

    def initialize_application(self):
        # Folder creation
        if not os.path.exists(self.session_folder):
            os.makedirs(self.session_folder)

        # Global logger
        self.main_logger = SessionLogger(self.session_folder, "System")
        self.main_logger.log(f"Application Started. Folder: {self.session_folder}")
        self.main_logger.log(f"Device Selected: {self.selected_device}")

        # Instantiate screens
        screen_rect = QtWidgets.QApplication.primaryScreen().size()
        width, height = screen_rect.width(), screen_rect.height()

        self.menu_widget = MainMenuWidget(self.session_folder, self.params, self.selected_device)
        #self.calibration_widget = CalibrationWidget()
        self.yn_widget = YNWidget()
        self.training_widget = TrainingWidget(device_type = self.selected_device)
        self.game_widget = GameWidget(width, height, self.session_folder)
        self.keyboard_widget = KeyboardApp()
        
        # Add them to the stack
        self.stack.addWidget(self.menu_widget)        # Index 1
        self.stack.addWidget(self.yn_widget)          # Index 2
        self.stack.addWidget(self.game_widget)        # Index 3
        self.stack.addWidget(self.training_widget)     # Index 4
        self.stack.addWidget(self.keyboard_widget)    # Index 5
        #self.stack.addWidget(self.calibration_widget) # Index 6

        # Navigation wiring
        # Main menu wirings
        self.menu_widget.settings_btn.clicked.connect(self.open_settings_window)
        #self.menu_widget.calibration_button.clicked.connect(self.open_calibration_widget)
        self.menu_widget.yn_button.clicked.connect(self.open_yn_widget)
        self.menu_widget.game_button.clicked.connect(self.open_game_widget)
        self.menu_widget.training_button.clicked.connect(self.open_training_widget)
        self.menu_widget.keyboard_button.clicked.connect(self.open_keyboard_widget)
        
        # Back buttons wirings
        #self.calibration_widget.back_btn.clicked.connect(self.go_home)
        self.yn_widget.go_back_signal.connect(self.go_home)
        self.game_widget.go_back_signal.connect(self.go_home)
        self.training_widget.go_back_signal.connect(self.go_home)
        self.keyboard_widget.go_back_signal.connect(self.go_home)
        
        # Receiver setup
        if self.selected_device == "gazepoint":
            self.receiver = GazepointReceiver()
        else:
            self.receiver = PupilLabsReceiver()
            
        self.receiver.connected_signal.connect(self.menu_widget.enable_menu)
        self.receiver.start()

        self.poll_timer = QtCore.QTimer()
        self.poll_timer.timeout.connect(self.poll_receiver)
        self.poll_timer.start(33)

        # Manual check in case of lost connected signal
        if hasattr(self.receiver, 'connected') and self.receiver.connected:
            print("Receiver already connected at application start")
            self.menu_widget.enable_menu()

        # Switch to Main Menu
        self.stack.setCurrentIndex(1)

    def poll_receiver(self):
        """Pulls all pending frames from the active receiver and processes them"""
        if hasattr(self, 'receiver') and self.receiver.connected:
            frames = self.receiver.get_all_frames()
            for area in frames:
                self.dispatch_data(area)

    def open_calibration_widget(self):
        self.menu_widget.end_session()
        self.main_logger.log("Opening Yes/No Widget")
        self.stack.setCurrentIndex(6)
        self.calibration_widget.start_session(self.session_folder, self.params, self.selected_device)
        
    def open_yn_widget(self):
        self.menu_widget.end_session()
        """Helper function to open widget and correctly initialise it"""
        self.main_logger.log("Opening Yes/No Widget")
        self.stack.setCurrentIndex(2)
        self.yn_widget.reset_to_initialization()
        self.yn_widget.start_session(self.session_folder, self.params, self.selected_device)

    def open_game_widget(self):
        self.menu_widget.end_session()
        """Helper function to open widget and correctly initialise it"""
        self.main_logger.log("Opening Shuttle Game Widget") 
        self.stack.setCurrentIndex(3)
        self.game_widget.start_session(self.session_folder, self.params, self.selected_device)

    def open_training_widget(self):
        self.menu_widget.end_session()
        """Helper function to open widget and correctly initialise it"""
        self.main_logger.log("Opening training Widget")
        self.stack.setCurrentIndex(4)
        self.training_widget.start_session(self.session_folder, self.params, self.selected_device)

    def open_keyboard_widget(self):
        self.menu_widget.end_session()
        self.main_logger.log("Opening training Widget")
        self.stack.setCurrentIndex(5)
        self.keyboard_widget.start_session(self.session_folder, self.params, self.selected_device)
    
    def apply_new_threshold(self, new_thresh):
        print(f"MainWindow: Updating Constriction Monitor with threshold {new_thresh: .2f}")

        self.yn_widget.monitor.thresh = new_thresh
        self.menu_widget.monitor.thresh = new_thresh

    def end_session_and_go_home(self):
        current = self.stack.currentWidget()
        if hasattr(current, 'end_session'):
            current.end_session()
        self.go_home

    def go_home(self):
        self.main_logger.log("Returning to Main Menu")

        current_widget = self.stack.currentWidget()
        if hasattr(current_widget, 'end_session'):
            current_widget.end_session()
        if hasattr(current_widget, 'reset_to_initialization'):
            self.stack.currentWidget().reset_to_initialization()

        self.menu_widget.monitor.reset_monitor()
        self.menu_widget.state = "INITIALIZATION"
        self.menu_widget.state_start_time = time.time()

        self.stack.setCurrentIndex(1)

    def dispatch_data(self, data_tuple):
        # Unpack the tuple we just created in the receiver
        if not isinstance(data_tuple, (tuple, list)):
            area = data_tuple
            x, y = 0.0, 0.0
        else:
            area, x, y = data_tuple
        
        current_widget = self.stack.currentWidget() 
        if hasattr(current_widget, 'update_data'):
            # Pass coordinates to TrainingWidget
            if isinstance(current_widget, TrainingWidget) or isinstance(current_widget, MainMenuWidget):
                current_widget.update_data(area, raw_x=x, raw_y=y)
            else:
                # Everything else only gets area
                current_widget.update_data(area)

    def merge_session_csvs(self):
        """Finds all Main Menu CSVs in the session folder and merges them into one timeline"""
        if not hasattr(self, 'session_folder') or not os.path.exists(self.session_folder):
            return

        # 1. Trova tutti i frammenti CSV del Main Menu (ignora maiuscole/minuscole)
        csv_files = [f for f in os.listdir(self.session_folder) 
                     if f.endswith('.csv') and f.lower().startswith('mainmenu_') and not f.lower().startswith('master_')]
        
        if len(csv_files) <= 1:
            # Se ci sono 0 o 1 file del menu, non c'è nulla da unire!
            return

        print("Unione dei file CSV del Menù Principale in corso...")
        df_list = []
        
        # 2. Leggi i file e preparali per l'unione
        for file in csv_files:
            file_path = os.path.join(self.session_folder, file)
            try:
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip() # Pulisce gli header
                
                # Aggiunge una colonna per capire da quale file provengono i dati
                widget_name = file.split('_')[0] if '_' in file else file.replace('.csv', '')
                df['Widget_Source'] = widget_name
                
                df_list.append(df)
            except Exception as e:
                print(f"Errore nella lettura di {file}: {e}")

        # 3. Unisci, ordina e salva
        if df_list:
            master_df = pd.concat(df_list, ignore_index=True)
            
            # Ordina cronologicamente l'intera timeline
            if 'Timestamp' in master_df.columns:
                master_df = master_df.sort_values(by='Timestamp')

            # Salva il file master finale
            master_path = os.path.join(self.session_folder, "Master_MainMenu_Log.csv")
            master_df.to_csv(master_path, index=False)
            
            if hasattr(self, "main_logger") and self.main_logger:
                self.main_logger.log(f"Master Main Menu CSV creato con successo: Master_MainMenu_Log.csv")
            print(f"Master CSV salvato in: {master_path}")

            # 4. PULIZIA: Elimina i frammenti aspettando che il Drive Uploader finisca
            for file in csv_files:
                file_path = os.path.join(self.session_folder, file)
                deleted = False
                attempts = 0
                
                # Prova a cancellare fino a 15 volte (0.2s di pausa = max 3 secondi)
                while not deleted and attempts < 15:
                    try:
                        os.remove(file_path)
                        deleted = True
                        print(f"Frammento {file} eliminato con successo.")
                    except PermissionError: # Cattura l'errore WinError 32 (File in uso)
                        time.sleep(0.2)
                        attempts += 1
                        
                if not deleted:
                    print(f"Impossibile eliminare {file}: il Drive Uploader ci sta mettendo troppo tempo.")
    
    def closeEvent(self, event):
        if hasattr(self, 'menu_widget') and hasattr(self.menu_widget, 'end_session'):
            self.menu_widget.end_session()
        
        time.sleep(0.2)
        self.merge_session_csvs()
        
        if hasattr(self, 'receiver'):
            self.receiver.stop()

        try:
            output = subprocess.check_output("tasklist", shell=True).decode()
            if "Gazepoint.exe" in output:
                print("Shutting down Gazepoint...")
                time.sleep(2) 
                subprocess.call("Taskkill /IM Gazepoint.exe", shell=True)
            elif "pupil_capture.exe" in output: 
                print("Shutting down Pupil Capture...")
                subprocess.call("Taskkill /IM pupil_capture.exe", shell=True)
                time.sleep(2) 

                if hasattr(self, "main_logger"):
                    self.main_logger.log("Gazepoint closed automatically.")
        except Exception as e:
            print(f"Error closing Gazepoint: {e}")
            
        event.accept()

# ---------------------------------------------------------
# APPLICATION BUILDER
# ---------------------------------------------------------
if __name__ == "__main__":
    # Ensure crisp rendering on TVs/High-DPI screens
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)

    UI_theme = """
            QWidget {
                background-color: #2b2b2b;  /* Dark grey background */
                color: #ffffff;             /* White text */
                font-family: 'Segoe UI', Arial;
            }
            QLabel {
                font-size: 30px;
                font-weight: bold;
                qproperty-alignment: 'AlignCenter';
            }
            QPushButton {
                background-color: #0078d7;  /* Professional blue */
                border-radius: 8px;
                border: 2px solid #005a9e;
                color: white;
                padding: 10px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #1086e8;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }"""
    app.setStyleSheet(UI_theme)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())