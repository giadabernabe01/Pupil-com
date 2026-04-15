import sys
import time
import numpy as np
import os
import datetime
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from DataProcessing import AreaFilter, ConstrictionMonitor, GazepointReceiver
from HelperClasses import SessionLogger, DataPlotter, DataSaver
from DigitalEye import DigitalEyeWidget

class TestingWidget(QtWidgets.QWidget):
    go_back_signal = QtCore.pyqtSignal()

    def __init__(self, device_type="gazepoint"):
        super().__init__()
        self.device_type = device_type
        self.filter = AreaFilter(fps=130, device_type=self.device_type)
        self.monitor = ConstrictionMonitor(fps=130, thresh=0.75, device_type=self.device_type)
        
        # Sound setup
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

        # UI layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignCenter)

        title = QtWidgets.QLabel("Testing")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(title)

        # Digital eye twin
        self.digital_eye = DigitalEyeWidget(device_type="gazepoint")
        self.layout.addWidget(self.digital_eye)

        self.area_label = QtWidgets.QLabel("Area registrata: 0.0")
        self.area_label.setStyleSheet("color: #888888; font-size: 14px;") # De-emphasized
        self.layout.addWidget(self.area_label)
        self.area_label.hide()

        self.fixation_dot = QtWidgets.QLabel()
        self.fixation_dot.setFixedSize(16, 16)
        self.fixation_dot.setStyleSheet("background-color: red; border-radius: 8px;")
        self.layout.addWidget(self.fixation_dot, alignment=QtCore.Qt.AlignCenter)

        # Dynamic instruction label
        self.message = QtWidgets.QLabel("Inizializzazione in corso...\n Guarda lontano")
        self.message.setStyleSheet("font-size: 18px; margin: 20px")
        self.message.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.message)

        self.gaze_warning_label = QtWidgets.QLabel("")
        self.gaze_warning_label.setStyleSheet("color: #ff4444; font-size: 20px; font-weight: bold;")
        self.gaze_warning_label.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.gaze_warning_label)

        # Results plot
        self.plot_image_label = QtWidgets.QLabel()
        self.plot_image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.plot_image_label.hide() # Keep it hidden until the test ends
        self.layout.addWidget(self.plot_image_label)

        # Buttons
        self.back_button = QtWidgets.QPushButton("Indietro")
        self.back_button.setMinimumHeight(50)
        self.back_button.clicked.connect(self.go_back_signal.emit)
        self.layout.addWidget(self.back_button)

        self.start_button = QtWidgets.QPushButton("Inizia il test")
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.start_testing_sequence)
        self.layout.addWidget(self.start_button)

        self.setLayout(self.layout)

        # Logic Variables
        self.logger = None
        self.plotter = None
        self.trials = []
        self.current_trial_idx = 0
        self.state = "IDLE"
        self.state_start_time = 0.0

        # Styles
        self.style_idle = "background-color: #2b2b2b; color: white;"
        self.style_active = "background-color: #0078d7; color: white"

        # Score counter
        self.correct_constrictions = 0
        self.current_trial_success = False

        # Data Accumulators (prevent overwriting and data loss)
        self.raw_data_history = []
        self.filtered_data_history = []
        self.timestamps_history = []

        self.folder_path = ""

    def start_session(self, folder_path, params, device_type):
        """Called by MainWindow when entering this screen"""
        self.folder_path = folder_path
        self.logger = SessionLogger(folder_path, "Testing")
        self.plotter = DataPlotter(folder_path, "Testing")
        self.saver = DataSaver(folder_path, "Testing")
        self.logger.log("Testing Session Started")
        
        # Retrieve parameters
        self.params = params
        self.device_type = device_type
        constrict_config = self.params.get("constriction", {})
        self.short = constrict_config.get("short_constr_dur", 0.5)
        self.long = constrict_config.get("long_constr_dur", 3.0)
        testing_config = self.params.get("testing_widget", {})
        self.t_init = testing_config.get("initialization_dur", 5.0)

        self.t_short_task = testing_config.get("short_task_dur", 3.5)
        self.t_long_task = testing_config.get("long_task_dur", 6.0)
        self.t_far_interval = testing_config.get("far_interval_dur", 4.0)

        active_fps = self.params.get("active_fps", 60) 
        threshold = self.params["constriction"].get("threshold", 0.75)

        self.filter = AreaFilter(fps=active_fps, device_type=self.device_type)
        self.monitor = ConstrictionMonitor(fps=active_fps, thresh=threshold, device_type=self.device_type)

        # Reset state but wait for user to click start button
        self.reset_logic()
        self.state = "IDLE"
        self.message.setText("Premi 'Inizia' per cominciare")
    
    def end_session(self):
        "Called by MainWindow when leaving"
        if self.logger: self.logger.log("Testing Session Ended")
        if self.plotter: 
            self.plotter.save_plot()
            png_files = [os.path.join(self.folder_path, f) for f in os.listdir(self.folder_path) if f.endswith('.png')]
            
            if png_files:
                # Grab the most recently created file in the list
                latest_plot_path = max(png_files, key=os.path.getmtime)
                
                pixmap = QtGui.QPixmap(latest_plot_path)
                scaled_pixmap = pixmap.scaled(600, 400, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.plot_image_label.setPixmap(scaled_pixmap)
                self.plot_image_label.show()
                
                # Force the GUI to update immediately
                QtWidgets.QApplication.processEvents()

        if self.saver: self.saver.save_file()

        timestamp = datetime.datetime.now().strftime("%H%M%S")

        if self.raw_data_history and self.folder_path:
            try:
                raw_name = f"Testing_Raw_{timestamp}.txt"
                np.savetxt(os.path.join(self.folder_path, raw_name), self.raw_data_history)

                filt_name = f"Testing_filt_{timestamp}.txt"
                np.savetxt(os.path.join(self.folder_path, filt_name), self.filtered_data_history)

                time_name = f"Testing_Filtered_{timestamp}.txt"
                np.savetxt(os.path.join(self.folder_path, time_name), self.timestamps_history)

                if self.logger: self.logger.log(f"Data saved: {raw_name}")
            except Exception as e:
                print(f"Error saving data: {e}")
                if self.logger: self.logger.log(f"Error saving data: {e}")
        self.logger = None
        self.plotter = None
        self.saver = None
        self.reset_logic()

    def reset_logic(self):
        self.current_trial_idx = 0
        self.trials = [1,1,1,2,2]
        np.random.shuffle(self.trials)
        self.monitor.reset_monitor()
        self.start_button.setEnabled(True)
        self.start_button.show()

        self.correct_constrictions = 0
        self.raw_data_history = []
        self.filtered_data_history = []
        self.timestamps_history = []

        self.baseline_x = []
        self.baseline_y = []
        self.center_x = 0.5
        self.center_y = 0.5
        self.gaze_tolerance = 0.15 # Default fallback
        if hasattr(self, 'gaze_warning_label'):
            self.gaze_warning_label.setText("")
        self.is_gaze_deviated = False
        self.gaze_dev_start_time = 0.0

    def start_testing_sequence(self):
        """Triggered by the start button"""
        if self.logger is None and self.folder_path:
            self.logger = SessionLogger(self.folder_path, "Testing")
            self.logger.log("Testing Session Restarted")

        if self.plotter is None and self.folder_path:
            self.plotter = DataPlotter(self.folder_path, "Testing")

        self.saver = DataSaver(self.folder_path, "Testing")

        self.start_button.setEnabled(False)
        self.start_button.hide()
        self.plot_image_label.hide()
        self.state = "BASELINE"
        self.state_start_time = time.time()
        self.message.setText("Acquisizione baseline...\nGuarda lontano")
        if self.logger: self.logger.log("Starting baseline collection")

    def play_audio_cue(self, player):
        """Helper to reliably play sound"""
        player.stop()
        player.setPosition(0)
        player.setVolume(100) # Unmute now
        player.play()

    def update_data(self, raw_area, raw_x=0, raw_y=0):
        """Main Loop called by Main Window"""
        frame_instruction_code = 0
        area = self.filter.area_filtering(raw_area)
        val = area if area is not None else 0.0
        self.area_label.setText(f"Area registrata: {val:.2f}")
        self.digital_eye.update_eye(raw_x, raw_y, val)

        # Calculate threshold
        current_thresh = 0.0
        if len(self.monitor.baseline_buffer) > 0:
            current_thresh = np.mean(self.monitor.baseline_buffer)* self.monitor.thresh

        status = self.monitor.constriction_detector(raw_area)
    
        # Updating plotter
        if self.plotter: self.plotter.add_data(val, current_thresh)

        elapsed = time.time() - self.state_start_time

        # --- STATE MACHINE ---
        if self.state == "IDLE":
            self.monitor.baseline_collection(raw_area)
            if status == 1:
                if self.logger: self.logger.log("Start triggered by Eye")
                self.start_testing_sequence()

        elif self.state == "BASELINE":
            self.monitor.baseline_collection(raw_area)
            if raw_x != 0 and raw_y != 0:
                self.baseline_x.append(raw_x)
                self.baseline_y.append(raw_y)
            if elapsed > self.t_init:
                if self.logger: self.logger.log("Baseline Collected")
                if len(self.baseline_x) > 0:
                    self.center_x = np.mean(self.baseline_x)
                    self.center_y = np.mean(self.baseline_y)
                    
                    # Calculate distances from the new center
                    distances = [np.sqrt((x - self.center_x)**2 + (y - self.center_y)**2) 
                                 for x, y in zip(self.baseline_x, self.baseline_y)]
                    
                    # Tolerance is 3*std. (We add a 0.05 minimum fallback in case they stare perfectly still)
                    self.gaze_tolerance = max(0.15, 3 * np.std(distances))
                    if self.logger: 
                        self.logger.log(f"Gaze Center: ({self.center_x:.2f}, {self.center_y:.2f}) | Tolerance: {self.gaze_tolerance:.3f}")
                self.next_trial()

        elif self.state == "INSTRUCTION_NEAR":
            current_type = self.trials[self.current_trial_idx]
            type_str = "SHORT" if current_type == 1 else "LONG"

            self.message.setText(f"Task {self.current_trial_idx+1}/5: {type_str}\nGUARDA VICINO!")
            if self.logger: self.logger.log(f"Trial {self.current_trial_idx+1}: {type_str} - Audio NEAR")

            self.play_audio_cue(self.player_near)

            self.state = "HOLDING"
            self.state_start_time = time.time()
            self.current_trial_success = False 

        elif self.state == "HOLDING":
            current_type = self.trials[self.current_trial_idx]
            duration = self.t_short_task if current_type == 1 else self.t_long_task
            frame_instruction_code = "NEAR_SHORT" if current_type == 1 else "NEAR_LONG"

            if status == 1:
                if self.plotter: self.plotter.mark_constriction("short")
                if current_type == 1 and not self.current_trial_success:
                    self.current_trial_success = True
                    if self.logger: self.logger.log("Success: Short constriction detected")
            elif status == 2:
                if self.plotter: self.plotter.mark_constriction("long")
                if current_type == 2 and not self.current_trial_success:
                    self.current_trial_success = True
                    if self.logger: self.logger.log("Success: Long constriction detected")
            
            if elapsed >= duration:
                if self.current_trial_success:
                    self.correct_constrictions += 1
                self.state = "INSTRUCTION_FAR"

        elif self.state == "INSTRUCTION_FAR":
            self.message.setText("Guarda Lontano")
            if self.logger: self.logger.log("Audio FAR")
            frame_instruction_code = "FAR"

            self.play_audio_cue(self.player_far)

            self.state = "COOLDOWN"
            self.state_start_time = time.time()

        elif self.state == "COOLDOWN":
            remaining = self.t_far_interval - elapsed
            self.message.setText(f"Attendi. {remaining: .2f}s...")
            frame_instruction_code = "FAR" # <-- Added so it logs "FAR" for the whole interval

            if remaining <= 0:
                self.current_trial_idx += 1
                if self.current_trial_idx >= len(self.trials):
                    self.state = "FINISHED"
                else:
                    self.next_trial()

        if self.state not in ["IDLE", "BASELINE", "FINISHED", "COMPLETED_IDLE"]:
            if raw_x != 0 and raw_y != 0:
                current_dist = np.sqrt((raw_x - self.center_x)**2 + (raw_y - self.center_y)**2)
                
                if current_dist > self.gaze_tolerance:
                    self.gaze_warning_label.setText("") #("⚠ SGUARDO FUORI CENTRO ⚠")
                    if not self.is_gaze_deviated:
                        self.is_gaze_deviated = True
                        self.gaze_dev_start_time = 0.0
                        if self.logger: self.logger.log("Warning: Gaze deviated from center")
                else:
                    self.gaze_warning_label.setText("")
                    if self.is_gaze_deviated:
                        self.is_gaze_deviated = False
                        dev_duration = time.time() - self.gaze_dev_start_time
                        if self.logger: self.logger.log(f"Gaze returned to center after {dev_duration}s.")
            else:
                self.gaze_warning_label.setText("⚠ OCCHIO NON RILEVATO ⚠")

                if not self.is_gaze_deviated:
                    self.is_gaze_deviated = True
                    self.gaze_dev_start_time = time.time()
                    if self.logger: self.logger.log("Warning: Eye tracking lost")
        
        if self.saver and self.state not in ["FINISHED", "COMPLETED_IDLE"]:
            self.saver.add_data(
                raw_area, 
                val, 
                current_thresh, 
                status, 
                frame_instruction_code,
                #extra_value="", # Leave blank if unused
                gaze_x=raw_x,   # Pass X coordinate
                gaze_y=raw_y    # Pass Y coordinate 
            )

        # Handle the shutdown independently so it doesn't block the saver
        if self.state == "FINISHED":
            score_msg = f"Test Completato.\n Costrizioni rilevate correttamente: {self.correct_constrictions}/5"
            self.message.setText(score_msg)
            if self.logger: 
                self.logger.log("Testing Trials completed")
                self.logger.log(f"Final Score: {self.correct_constrictions}/5")

            self.state = "COMPLETED_IDLE"
            self.end_session()

    def next_trial(self):
        """Prepares state for the next trial"""
        self.state = "INSTRUCTION_NEAR"
        self.state_start_time = time.time()