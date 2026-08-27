import sys
import time
import numpy as np
import zmq
import winsound
import subprocess
import os
import matplotlib.pyplot as plt
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QSizePolicy, QApplication, QMessageBox
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from DataProcessing import AreaFilter, ConstrictionMonitor
from HelperClasses import SessionLogger, DataPlotter, DataSaver

# ---------------------------------------------------------
# YES/NO WIDGET
# ---------------------------------------------------------
class YNWidget(QtWidgets.QWidget):
    go_back_signal = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.filter = AreaFilter(fps=130, device_type="gazepoint")
        self.monitor = ConstrictionMonitor(fps=130, thresh=0.75, device_type="gazepoint")

        #Sound setup
        self.player = QMediaPlayer()
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.sound_directory = os.path.join(base_path, "Sounds")
        self.sound_yes = os.path.join(self.sound_directory, "answer_yes.mp3")
        self.sound_no = os.path.join(self.sound_directory, "answer_no.mp3")

        self.layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel("Sì o No?")
        self.layout.addWidget(self.label)
        self.setWindowTitle("Sì o No?")

        self.area_label = QtWidgets.QLabel("Area: 0.0")
        self.layout.addWidget(self.area_label)

        self.ans_label = QtWidgets.QLabel("Acquisizione baseline\nGuarda lontano...")
        self.ans_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.ans_label)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.setSpacing(30)

        self.yes_button = QtWidgets.QPushButton("SI")
        self.yes_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.button_layout.addWidget(self.yes_button)
        self.no_button = QtWidgets.QPushButton("NO")
        self.no_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.button_layout.addWidget(self.no_button)
        self.layout.addLayout(self.button_layout)

        self.back_button = QtWidgets.QPushButton("Indietro")
        self.layout.addWidget(self.back_button)
        self.back_button.clicked.connect(self.go_back_signal.emit)
        
        # STATE MACHINE VARIABLES
        self.state = "INITIALIZATION" # options: INITIALIZATION, SCANNING, COOLDOWN
        self.state_start_time = time.time()
        self.pending_selection = False
        self.qa_counter = 0
        self.advance_trial = False

        # SCANNING VARIABLES
        self.current_option = "YES" # options: YES, NO
        self.current_pause_opt = 0 # 0: RIPRENDI, 1: ESCI
        self.scan_start_time = 0

        # VISUAL STYLES
        self.active_style = "background-color: #0078d7; color: white;"
        self.inactive_style = "background-color: #333333; color: gray;"
        self.detected_style = "background-color: #1a1a1a; color: #555; border: 1px solid #333;" # Dark/Greyed out
        self.yes_button.setStyleSheet(self.active_style)
        self.no_button.setStyleSheet(self.active_style)

        # Tools placeholders
        self.logger = None
        self.plotter = None
        self.saver = None

        self.setLayout(self.layout)

    def mousePressEvent(self, event):
        """Metodo nativo di PyQt: scatta solo quando l'utente clicca il widget"""
        self.advance_trial = True

    def resizeEvent(self, event):
        """Dynamically scales all text to fit the screen size"""
        base_size = max(16, int(self.height() / 25))
        
        # Big SI / NO buttons
        main_btn_font = QtGui.QFont('Arial', int(base_size * 2), QtGui.QFont.Bold)
        self.yes_button.setFont(main_btn_font)
        self.no_button.setFont(main_btn_font)
        
        # Smaller Back button
        self.back_button.setFont(QtGui.QFont('Arial', base_size, QtGui.QFont.Bold))
        
        # Labels
        if hasattr(self, 'label'):
            self.label.setFont(QtGui.QFont('Arial', int(base_size * 1.5), QtGui.QFont.Bold))
        if hasattr(self, 'ans_label'):
            self.ans_label.setFont(QtGui.QFont('Arial', base_size, QtGui.QFont.Bold))
        if hasattr(self, 'area_label'):
            self.area_label.setFont(QtGui.QFont('Arial', int(base_size * 0.8)))

        super().resizeEvent(event)

    def start_session(self, folder_path, params, device_type):
        """ Called by MainWindow when entering this screen """
        self.logger = SessionLogger(folder_path, "YesNo_Widget")
        self.plotter = DataPlotter(folder_path, "YesNo_Widget")
        self.saver = DataSaver(folder_path, "YesNo_Widget")

        # Retrieve parameters
        self.params = params
        self.device_type = device_type
        constrict_config = self.params.get("constriction", {})
        self.short = constrict_config.get("short_constr_dur", 0.5)
        self.long = constrict_config.get("long_constr_dur", 3.0)
        wf_config = self.params.get("yn_widget", {})
        self.t_init = wf_config.get("initialization_dur", 5.0)
        self.t_scan = wf_config.get("scan_interval_dur", 4.0)
        self.t_cool = wf_config.get("cooldown_dur", 5.0)

        active_fps = self.params.get("active_fps", 60) 
        threshold = self.params["constriction"].get("threshold", 0.75)

        self.filter = AreaFilter(fps=active_fps, device_type=self.device_type)
        self.monitor = ConstrictionMonitor(fps=active_fps, thresh=threshold, device_type=self.device_type)

        self.reset_to_initialization()
        self.logger.log("Session Started")

    def end_session(self):
        """ Called by MainWindow when leaving """
        if self.logger: self.logger.log("Session ended")
        if self.plotter: self.plotter.save_plot()
        if self.saver: self.saver.save_file(extra_column_name="Answer_Code")
        self.logger = None
        self.plotter = None
        self.saver = None

    def play_sound(self,file_path):
        """Helper to play audiio cues."""
        if os.path.exists(file_path):
            url = QUrl.fromLocalFile(file_path)
            content = QMediaContent(url)
            self.player.setMedia(content)
            self.player.play()
        else:
            print(f"File audio non trovato: {file_path}")
    
    def update_visual_scanning(self):
        """Helper to handle the blinking YEN/NO buttons"""
        elapsed = time.time() - self.scan_start_time

        if elapsed >= self.t_scan:
            self.scan_start_time = time.time()
            self.current_option = "NO" if self.current_option == "YES" else "YES"
        if self.current_option == "YES":
            self.yes_button.setStyleSheet(self.active_style)
            self.no_button.setStyleSheet(self.inactive_style)
        else:
            self.yes_button.setStyleSheet(self.inactive_style)
            self.no_button.setStyleSheet(self.active_style)

    def set_ui_detected(self):
        """Freezes the UI when a short constriction is performed, waiting for short or long confirmation"""
        if self.state == "SCANNING":
            if self.current_option == "YES":
                self.no_button.setStyleSheet(self.detected_style)
            else:
                self.yes_button.setStyleSheet(self.detected_style)
        elif self.state == "PAUSED":
            if self.current_pause_opt == 0:
                self.no_button.setStyleSheet(self.detected_style)
            else:
                self.yes_button.setStyleSheet(self.detected_style)

    def trigger_pause(self):
        """Helper to safely move into pause mode"""
        if self.logger: self.logger.log("Pause triggered via Long Constriction")
        self.state = "WAIT_RELEASE"
        self.pending_selection = False
        self.label.setText("PAUSA")
        self.ans_label.setText("GUARDA LO SCHERMO PER METTERE IN PAUSA")
        self.ans_label.setStyleSheet("font-size: 20px; font-weight: bold; color: yellow;")
        self.yes_button.setStyleSheet(self.inactive_style)
        self.no_button.setStyleSheet(self.inactive_style)
        self.monitor.reset_monitor()

    def show_timeout_dialog(self):
        """Pauses the interface and requests the caregiver's assistance."""
        
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

    def update_data(self, raw_area):
        frame_answer_code = 0
        area = self.filter.area_filtering(raw_area)
        # Signal loss timeout check
        if self.filter.timeout_triggered:
            self.show_timeout_dialog()
            return
        val = area if area is not None else 0.0
        self.area_label.setText(f"Area registrata: {val:.2f}")
        current_thresh = self.monitor.current_sma_thresh
        exit_thresh = self.monitor.exit_thresh
        # Monitor logic
        status = self.monitor.constriction_detector(raw_area)

        is_constricted = self.monitor.drop_start_time is not None

        # STATE MACHINE logic. Check DOCUMENTATION for the detailed diagram.
        if self.state == "INITIALIZATION":
            self.ans_label.setText("Guarda lontano e ascolta la domanda")

            self.monitor.baseline_collection(raw_area)

            # Activates answers scanning and increases counter at caregiver's click.
            if self.advance_trial:
                self.advance_trial = False
                self.qa_counter+=1
                if self.logger: self.logger.log(f"Question {self.qa_counter} asked. Moving to answer {self.qa_counter}.")
                self.state = "SCANNING"
                self.current_option = "YES"
                self.scan_start_time = time.time()
                self.state_start_time = time.time()
                self.ans_label.setText("Guarda vicino quando la tua risposta è illuminata.")
        
        elif self.state == "SCANNING":
            # Check constriction from monitor
            if not is_constricted and not self.pending_selection:
                self.update_visual_scanning()
            
            if status == 1:
                if self.logger: self.logger.log("Constriction detected. Waiting for short/long confirmation")
                if self.plotter: self.plotter.mark_constriction("short")
                self.pending_selection = True
                self.set_ui_detected()

            elif status == 2:
                if self.plotter: self.plotter.mark_constriction("long")
                self.trigger_pause()
                return
            
            elif not is_constricted and self.pending_selection:
                elapsed = time.time() - self.state_start_time
                if self.logger: self.logger.log(f"Short constriction confirmed. Answer: {self.current_option} to question {self.qa_counter}. Provided in: {elapsed} s")
                self.ans_label.setText(f"Hai risposto: {self.current_option}")
                self.ans_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")

                #Sound playing
                if self.current_option == "YES": 
                    self.play_sound(self.sound_yes)
                    frame_answer_code = 1
                else: 
                    self.play_sound(self.sound_no)
                    frame_answer_code = 2

                self.pending_selection = False
                self.state = "COOLDOWN"
                self.state_start_time = time.time()
                self.yes_button.setStyleSheet(self.inactive_style)
                self.no_button.setStyleSheet(self.inactive_style)
                self.monitor.reset_monitor()

        elif self.state == "WAIT_RELEASE":

            if status == 0 and val > current_thresh:
                self.state = "PAUSED"
                self.ans_label.setText("VUOI USCIRE?")
                self.yes_button.setText("RIPRENDI")
                self.no_button.setText("ESCI")
                self.current_pause_opt = 0 # 0=Riprendi, 1=Esci
                self.scan_start_time = time.time()
                self.monitor.reset_monitor()

        elif self.state == "PAUSED":
            if not is_constricted and not self.pending_selection:
                elapsed = time.time() - self.scan_start_time
                if elapsed >= self.t_scan:
                    self.scan_start_time = time.time()
                    self.current_pause_opt = 1 - self.current_pause_opt

                if self.current_pause_opt == 0:
                    self.yes_button.setStyleSheet(self.active_style)
                    self.no_button.setStyleSheet(self.inactive_style)
                else:
                    self.yes_button.setStyleSheet(self.inactive_style)
                    self.no_button.setStyleSheet(self.active_style)

            if status == 1:
                self.pending_selection = True
                self.set_ui_detected()

            elif not is_constricted and self.pending_selection:
                self.pending_selection = False
                self.monitor.reset_monitor()

                self.label.setText("Sì o No?")
                self.yes_button.setText("SI")
                self.no_button.setText("NO")
                self.yes_button.setStyleSheet(self.inactive_style)
                self.no_button.setStyleSheet(self.inactive_style)

                if self.current_pause_opt == 0:
                    if self.logger: self.logger.log("Resuming from pause")
                    self.state = "COOLDOWN"
                    self.state_start_time = time.time()
                else:
                    if self.logger: self.logger.log("Exit confirmed from pause")
                    self.go_back_signal.emit()
                    self.reset_to_initialization()
                        
        elif self.state == "COOLDOWN":
            #check for status 2 in case long constriction triggered an answer
            if status == 2:
                self.trigger_pause()
                return
            # Wait 5 seconds before restarting the loop
            remaining = self.t_cool - (time.time() - self.state_start_time)
            self.ans_label.setText(f"Rispondi a un'altra domanda tra {remaining: .1f}...")

            if remaining <=0:
                self.advance_trial= False
                self.reset_to_initialization()

        # Save data to CSV
        if self.saver:
            self.saver.add_data(raw_area, val, current_thresh, exit_thresh, status, frame_answer_code)
        
        # Plot data
        if self.plotter:
            self.plotter.add_data(val, current_thresh, exit_thresh)


    def reset_to_initialization(self):
        """Helper to cleanly reset the state and baseline"""
        self.monitor.reset_monitor()
        self.state = "INITIALIZATION"
        self.state_start_time = time.time()
        self.pending_selection = False
        self.label.setText("Sì o No?")
        self.yes_button.setText("SI")
        self.no_button.setText("NO")
        self.ans_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.yes_button.setStyleSheet(self.active_style)
        self.no_button.setStyleSheet(self.active_style)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YNWidget()
    ex.show()
    sys.exit(app.exec_())
