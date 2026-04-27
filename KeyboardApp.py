import sys
import time
import numpy as np
import os
import matplotlib.pyplot as plt
import difflib as dfl
import threading
import winsound
from autocorrect import Speller
from wordfreq import top_n_list
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit, QLabel, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from DataProcessing import AreaFilter, ConstrictionMonitor
from HelperClasses import SessionLogger, DataPlotter, DataSaver

# in csv file add near/far instruction and written word/letter

class KeyboardApp(QWidget):
    go_back_signal = QtCore.pyqtSignal()
    
    def __init__(self):
        super().__init__()
        # Tools initialization
        self.filter = AreaFilter(fps=130, device_type="gazepoint")
        self.monitor = ConstrictionMonitor(fps=130, thresh=0.75, device_type="gazepoint")

        # Suggestions hybrid logic setup
        self.spell = Speller(lang='it') # from autocorrect library
        self.common_words = top_n_list('it', 10000) # most frequent words in Italian
        self.default_suggestions = ['CIAO', 'COME', 'NON']

        #Logic flags
        self.pending_selection = None # options: None, "SHORT", "LONG", 
        self.last_logged_state = None
        self.loop_count = 0
        self.max_loops = 2

        # Layout setup
        self.layout = QVBoxLayout()
        self.label = QLabel("SCRIVI QUELLO CHE VUOI")
        self.label.setFont(QFont('Arial', 16, QFont.Bold))
        self.label.setStyleSheet('color: white;')
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        
        # Live status label (added as it was referenced in your update_data)
        self.live_label = QLabel("INITIALIZING...")
        self.live_label.setStyleSheet('color: #aaa; font-size: 14px;')
        self.live_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.live_label)

        self.setWindowTitle('App Tastiera')
        self.setStyleSheet('background-color: #2b2b2b')

        # Display
        self.display = QLineEdit()
        self.display.setFont(QFont('Arial', 24))
        self.display.setStyleSheet("padding: 10px; font-size: 16px; color: white; background-color: #444; border: 1px solid #666")
        self.layout.addWidget(self.display)

        # Visual styles
        self.active_style = "background-color: #0078d7; color: white; border: 2px solid white;"
        self.inactive_style = "background-color:#2b2b2b; color: white; border: 1px solid #555;"
        self.detected_style = "background-color: #1a1a1a; color: #555; border: 1px solid #333;" # Dark/Greyed out

        # Grid setup
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8)
        self.layout.addLayout(self.grid_layout)

        # Suggestion buttons
        self.suggestion_widgets = []
        for i in range(3):
            btn = QPushButton(self.default_suggestions[i])
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setFont(QFont('Arial', 14 , QFont.Bold))
            btn.setStyleSheet(self.inactive_style)
            btn.clicked.connect(lambda checked, idx=i: self.process_suggestion_click(idx))
            self.grid_layout.addWidget(btn, 0, i*2, 1, 2)
            self.suggestion_widgets.append(btn)

        # Keys setup
        self.keys = [ 
            ['R','S','E','T','L','P'],
            ['A','N','C','B','M', 'G'],
            ['I','V','D', 'F', 'U', 'H'],
            ['O','QU', 'Z','Y','J', '!'],
            ['K','W','X','?','.',',']
        ]

        self.button_matrix = []
        for row_idx, row in enumerate(self.keys):
            button_row = []
            for col_idx, key in enumerate(row):
                btn = QPushButton(key)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setFont(QFont('Arial', 18, QFont.Bold))
                btn.setStyleSheet(self.inactive_style)
                btn.clicked.connect(lambda checked, k=key: self.on_click(k))
                self.grid_layout.addWidget(btn, row_idx+1, col_idx)
                button_row.append(btn)
            self.button_matrix.append(button_row)

        # Space and Canc buttons
        self.bottom_row_idx = len(self.keys) + 1
        self.space_btn = QPushButton("SPAZIO")
        self.space_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.space_btn.setFont(QFont('Arial', 16, QFont.Bold))
        self.space_btn.setStyleSheet(self.inactive_style)
        self.space_btn.clicked.connect(lambda: self.on_click(" "))
        self.grid_layout.addWidget(self.space_btn, self.bottom_row_idx, 0, 1, 4)

        self.canc_button = QPushButton("CANCELLA")
        self.canc_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canc_button.setFont(QFont('Arial', 16, QFont.Bold))
        self.canc_button.setStyleSheet(self.inactive_style)
        self.canc_button.clicked.connect(lambda: self.on_click("CANC"))
        self.grid_layout.addWidget(self.canc_button, self.bottom_row_idx, 4, 1, 2)

        # Back button
        self.back_button = QPushButton("MENÙ PRINCIPALE")
        self.back_button.setFont(QFont('Arial', 12, QFont.Bold))
        self.back_button.setStyleSheet(self.inactive_style)
        self.back_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.back_button.setMinimumHeight(40)
        self.back_button.setMaximumHeight(60)
        self.back_button.clicked.connect(self.go_back_signal.emit)
        self.layout.addWidget(self.back_button)

        # Pause menu overlay widgets
        self.pause_label = QLabel("PAUSA\nGuarda vicino per selezionare")
        self.pause_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.pause_label.setStyleSheet('color: yellow;')
        self.pause_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.pause_label)

        self.btn_riprendi = QPushButton("RIPRENDI")
        self.btn_esci = QPushButton("MENU PRINCIPALE")
        for btn in (self.btn_riprendi, self.btn_esci):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setFont(QFont('Arial', 16, QFont.Bold))
            btn.setStyleSheet(self.inactive_style)
            self.layout.addWidget(btn)
            
        self.pause_label.hide()
        self.btn_riprendi.hide()
        self.btn_esci.hide()

        # State machine variables
        self.state = "INITIALIZATION"
        self.state_start_time = time.time()
        self.scan_start_time = time.time()
        self.next_state = "KEYBOARD_ROW"
        
        self.current_row_idx = -1
        self.current_col_idx = -1
        self.current_sugg_idx = -1
        self.current_pause_opt = 0

        self.setLayout(self.layout)

    def resizeEvent(self, event):
        """Dynamically scales all text to fit the screen size"""
        super().resizeEvent(event)
        
        # Calculate base size relative to window height (minimum 14px)
        base_size = max(14, int(self.height() / 30)) 

        # 1. Update all standard buttons to be HUGE (1.8x multiplier)
        key_font_size = int(base_size * 1.8)
        key_font = QFont('Arial', key_font_size, QFont.Bold)
        for btn in self.findChildren(QPushButton):
            btn.setFont(key_font)

        # 2. OVERRIDE Suggestion Buttons (Slightly smaller so words fit, 1.2x)
        sugg_font_size = int(base_size * 1.2)
        sugg_font = QFont('Arial', sugg_font_size, QFont.Bold)
        for btn in self.suggestion_widgets:
            btn.setFont(sugg_font)

        # 3. OVERRIDE the Back Button to be smaller (0.7x)
        small_btn_font_size = max(12, int(base_size * 0.7))
        small_btn_font = QFont('Arial', small_btn_font_size, QFont.Bold)
        self.back_button.setFont(small_btn_font)

        # 4. Update the Text Display
        self.display.setFont(QFont('Arial', int(base_size * 1.5)))
        
        # 5. Update all Labels
        self.label.setFont(QFont('Arial', int(base_size * 1.2), QFont.Bold))
        self.pause_label.setFont(QFont('Arial', int(base_size * 1.5), QFont.Bold))
        self.live_label.setFont(QFont('Arial', int(base_size * 0.8)))

    def log_once(self, message):
        """Prevents logging identical messages at high frame rates"""
        if self.logger and self.last_logged_state != message:
            self.logger.log(message)
            self.last_logged_state = message

    def play_sharp_beep(self):
        """Plays a high-pitch, short beep in a separate thread to prevent UI freezing"""
        # Frequency = 2000Hz (sharp), Duration = 80ms (very short)
        threading.Thread(target=winsound.Beep, args=(2000, 80), daemon=True).start() 

    def start_session(self, folder_path, params, device_type):
        self.logger = SessionLogger(folder_path, "Keyboard_Widget")
        self.plotter = DataPlotter(folder_path, "Keyboard_Widget")
        self.saver = DataSaver(folder_path, "Keyboard_Widget")

        # Retrieve parameters
        self.params = params
        self.device_type = device_type
        constrict_config = self.params.get("constriction", {})
        self.short = constrict_config.get("short_constr_dur", 0.5)
        self.long = constrict_config.get("long_constr_dur", 3.0)
        wf_config = self.params.get("keyboard_widget", {})
        self.t_init = wf_config.get("initialization_dur", 3.0)
        self.scan_interval = wf_config.get("scan_interval_dur", 3.0)
        self.t_cool = wf_config.get("cooldown_dur", 2.0)
        self.max_loops = wf_config.get("max_loops", 2)
        self.t_exit = wf_config.get("extra_trigger_dur", 5.0)

        active_fps = self.params.get("active_fps", 60) 
        threshold = self.params["constriction"].get("threshold", 0.75)

        self.filter = AreaFilter(fps=active_fps, device_type=self.device_type)
        self.monitor = ConstrictionMonitor(fps=active_fps, thresh=threshold, device_type=self.device_type, short_dur=self.short, long_dur=self.long)

        self.reset_to_initialization()
        if self.logger: self.logger.log("Session Started")

    def end_session(self):
        if self.logger: self.logger.log("Session ended")
        if self.plotter: self.plotter.save_plot()
        if self.saver: self.saver.save_file()
        self.logger = None
        self.plotter = None
        self.saver = None

    def reset_to_initialization(self):
        self.monitor.baseline_buffer.clear()
        self.display.setText("")
        self.state = "INITIALIZATION"
        self.state_start_time = time.time()
        self.pending_selection = None
        self.toggle_pause_ui(False)
        self.reset_ui_styles()

    def update_suggestions(self):
        current_text = self.display.text()
        if not current_text or current_text.endswith(" "):
            self.apply_suggestions(self.default_suggestions)
            return

        words = current_text.split(" ")
        last_word = words[-1].lower()

        matches = [w.upper() for w in self.common_words if w.startswith(last_word)]
        suggestions = matches[:3]

        if len(suggestions) < 3:
            correction = self.spell(last_word).upper()
            if correction != last_word.upper() and correction not in suggestions:
                suggestions.append(correction)

        while len(suggestions) < 3:
            for d in self.default_suggestions:
                if d not in suggestions:
                    suggestions.append(d)
                if len(suggestions) == 3: break
        
        self.apply_suggestions(suggestions)

    def apply_suggestions(self, word_list):
        for i, word in enumerate(word_list):
            btn = self.suggestion_widgets[i]
            btn.setText(word)
            btn.setProperty("word_val", word)

    def process_suggestion_click(self,idx):
        btn = self.suggestion_widgets[idx]
        word = btn.property("word_val")
        if word:
            print(f"DEBUG: Sggerimento cliccato: {word}")
            self.on_click_suggestion(word)
    
    def on_click_suggestion(self, word):
        current_text = self.display.text()
    
        if current_text.endswith(" "):
            new_text = current_text + word + " "
        else:
            words = current_text.split(" ")
            if words:
                words[-1] = word #
            new_text = " ".join(words) + " "

        self.display.setText(new_text)
        self.update_suggestions()
        self.log_once(f"Word completed/replaced: {word}")
        self.next_state = "KEYBOARD_ROW"

    def toggle_pause_ui(self, show_pause):
        """Swaps the entire keyboard layout for the pause menu"""
        self.display.setVisible(not show_pause)
        self.label.setVisible(not show_pause)
        self.back_button.setVisible(not show_pause)

        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget: widget.setVisible(not show_pause)

        self.pause_label.setVisible(show_pause)
        self.btn_riprendi.setVisible(show_pause)
        self.btn_esci.setVisible(show_pause)

    def update_visual_scanning(self):
        """Logic for cycling the highlights based on elapsed time"""
        elapsed = time.time() - self.scan_start_time
        if elapsed >= self.scan_interval:
            self.scan_start_time = time.time()
            self.reset_ui_styles()

            # 1. Row Scanning (Including the Bottom Row)
            if self.state == "KEYBOARD_ROW":
                total_rows = len(self.button_matrix) + 1
                self.current_row_idx = (self.current_row_idx + 1) % total_rows
                
                if self.current_row_idx < len(self.button_matrix):
                    for btn in self.button_matrix[self.current_row_idx]:
                        btn.setStyleSheet(self.active_style)
                else: # The "SPAZIO/CANC" Row
                    self.space_btn.setStyleSheet(self.active_style)
                    self.canc_button.setStyleSheet(self.active_style)

            # 2. Column Scanning (Inside a selected row)
            elif self.state == "KEYBOARD_COL":
                if self.current_row_idx < len(self.button_matrix):
                    row_len = len(self.button_matrix[self.current_row_idx])
                else:
                    row_len = 2
                    
                self.current_col_idx = (self.current_col_idx + 1) % row_len

                if self.current_col_idx == 0:
                    self.loop_count += 1

                if self.loop_count >= self.max_loops:
                    self.log_once("Loop limit reached: Auto-resetting to Rows")
                    self.loop_count = 0
                    self.state = "KEYBOARD_ROW"
                    self.current_row_idx = -1
                    self.reset_ui_styles()
                    return
                
                # apply active style to current button 
                if self.current_row_idx < len(self.button_matrix):
                    self.button_matrix[self.current_row_idx][self.current_col_idx].setStyleSheet(self.active_style)
                else:
                    target = self.space_btn if self.current_col_idx == 0 else self.canc_button
                    target.setStyleSheet(self.active_style)

            # 3. Suggestion Scanning
            elif self.state == "SUGGESTIONS":
                self.current_sugg_idx = (self.current_sugg_idx + 1) % len(self.suggestion_widgets)
                self.suggestion_widgets[self.current_sugg_idx].setStyleSheet(self.active_style)

            # 4. Puase options scanning
            elif self.state == "PAUSED":
                self.current_pause_opt = 1 - self.current_pause_opt
                if self.current_pause_opt == 0:
                    self.btn_riprendi.setStyleSheet(self.active_style)
                    self.btn_esci.setStyleSheet(self.inactive_style)
                else:
                    self.btn_riprendi.setStyleSheet(self.inactive_style)
                    self.btn_esci.setStyleSheet(self.active_style)

    def set_ui_detected(self):
        """Visual feedback: the UI freezes and the target buttons is highlighted as detected"""
        for btn in self.findChildren(QPushButton):
            if btn == self.back_button: continue

            if self.state != "PAUSED" and btn in (self.btn_riprendi, self.btn_esci): continue
            if self.state == "PAUSED" and btn not in (self.btn_riprendi, self.btn_esci): continue

            is_target = False
            if self.state == "KEYBOARD_ROW":
                if self.current_row_idx < len(self.button_matrix):
                    is_target = (btn in self.button_matrix[self.current_row_idx])
                else:
                    is_target = (btn in [self.space_btn, self.canc_button])
            elif self.state == "KEYBOARD_COL":
                if self.current_row_idx < len(self.button_matrix):
                    is_target = (btn == self.button_matrix[self.current_row_idx][self.current_col_idx])
                else:
                    is_target = (btn == (self.space_btn if self.current_col_idx == 0 else self.canc_button))
            elif self.state == "SUGGESTIONS":
                is_target = (btn == self.suggestion_widgets[self.current_sugg_idx])
            elif self.state == "PAUSED":
                is_target = (btn == self.btn_riprendi if self.current_pause_opt == 0 else btn == self.btn_esci)

            if not is_target:
                btn.setStyleSheet(self.detected_style)

    def reset_ui_styles(self):
        """Resets all the button to default inactive style"""
        for btn in self.findChildren(QPushButton):
            if btn != self.back_button:
                btn.setStyleSheet(self.inactive_style)

    def trigger_pause(self):
        self.log_once("Extra Long constriction detected: Triggering Pause")
        self.state = "WAIT_RELEASE"
        self.pending_selection = None
        self.toggle_pause_ui(True)
        self.pause_label.setText("RILASCIA PER PAUSA")
        self.btn_riprendi.setStyleSheet(self.inactive_style)
        self.btn_esci.setStyleSheet(self.inactive_style)
        self.monitor.reset_monitor()

    def update_data(self, raw_area):
        """Main update loop triggered by raw data input"""
        frame_output = 0
        area = self.filter.area_filtering(raw_area)
        status = self.monitor.constriction_detector(raw_area)
        is_eye_constricted = self.monitor.drop_start_time is not None

        current_thresh = self.monitor.current_sma_thresh
        exit_thresh = self.monitor.exit_thresh

        plot_val = area if area is not None else 0.0

        if area is not None:
            self.live_label.setText(f"Acquisendo...")
        else:
            self.live_label.setText("AREA NON TROVATA")

        # --- STATE MACHINE LOGIC ---
        if self.state == "INITIALIZATION":
            self.log_once("Initialization Started")
            self.monitor.baseline_collection(raw_area)
            if time.time() - self.state_start_time >= self.t_init:
                self.state = "KEYBOARD_ROW"
                self.current_row_idx = -1
                self.scan_start_time = time.time()
                self.live_label.setText("SELEZIONA UNA RIGA")
                
        elif self.state == "KEYBOARD_ROW":
            if not is_eye_constricted and not self.pending_selection:
                self.update_visual_scanning()

            if status == 1: # Short: Select Row
                self.log_once("Short constriction detected: waiting for selection confirmed")
                if self.plotter: self.plotter.mark_constriction("short")
                self.pending_selection = "SHORT"
                self.set_ui_detected()
            elif status == 2: # Long: Suggestions
                if self.pending_selection != "LONG":
                    self.play_sharp_beep()
                self.log_once("Long constriction detected: moving to Suggestions")
                if self.plotter: self.plotter.mark_constriction("long")
                self.pending_selection = "LONG"
            elif status == 3: # Extra long: exit request
                self.trigger_pause()
            elif not is_eye_constricted and self.pending_selection == "SHORT":
                self.log_once("Short constriction confirmed: selecting row")
                self.pending_selection = None
                self.next_state = "KEYBOARD_COL"
                self.state = "COOLDOWN"
                self.state_start_time = time.time()                
            elif not is_eye_constricted and self.pending_selection == "LONG":
                self.log_once("Long constriction confirmed: moving to Suggestions")
                self.pending_selection = None
                self.next_state = "SUGGESTIONS"
                self.state = "COOLDOWN"
                self.current_sugg_idx = -1
                self.reset_ui_styles()
                

        elif self.state == "KEYBOARD_COL":
            if not is_eye_constricted and not self.pending_selection:
                self.update_visual_scanning()

            is_on_canc = (self.current_row_idx >= len(self.button_matrix) and self.current_col_idx == 1)

            if status == 1: # Short: Select Key
                self.log_once("Short constriction detected: waiting for selection confirmed")
                if self.plotter: self.plotter.mark_constriction("short")
                self.pending_selection = "SHORT"
                self.set_ui_detected()
            elif status == 2:
                if self.pending_selection != "LONG":
                    self.play_sharp_beep()
                self.log_once("Long constriction detected: moving to suggestions")
                if self.plotter: self.plotter.mark_constriction("long")
                self.pending_selection = "LONG"
            elif status == 3:
                self.trigger_pause()
            elif not is_eye_constricted and self.pending_selection == "SHORT":
                self.log_once("Short constriction confirmed: selecting key")
                self.pending_selection = None
                if self.current_row_idx < len(self.button_matrix):
                    btn = self.button_matrix[self.current_row_idx][self.current_col_idx]
                    btn.click()
                    frame_output = btn.text()
                    self.next_state = "KEYBOARD_ROW"
                else:
                    target = self.space_btn if self.current_col_idx == 0 else self.canc_button
                    target.click()
                    frame_output = target.text()

                self.state = "COOLDOWN"
                self.state_start_time = time.time()
            elif not is_eye_constricted and self.pending_selection == "LONG":
                self.log_once("Long constriction confirmed: Action triggered")
                self.pending_selection = None
                if is_on_canc:
                    self.on_click("FULL_CANC")
                    frame_output = "FULL_CANC"
                    self.next_state = "KEYBOARD_COL"
                    self.current_col_idx = 0
                else:
                    self.next_state = "SUGGESTIONS"

                self.state = "COOLDOWN"
                self.current_sugg_idx = -1
                self.reset_ui_styles()
                self.state_start_time = time.time()              

        elif self.state == "SUGGESTIONS":
            self.log_once("Scanning Suggestions Started")
            if not is_eye_constricted and not self.pending_selection:
                self.update_visual_scanning()
            if status == 1:
                self.log_once("Short constriction detected: waiting for selection confirmed")
                if self.plotter: self.plotter.mark_constriction("short")
                self.pending_selection = "SHORT"
                self.set_ui_detected()
            elif status == 2:
                if self.pending_selection != "LONG":
                    self.play_sharp_beep()
                self.log_once("Long constriction detected: moving to keyboard")
                if self.plotter: self.plotter.mark_constriction("long")
                self.pending_selection = "LONG"
                #self.next_state = "KEYBOARD_ROW"
                #self.state = "COOLDOWN"
                #self.reset_ui_styles()
            elif status == 3:
                self.trigger_pause()
            elif not is_eye_constricted and self.pending_selection == "SHORT":
                self.log_once("Short constriction confirmed: selecting word")
                word = self.suggestion_widgets[self.current_sugg_idx]
                word.click()
                frame_output = word.text()
                self.pending_selection = None
                self.next_state = "KEYBOARD_ROW"
                self.state = "COOLDOWN"
                self.state_start_time = time.time()
            elif not is_eye_constricted and self.pending_selection == "LONG":
                self.log_once("Long constriction confirmed: returning to Keyboard Row")
                self.pending_selection = None
                self.next_state = "KEYBOARD_ROW"
                self.state = "COOLDOWN"
                self.reset_ui_styles()
                self.state_start_time = time.time()

        elif self.state == "WAIT_RELEASE":
            if status == 0 and plot_val > current_thresh:
                self.state = "PAUSED"
                self.current_pause_opt = 0 
                self.scan_start_time = time.time()
                self.pause_label.setText("VUOI USCIRE?")
                self.btn_riprendi.setStyleSheet(self.active_style)
                self.btn_esci.setStyleSheet(self.inactive_style)
                self.monitor.reset_monitor()

        elif self.state == "PAUSED":
            if not is_eye_constricted and not self.pending_selection:
                self.update_visual_scanning()

            if status == 1:
                self.pending_selection = "SHORT"
                self.set_ui_detected()

            elif not is_eye_constricted and self.pending_selection == "SHORT":
                self.pending_selection = None
                self.monitor.reset_monitor()

                if self.current_pause_opt == 0:
                    self.log_once("Resuming from pause")
                    self.toggle_pause_ui(False)
                    self.state = "COOLDOWN"
                    self.state_start_time = time.time()
                else:
                    self.log_once("Exit confirmed. Back to Main Menu")
                    self.go_back_signal.emit()
                    self.reset_to_initialization()

        elif self.state == "COOLDOWN": # Waits 2s for pupil recovery
            self.log_once("Cooldown started")
            self.reset_ui_styles()
            if time.time() - self.state_start_time >= self.t_cool:
                # Determine if we are coming from a Row Selection or a Button Click
                if self.next_state == "KEYBOARD_COL":
                    self.current_col_idx = -1 
                elif self.next_state == "KEYBOARD_ROW":
                    self.current_row_idx = -1
                    self.current_col_idx = -1
                
                self.state = self.next_state
                self.log_once(f"Moving to {self.state}")
                    
                self.loop_count = 0
                self.scan_start_time = time.time()

        if self.saver:
            self.saver.add_data(raw_area, plot_val, current_thresh, exit_thresh, status, frame_output)

        if self.plotter:
            self.plotter.add_data(plot_val, current_thresh, exit_thresh)

    def on_click(self, key):
        current = self.display.text()
        self.loop_count = 0

        if key == "CANC":
            self.log_once("Button clicked: CANC")
            self.display.setText(current[:-1])
            self.update_suggestions()
            self.next_state = "KEYBOARD_COL"
            self.current_col_idx = 0
        elif key == "FULL_CANC":
            self.log_once("Button clicked: CANC, FULL_CANC option --> word erased")
            if current.rfind(" ") != -1:
                self.display.setText(current[:current.rfind(" ")]) # delete the fully last word
            else:
                self.display.setText("")
            self.update_suggestions()
            self.next_state = "KEYBOARD_ROW"
        else:
            self.display.setText(current+key)
            self.log_once(f"Button clicked. Current text: {self.display.text()}")
            self.update_suggestions()
            self.next_state = "KEYBOARD_ROW"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = KeyboardApp()
    ex.show()
    sys.exit(app.exec_())