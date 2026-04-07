import numpy as np
import os
import json
import time
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWidgets import QSizePolicy
from DataProcessing import AreaFilter
from HelperClasses import SessionLogger, DataPlotter, DataSaver

# ---------------------------------------------------------
# CALIBRATION WIDGET
# ---------------------------------------------------------
class CalibrationWidget(QtWidgets.QWidget):
    go_back_signal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        # Audio setup
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.sound_directory = os.path.join(base_path, "Sounds")

        self.player_near = QMediaPlayer()
        near_path = os.path.join(self.sound_directory, "vicino.mp3")
        self.player_far = QMediaPlayer()
        far_path = os.path.join(self.sound_directory, "lontano.mp3")

        # Warm-up audio to avoid cues loss
        if os.path.exists(near_path):
            self.player_near.setMedia(QMediaContent(QUrl.fromLocalFile(near_path)))
            self.player_near.setVolume(0)
            self.player_near.play()

        if os.path.exists(near_path):
            self.player_far.setMedia(QMediaContent(QUrl.fromLocalFile(far_path)))
            self.player_far.setVolume(0)
            self.player_far.play()

        #self.filter = AreaFilter(fps=130, device_type="gazepoint")
        self.logger = None
        self.plotter = None
        self.saver = None

        self.far_data = []
        self.near_data = []
        self.calculated_thresholds = []
        self.collecting = False
        self.min_cut = 1500
        self.state = "IDLE"
        self.current_target = ""
        self.state_start_time = 0.0
        self.count_loops = 0
        
        # Layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.setSpacing(20)

        # Title text
        self.title = QtWidgets.QLabel("CALIBRAZIONE")
        self.title.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.title)

        # Instruction Text
        self.instr = QtWidgets.QLabel("Premi 'Inizia' per calibrare il sistema.")
        self.instr.setStyleSheet("font-size: 20px; color: #ccc;")
        self.instr.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.instr)

        # Live Value
        self.live_val = QtWidgets.QLabel("Area Corrente: 0.00")
        self.live_val.setStyleSheet("font-size: 18px; color: #888;")
        self.live_val.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.live_val)

        # Buttons layout
        self.inner_btn_layout = QtWidgets.QVBoxLayout()
        self.inner_btn_layout.setSpacing(20) # Space between the two buttons
        
        # Start Button (Top)
        self.start_btn = QtWidgets.QPushButton("Inizia")
        self.start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.start_btn.setStyleSheet("background-color: #0078d7; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_sequence)
        self.inner_btn_layout.addWidget(self.start_btn)

        # Back Button (Bottom)
        self.back_btn = QtWidgets.QPushButton("MENÙ PRINCIPALE")
        self.back_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.back_btn.clicked.connect(self.go_back_signal.emit)
        self.inner_btn_layout.addWidget(self.back_btn)

        # 2. Add the vertical "cage" to the main layout using stretches
        # The main layout (self.layout) is already a QVBoxLayout.
        self.layout.addStretch(2)                       # Spring above (takes 25% height)
        self.layout.addLayout(self.inner_btn_layout, 2) # The stacked buttons (take 50% height)
        #self.layout.addStretch(1)                       # Spring below (takes 25% height)

        self.setLayout(self.layout)

    def resizeEvent(self, event):
        base_size = max(16, int(self.height() / 25))
        self.title.setFont(QtGui.QFont('Arial', int(base_size * 3), QtGui.QFont.Bold))
        self.instr.setFont(QtGui.QFont('Arial', int(base_size * 2.5)))
        self.live_val.setFont(QtGui.QFont('Arial', base_size * 3))
        self.back_btn.setFont(QtGui.QFont('Arial', base_size, QtGui.QFont.Bold))
        self.start_btn.setFont(QtGui.QFont('Arial', base_size, QtGui.QFont.Bold))
        super().resizeEvent(event)

    def start_session(self, folder_path, params, device_type):
        self.logger = SessionLogger(folder_path, "Calibration")
        self.plotter = DataPlotter(folder_path, "Calibration")
        self.saver = DataSaver(folder_path, "Calibration")

        # Retrieve parameters
        self.params = params
        self.device_type = device_type
        calibration_config = self.params.get("calibration", {})
        self.t_init = calibration_config.get("initialization_dur", 5.0)
        self.t_task = calibration_config.get("task_dur", 4.0)
        self.max_count_loops = calibration_config.get("loops_num", 2)

        self.reset_ui()
        active_fps = self.params.get("active_fps", 60)

        self.filter = AreaFilter(fps=active_fps, device_type=self.device_type)

        self.logger.log("Calibration Started")

    def end_session(self): # RIVEDI
        self.collecting = False
        self.state = "IDLE"
        self.logger = None
        if self.plotter: self.plotter.save_plot()
        if self.saver: self.saver.save_file()
        self.plotter = None
        self.saver = None

    def reset_ui(self):
        self.state = "IDLE"
        self.count_loops = 0
        self.far_data = []
        self.near_data = []
        self.calculated_thresholds = []
        self.instr.setText("Premi 'Inizia' per avviare la calibrazione")
        self.instr.setStyleSheet("font-size: 20px; color: #ccc;")

        self.start_btn.setText("Inizia")
        self.start_btn.setEnabled(True)
        self.back_btn.setEnabled(True)

        try: self.start_btn.clicked.disconnect()
        except TypeError: pass
        self.start_btn.clicked.connect(self.start_sequence)

    def play_audio_cue(self, player):
        """Helper to play sounds reliably"""
        player.stop()
        player.setPosition(0)
        player.setVolume(100)
        player.play()

    def start_sequence(self):
        """Begins the automatic state machine"""
        self.start_btn.setEnabled(False)
        self.back_btn.setEnabled(False)
        
        # Prepare for Far
        self.state = "INITIALIZATION"
        self.state_start_time = time.time()
        self.instr.setText("Ascolta...")
        if self.logger: self.logger.log("Initialization Started")

    def update_data(self, raw_area):
        filtered = self.filter.area_filtering(raw_area)
        val = filtered if filtered else 0.0
        self.live_val.setText(f"Area registrata: {val:.0f}")
        if self.saver: self.saver.add_data(raw_area, val, 0, 0, 0)
        if self.plotter: self.plotter.add_data(val, threshold=0)

        if self.state == "IDLE" or self.state == "DONE":
            return
        
        elapsed = time.time() - self.state_start_time

        # STATE MACHINE

        if self.state == "INITIALIZATION":
            countdown = self.t_init - elapsed

            if countdown > 0:
                self.instr.setText(f"Inizio calibrazione tra {countdown:.1f}...")
            else:
                self.state = "INSTRUCTION_FAR"

        elif self.state == "INSTRUCTION_FAR":
            if self.logger: self.logger.log(f"Far instruction. Loop {self.count_loops+1}")
            self.play_audio_cue(self.player_far)
            self.current_target = "FAR"
            self.far_data = []

            self.state = "HOLDING"
            self.state_start_time = time.time()
            self.instr.setText(f"Ciclo {self.count_loops+1}/{self.max_count_loops}\nAcquisizione LONTANO...\nResta fermo.")
            self.instr.setStyleSheet("font-size: 26px; color: #0078d7; font-weight: bold;")

        elif self.state == "INSTRUCTION_NEAR":
            if self.logger: self.logger.log(f"Near instruction. Loop {self.count_loops+1}")
            self.play_audio_cue(self.player_near)
            self.current_target = "NEAR"
            self.near_data = []
            self.state = "HOLDING"
            self.state_start_time = time.time()
            self.instr.setText(f"Ciclo {self.count_loops+1}/{self.max_count_loops}\nAcquisizione VICINO...\nResta fermo.")
            self.instr.setStyleSheet("font-size: 26px; color: #0078d7; font-weight: bold;")

        elif self.state == "HOLDING":
            if val > self.min_cut:
                if self.current_target == "FAR":
                    self.far_data.append(val)
                else:
                    self.near_data.append(val)
                 
            if elapsed > self.t_task:
                #if not self.far_data:
                    #self.abort_sequence("Nessun dato rilevato in fase 1")
                    #return
                if self.current_target == "FAR":
                    self.state = "INSTRUCTION_NEAR"
                else:
                    success = self.process_data_loop()

                    if success:
                        self.count_loops += 1

                        if self.count_loops >= self.max_count_loops:
                            self.state = "DONE"
                            self.calculate_new_threshold()
                        else:
                            self.play_audio_cue(self.player_far)
                            self.state = "COOLDOWN"
                            self.state_start_time = time.time()
                            self.instr.setStyleSheet("font-size: 22px; color: #ccc;")
                            if self.logger: self.logger.log(f"Loop {self.count_loops} valid. Starting cooldown.")
        elif self.state == "COOLDOWN":
            countdown = self.t_init - elapsed
            if countdown > 0:
                self.instr.setText(f"Attendi {countdown:.1f}...")
            else:
                self.state = "INSTRUCTION_FAR"

    def process_data_loop (self):
        """ Processes one FAR-NEAR cycle. Returns True if data is valid, False if aborted. """
        if not self.far_data or not self.near_data:
            self.abort_sequence("Nessun dato valido rilevato.")
            return False
        
        mean_far = np.mean(self.far_data)
        std_far = np.std(self.far_data)
        mean_near = np.mean(self.near_data)
        std_near = np.std(self.near_data)

        # quality check if std is too big
        if std_far > mean_far * 0.5 or std_near > mean_near *0.5:
            self.abort_sequence("Dati instabili.\nRiprova")
            self.instr.setText("Errore: dati instabili. \nRiprova")
            if self.logger: self.logger.log("Unstable data detected. Restarting calibration")
            return False
        if mean_near > mean_far:
            self.abort_sequence(f"Dati errati. Vicino ({mean_near:.0f}) > Lontano ({mean_far:.0f}).\nRiprova.")
            if self.logger: self.logger.log("Average near > average far. Restarting calibration")
            return False

        dynamic_range = mean_far - mean_near
        ideal_trigger_area = mean_far - (dynamic_range * 0.5)
        calculated_ratio = round(ideal_trigger_area / mean_far, 2)
        self.calculated_thresholds.append(calculated_ratio)
        if self.logger: self.logger.log(f"Loop calculated ratio: {calculated_ratio}")
        return True

    def calculate_new_threshold(self):
        # if the thresholds in the list are not too far away from each other (diff>0.15), set the average of them as the new threshold
        # otherwise set message for unstable data and ask to retry the calibration
        if len(self.calculated_thresholds) == 0:
            self.abort_sequence("Nessuna soglia calcolata.")
            return
        max_val = max(self.calculated_thresholds)
        min_val = min(self.calculated_thresholds)

        # Variance check across the loops
        if max_val - min_val > 0.15:
            self.abort_sequence(f"Differenza tra loop troppo alta ({max_val} vs {min_val}).\nRiprova.")
            if self.logger: self.logger.log("Threshold variance too high across loops. Aborting.")
            return
            
        # Average the results
        self.final_threshold = round(np.mean(self.calculated_thresholds), 2)
        
        # Display Success
        self.instr.setText(f"CALIBRAZIONE COMPLETATA!\n\nSoglia finale calcolata: {self.final_threshold}")
        self.instr.setStyleSheet("font-size: 24px; color: #00ff00; font-weight: bold;")
        
        if self.logger: self.logger.log(f"Calibration successful. Final threshold: {self.final_threshold}")
        
        # Enable Saving
        self.start_btn.setText("Salva")
        self.start_btn.setEnabled(True)
        self.back_btn.setEnabled(True)
        
        try: self.start_btn.clicked.disconnect()
        except TypeError: pass
        self.start_btn.clicked.connect(self.save_and_exit)

    def save_and_exit(self):
        """ Saves parameters.json and exits the widget """
        try:
            if "constriction" not in self.params:
                self.params["constriction"] = {}
            
            self.params["constriction"]["threshold"] = self.final_threshold

            with open("parameters.json", "w") as f:
                json.dump(self.params, f, indent=4)
            
            print(f"Saved new threshold: {self.final_threshold}")
            if self.logger: self.logger.log("Parameters saved to JSON")
            
            self.go_back_signal.emit()
            
        except Exception as e:
            print(f"Error saving: {e}")
            self.instr.setText(f"Errore di salvataggio: {e}")
            self.instr.setStyleSheet("color: red;")
    
    def abort_sequence(self, reason):
        """Halts the process, displays an error, and asks the user to restart."""
        self.state = "IDLE"
        self.instr.setText(f"ERRORE: {reason}\nPremi Inizia per riprovare dall'inizio.")
        self.instr.setStyleSheet("font-size: 20px; color: red; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.back_btn.setEnabled(True)
        self.count_loops = 0
        self.calculated_thresholds = []