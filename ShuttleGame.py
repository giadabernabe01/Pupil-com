import os
import time
import random
import datetime
import numpy as np
import pygame
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QPushButton, QLabel, QMessageBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer

from DataProcessing import AreaFilter, ConstrictionMonitor
from HelperClasses import SessionLogger, DataPlotter, DataSaver

# ---------------------------------------------------------
# SPACE SHUTTLE GAME WIDGET
# ---------------------------------------------------------
class GameWidget(QWidget):
    go_back_signal = QtCore.pyqtSignal()

    def __init__(self, screen_width, screen_height, folder_name):
        super().__init__()
        
        # SENSOR & FILTER INITIALIZATION
        self.fps = 130
        self.thresh = 0.75
        self.filter = AreaFilter(fps=self.fps, device_type="gazepoint")
        self.monitor = ConstrictionMonitor(fps=self.fps, thresh=self.thresh, device_type="gazepoint")
        self.current_area = 0.0
        
        # LAYOUT SETUP
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(self.main_layout)

        # GENERAL PARAMETERS
        self.foldername = folder_name 
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # STATE FLAGS
        self.game_active = False 
        self.logger = None
        self.plotter = None
        self.saver = None

        self.reset_to_initialization()

    def start_session(self, folder_path, params, device_type):
        """Called by MainWindow to initialize logging and parameters for a new session."""
        self.foldername = folder_path
        self.logger = SessionLogger(self.foldername, "Shuttle Game")
        self.plotter = DataPlotter(self.foldername, "Space Shuttle")
        self.saver = DataSaver(self.foldername, "ShuttleGame")
        self.logger.log("Session Started: Game Widget")

        # PARAMETER RETRIEVAL
        self.params = params
        self.device_type = device_type
        
        constrict_config = self.params.get("constriction", {})
        self.short = constrict_config.get("short_constr_dur", 0.5)
        self.long = constrict_config.get("long_constr_dur", 3.0)
        
        game_config = self.params.get("game_widget", {})
        self.t_cool = game_config.get("cooldown_dur", 2.0)
        self.t_init = game_config.get("initialization_dur", 3.0)
        
        # GAME SPECIFIC PARAMS
        self.default_lives = game_config.get("lives", 5)
        self.default_shuttle_speed = game_config.get("shuttle_speed", 10)
        self.default_planet_speed = game_config.get("planet_speed_base", 2)

        active_fps = self.params.get("active_fps", 60) 
        threshold = self.params["constriction"].get("threshold", 0.75)

        self.filter = AreaFilter(fps=active_fps, device_type=self.device_type)
        self.monitor = ConstrictionMonitor(fps=active_fps, thresh=threshold, device_type=self.device_type, short_dur=self.short, long_dur=self.long)

        self.reset_to_initialization()

    def end_session(self):
        """Called by MainWindow to cleanup processes and save data."""
        self.game_active = False
        if hasattr(self, 'logger') and self.logger: 
            self.logger.log("Session Ended: Game Widget")
        if hasattr(self, 'plot') and self.plotter: 
            self.plot.save_plot()
        if hasattr(self, 'saver') and self.saver: 
            self.saver.save_file()

        if pygame.get_init():
            pygame.quit()

        self.logger = None
        self.plotter = None
        self.saver = None

    def trigger_cooldown(self):
        """Adds a delay before restarting to allow the user's eye to relax."""
        self.state = "COOLDOWN"
        self.state_start_time = time.time()
        self.clear_ui()
        
        msg = QtWidgets.QLabel("Preparazione nuova partita...")
        msg.setAlignment(QtCore.Qt.AlignCenter)
        msg.setStyleSheet("font-size: 24px; color: orange; font-weight: bold;")
        self.main_layout.addWidget(msg)
        
    def reset_game_state(self):
        """Resets all internal game mechanics and dynamic difficulty multipliers."""
        self.game_trigger = 0       
        self.frame_event_code = 0   
        self.start_time = 3 
        self.collision_flag = False
        self.timestamp = np.array([0])
        self.planet_list = ["nettuno.png", "urano.png", "saturno.png", "giove.png", "marte.png", "terra.png", "venere.png", "mercurio.png", "sole.png"]
        
        # DYNAMIC SPEEDS (Screen-size independent at 60 FPS)
        self.base_planet_speed = self.screen_width / (getattr(self, 'default_planet_speed', 5) * 60.0) 
        self.base_shuttle_speed = self.screen_height / (getattr(self, 'default_shuttle_speed', 1.5) * 60.0)
        
        self.planet_speed = self.base_planet_speed
        self.shuttle_speed = self.base_shuttle_speed
        self.asteroid_speed = self.base_planet_speed * 1.2 

        self.lives = getattr(self, 'default_lives', 5)
        self.psu_multiplier = 1 
        self.score = 0
        self.level = 0
        self.openflag = True
        
        # FEATURE FLAGS
        self.asteroid_flag = False
        self.asteroid_toggle = 0
        self.asteroid_probability = 10
        self.asteroid_active = False
        self.asteroid_togglevalues = []
        self.var_planet_start = False
        self.planet_start = 0
        self.var_asteroid_start = False
        self.asteroid_start = 0
        
        # SINE WAVE MOVEMENT DATA
        self.sinflag = False
        self.sinx = np.linspace(0, 2 * np.pi, 50)
        self.siny = 5 * np.sin(self.sinx)
        self.siny_ind_planet = 0
        
        self.exit_time = 4 
        self.check_exit_flag = False
    
    def update_game_area(self, area):
        """Slot to receive direct area updates."""
        self.current_area = area

    def show_timeout_dialog(self):
        """Pauses the UI and requests user intervention if tracking is lost."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Errore di Rilevamento")
        msg.setText("Il sistema non riesce a rilevare correttamente la pupilla.\nControlla l'inquadratura e clicca riprova.")
        
        btn_retry = msg.addButton("Riprova", QMessageBox.AcceptRole)
        msg.setStyleSheet("QLabel { color: white; font-size: 16px; } QPushButton { font-size: 16px; padding: 5px; }")
        
        msg.exec_()
        
        self.filter.reset()
        self.monitor.reset_monitor()
        self.state_start_time = time.time()

    def update_data(self, raw_area):
        """Main logical loop triggered by incoming frame data."""
        self.current_area = raw_area 

        # PERFORM MATH SYNCED WITH POLL TIMER
        self.filtered_val = self.filter.area_filtering(raw_area)

        if self.filter.timeout_triggered:
            self.show_timeout_dialog()
            return
        
        current_thresh = self.monitor.current_sma_thresh
        exit_thresh = self.monitor.exit_thresh
            
        status = self.monitor.constriction_detector(self.filtered_val)
        
        # MAKE TRIGGER STICKY FOR PYGAME 
        if status != 0:
            self.game_trigger = status

        # SAVE AND PLOT FOR ACCURATE TIME-SERIES
        if self.plotter: 
            self.plotter.add_data(self.filtered_val, current_thresh, exit_thresh)
            
        if self.saver: 
            event = getattr(self, 'frame_event_code', 0) if getattr(self, 'game_active', False) else "MENU"
            self.saver.add_data(raw_area, self.filtered_val, current_thresh, exit_thresh, status, event)
            
            if getattr(self, 'game_active', False) and event != 0:
                self.frame_event_code = 0 

        # EVENT ROUTING
        if getattr(self, 'game_active', False):
            # Pygame handles the logic internally while active
            return 
            
        # PRE-GAME MENU STATE MACHINE
        if self.state == "INITIALIZATION":
            self.monitor.baseline_collection(self.filtered_val)

            elapsed = time.time() - self.state_start_time
            remaining = self.t_init - elapsed
            if remaining > 0:
                self.info_label.setText(f"Acquisizione baseline... {remaining:.1f}s")

            if elapsed > self.t_init:
                self.state = "WAIT_INPUT"
                self.state_start_time = time.time()
                self.menu_scan_start_time = time.time()

                self.info_label.setText("GUARDA VICINO PER INIZIARE")
                self.info_label.setStyleSheet("font-size: 22px; color: green; font-weight: bold;")
                
                self.menu_scan_index = 0
                self.menu_buttons[0].setStyleSheet(self.active_btn_style)

                if self.logger: 
                    self.logger.log("Menu Ready. Waiting for launch trigger.")

        elif self.state == "WAIT_INPUT":
            elapsed_scan = time.time() - self.menu_scan_start_time
            if elapsed_scan >= 3.5: 
                self.menu_scan_start_time = time.time()
                self.menu_scan_index = 1 - self.menu_scan_index 
                
                for i, btn in enumerate(self.menu_buttons):
                    if i == self.menu_scan_index:
                        btn.setStyleSheet(self.active_btn_style)
                    else:
                        btn.setStyleSheet(self.inactive_btn_style)

            # ANY CONSTRICTION SELECTS HIGHLIGHTED OPTION
            if status == 1 or status == 2: 
                if self.logger: 
                    self.logger.log(f"Menu Selection: Option {self.menu_scan_index}")
                
                self.state = "STARTING"
                
                if self.menu_scan_index == 0:
                    print("Game start triggered via visual scan")
                    QtCore.QTimer.singleShot(0, self.start_game)
                elif self.menu_scan_index == 1:
                    print("Exit triggered via visual scan")
                    self.go_back_signal.emit()
                return
        
        elif self.state == "COOLDOWN":
            if time.time() - self.state_start_time > self.t_cool:
                self.reset_to_initialization()

        elif self.state == "WAIT_EXIT":
            if time.time() - self.state_start_time >= 5:
                if self.logger: 
                    self.logger.log("Back to game lobby")
                self.trigger_cooldown()

    def clear_ui(self):
        """Completely removes all widgets from the main layout."""
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        QApplication.processEvents()
    
    def save_array(self, array, filename):
        self.filepath = os.path.join(self.foldername, filename)
        np.savetxt(self.filepath, array)

    def reset_to_initialization(self):
        """Resets the UI to the Start Screen."""
        self.state = "RESETTING"
        self.reset_game_state()

        self.monitor.reset_monitor()
        if hasattr(self.monitor, 'baseline_buffer'):
            self.monitor.baseline_buffer.clear()

        self.game_active = False 
        self.clear_ui()

        welcome = QtWidgets.QLabel(
            "Benvenuto in SPACE SHUTTLE\n\n"
            "Guida la navicella\n"
            "per visitare tutti i pianeti!\n"
            "Guarda vicino quando vuoi \nfar"
            " decollare l'astronave."
        )
        welcome.setAlignment(QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(welcome)
        
        self.info_label = QtWidgets.QLabel("Inizializzazione...")
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 20px; color: orange; font-weight: bold;")
        self.main_layout.addWidget(self.info_label)

        self.start_button = QtWidgets.QPushButton("Inizia il gioco")
        self.start_button.clicked.connect(self.start_game)
        self.main_layout.addWidget(self.start_button)
        
        self.back_btn = QtWidgets.QPushButton("Indietro")
        self.back_btn.clicked.connect(self.go_back_signal.emit)
        self.main_layout.addWidget(self.back_btn)

        self.menu_buttons = [self.start_button, self.back_btn]
        self.menu_scan_index = 0

        self.active_btn_style = "background-color: #0078d7; color: white; font-size: 24px; font-weight: bold; border: 3px solid white; border-radius: 10px; padding: 15px;"
        self.inactive_btn_style = "background-color: #444; color: #ccc; font-size: 22px; font-weight: bold; border-radius: 10px; padding: 15px;"
        
        for btn in self.menu_buttons:
            btn.setStyleSheet(self.inactive_btn_style)
        
        self.state_start_time = time.time()
        self.state = "INITIALIZATION"
        
    def collision_check(self):
        """Validates positions to determine if a score, life gain, or crash occurred."""
        # PLANET COLLISION
        if not self.collision_flag and self.y_planet <= (self.y_shuttle + self.shuttle_height) <= (self.y_planet + self.planet_size) or self.y_shuttle <= (self.y_planet + self.planet_size) <= (self.y_shuttle + self.shuttle_height):
            if self.x_planet <= self.x_shuttle <= self.x_planet + self.planet_size or self.x_shuttle <= self.x_planet <= self.x_shuttle + self.shuttle_width:
                self.score += 1
                pygame.mixer.Channel(0).play(self.score_sound)

                self.collision_flag = True
                self.frame_event_code = "SCORE"
                
                if self.score % 5 == 0:
                    self.lives += 1
                    pygame.mixer.Channel(0).play(self.lifegain_sound)
                    self.frame_event_code = "LIFE_GAIN"

        # ASTEROID COLLISION
        if self.asteroid_flag:
            if not self.collision_flag and self.y_asteroid <= (self.y_shuttle + self.shuttle_height) <= (self.y_asteroid + self.asteroid_size) or self.y_shuttle <= (self.y_asteroid + self.asteroid_size) <= (self.y_shuttle + self.shuttle_height):
                if self.x_asteroid <= self.x_shuttle <= self.x_asteroid + self.asteroid_size or self.x_shuttle <= self.x_asteroid <= self.x_shuttle + self.shuttle_width:
                    self.lives -= 1
                    self.collision_flag = True
                    self.frame_event_code = "COLLISION_ASTEROID"
                    pygame.mixer.Channel(0).play(self.lifelost_sound)

        # MISSED PLANET CHECK
        if not self.collision_flag:
            if self.x_planet + self.planet_size < 0 or self.x_planet > self.screen_width:
                self.lives -= 1
                self.collision_flag = True
                self.frame_event_code = "MISSED_PLANET"
                pygame.mixer.Channel(0).play(self.lifelost_sound)

    def start_game(self):
        """Initializes Pygame environment and runs the core game loop."""
        if self.logger: 
            self.logger.log("Initialising Pygame...")

        self.reset_game_state()
        self.openflag = True
        self.monitor.reset_monitor()

        base_path = os.path.dirname(os.path.abspath(__file__))
        sound_dir = os.path.join(base_path, "Sounds")
        image_dir = os.path.join(base_path, "Images")

        pygame.init()
        self.game_active = True
        pygame.font.init()
        pygame.mixer.init()
        pygame.mixer.set_num_channels(1)
        self.clock = pygame.time.Clock()

        try:
            self.score_sound = pygame.mixer.Sound(os.path.join(sound_dir, 'pop.mp3'))
            self.lifelost_sound = pygame.mixer.Sound(os.path.join(sound_dir, 'no_sound.mp3'))
            self.lifegain_sound = pygame.mixer.Sound(os.path.join(sound_dir, 'yes_sound.mp3'))
        except:
            print("Warning: Audio files not found")
            self.score_sound = pygame.mixer.Sound(buffer=bytearray())
            self.lifelost_sound = pygame.mixer.Sound(buffer=bytearray())
            self.lifegain_sound = pygame.mixer.Sound(buffer=bytearray())

        window_width, window_height = self.screen_width, self.screen_height
        window = pygame.display.set_mode((window_width, window_height))

        target_center_x = window_width // 2
        target_center_y = window_height // 2

        button_text = "Esci"
        font = pygame.font.SysFont("Calibri", 25)
        button_text_surface = font.render(button_text, True, (0,0,0))
        button_text_rect = button_text_surface.get_rect()
        button_text_rect.center = (window_width - 25, 25)
        button_width = 60
        button_height = 50
        button_rect = pygame.Rect(window_width - 65, 10, button_width, button_height)
        button_color = (244,138,148)
        button_radius = 10 

        score_surface = font.render("Pianeti visitati: " + str(self.score) + " - Livello: " + str(self.level + 1), True, (0,0,0))
        score_surface_rect = score_surface.get_rect()
        score_surface_rect.center = (window_width/2, 25)
        score_rect = pygame.Rect(window_width/2 - 200, 10, 400, button_height)
        score_rect_color = (255,247,210)
        score_rect_radius = 10 

        # LOAD IMAGES
        try:
            starrysky = pygame.image.load(os.path.join(image_dir,'starrysky_red.jpg'))
            window.blit(starrysky, (0,0))

            shuttle = pygame.image.load(os.path.join(image_dir,"shuttle.png")).convert_alpha()
            self.shuttle_width = 45
            self.shuttle_height = 90
            shuttle = pygame.transform.scale(shuttle, (self.shuttle_width,self.shuttle_height))

            self.y_shuttle_base = window_height - self.shuttle_height - 50
            self.x_shuttle = window_width // 2 - int(self.shuttle_width/2)
            self.y_shuttle = self.y_shuttle_base

            self.planet_counter = 0
            planet = pygame.image.load(os.path.join(image_dir, self.planet_list[self.planet_counter])).convert_alpha()
            self.planet_size = 70
            planet = pygame.transform.scale(planet, (self.planet_size,self.planet_size))
            self.x_planet = window_width - self.planet_size
            self.y_planet_limit = self.y_shuttle_base - self.shuttle_height
            self.y_planet = random.randint(2*button_height, self.y_planet_limit)

            self.asteroid_size = int(self.planet_size + self.planet_size/2)
            asteroid = pygame.image.load(os.path.join(image_dir,"asteroide.png")).convert_alpha()
            asteroid = pygame.transform.scale(asteroid, (self.asteroid_size,self.asteroid_size))
            self.x_asteroid = window_width - self.asteroid_size
            self.y_asteroid_limit = window_height//2 - self.asteroid_size
            
            life = pygame.image.load(os.path.join(image_dir, 'heart.png'))
            life = pygame.transform.scale(life, (self.shuttle_width, self.shuttle_width))
        except Exception as e:
            print(f"Error loading images from {image_dir}: {e}")
            self.game_active = False
            pygame.quit()
            return

        self.shuttlebuffer = window.subsurface(pygame.Rect(
            self.x_shuttle, self.y_shuttle,
            self.shuttle_width, self.shuttle_height)).copy()          

        self.planetbuffer = window.subsurface(pygame.Rect(
            self.x_planet - int(self.planet_size), self.y_planet - int(self.planet_size), 
            self.planet_size, self.planet_size)).copy()

        t_start = datetime.datetime.now()
        self.text_font = pygame.font.Font(None, 72)
        
        # INTRO ANIMATION LOOP
        while (datetime.datetime.now() - t_start).total_seconds() < self.start_time:
            self.clock.tick(60)
            QApplication.processEvents()
            window.blit(starrysky, (0,0))
            window.blit(shuttle, (self.x_shuttle, self.y_shuttle))

            if 0 < (datetime.datetime.now()-t_start).total_seconds() < self.start_time/2:
                first_text_surface = self.text_font.render("Pronto?", True, (255,219,88))
            else:
                first_text_surface = self.text_font.render("Via!", True, (255,219,88))

            first_text_surface_rect = first_text_surface.get_rect()
            first_text_surface_rect.center = (window_width/2, window_height/2)
            window.blit(first_text_surface, first_text_surface_rect)
            pygame.display.flip()
        
        t_start = datetime.datetime.now()
        frame_counter = 0
        self.game_trigger = 0 
        self.monitor.reset_monitor()

        # MAIN GAME LOOP
        while self.lives > 0 and self.openflag and self.game_active:
            self.clock.tick(60)
            window.fill((255,255,255))        
            window.blit(starrysky, (0,0))

            for i in range(int(self.lives)): 
                window.blit(life, (window_width// 4 + i*self.shuttle_width, button_height + 10))

            pygame.draw.circle(window, (255, 0, 0), (target_center_x, target_center_y), 5)
            pygame.draw.rect(window, button_color, button_rect, border_radius=button_radius)
            pygame.draw.rect(window, score_rect_color, score_rect, border_radius=score_rect_radius)
        
            text_x = button_rect.centerx - button_text_surface.get_width() / 2
            text_y = button_rect.centery - button_text_surface.get_height() / 2
            score_x = score_rect.centerx - score_surface.get_width() / 2
            score_y = score_rect.centery - score_surface.get_height() / 2
            
            window.blit(button_text_surface, (text_x, text_y))
            window.blit(score_surface, (score_x, score_y))

            # DIFFICULTY SCALING
            self.level = int(self.score / 5)
            
            speed_multiplier = 1.0 + (self.level * 0.15)
            self.planet_speed = self.base_planet_speed * speed_multiplier
            self.asteroid_speed = (self.base_planet_speed * 1.2) * speed_multiplier
            
            # DYNAMIC OBSTACLE LOGIC
            if self.level >= 2 and not self.asteroid_flag:
                self.asteroid_active = True
                self.asteroid_togglevalues = [5,7]
            if self.level >= 4: 
                self.var_planet_start = True                
            if self.level >= 5 and not self.asteroid_flag:                
                self.asteroid_toggle = random.randint(0,self.asteroid_probability)
                self.asteroid_togglevalues = [2,5,7]
            if self.level == 7:
                self.asteroid_togglevalues = [2,5,7,9]
            if self.level >= 8: 
                self.sinflag = True
            if self.level >= 9: 
                self.var_asteroid_start = True
            if self.level >= 10: 
                self.asteroid_togglevalues = [1,2,5,7,8,9]
            if self.level >= 11:
                if not self.asteroid_flag:
                    self.asteroid_size = random.choice([i for i in range(self.planet_size - 20, self.planet_size +21, 10)]) 
            if self.level >= 12: 
                self.asteroid_togglevalues = [1,2,3,4,5,6,7,8,9]
            
            if self.score % 15 == 0 and self.score > 0 and not self.asteroid_flag:
                self.asteroid_toggle = random.randint(0,self.asteroid_probability)
                if self.asteroid_probability / 2 >= 5:
                    self.asteroid_probability = int(self.asteroid_probability / 2)
                    if self.asteroid_toggle in [2,5]:
                        self.asteroid_flag = True
                        self.y_asteroid = random.randint(2*button_height, self.y_asteroid_limit)
                else:
                    if self.asteroid_toggle in [2,5,7]:
                        self.asteroid_flag = True
                        self.y_asteroid = random.randint(2*button_height, self.y_asteroid_limit)

            # MOVEMENT UPDATES
            if self.var_planet_start:
                if self.planet_start == 0: self.planet_speed = abs(self.planet_speed)
                else: self.planet_speed = -abs(self.planet_speed)
            
            self.x_planet -= self.planet_speed

            if self.sinflag:
                self.y_planet += self.siny[self.siny_ind_planet]
                self.siny_ind_planet += 1
                if self.siny_ind_planet >= len(self.siny):
                    self.siny_ind_planet = 0

            if self.asteroid_flag:
                if self.var_asteroid_start:
                    if self.asteroid_start == 0: self.asteroid_speed = abs(self.asteroid_speed)
                    else: self.asteroid_speed = -abs(self.asteroid_speed)
                self.x_asteroid -= self.asteroid_speed
                if self.x_asteroid < -self.asteroid_size: 
                    self.asteroid_flag = False
                            
            window.blit(shuttle, (self.x_shuttle, self.y_shuttle))
            window.blit(planet, (self.x_planet, self.y_planet))
            if self.asteroid_flag:
                window.blit(asteroid, (self.x_asteroid, self.y_asteroid))

            score_surface = font.render("Pianeti visitati: " + str(self.score) + " - Livello: " + str(self.level + 1), True, (0,0,0))

            t_now = datetime.datetime.now()
            frame_counter += 1
            fps_temp = int(np.round(frame_counter/(t_now-t_start).total_seconds()))
            self.timestamp = np.append(self.timestamp,(t_now-t_start).total_seconds())

            # TRIGGER UPDATE_DATA LOGIC
            QApplication.processEvents()

            # PYGAME INPUT HANDLING
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.openflag = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if button_rect.collidepoint(event.pos):
                        print("Pulsante Esci premuto")
                        self.openflag = False
                        break

            current_thresh = self.monitor.current_sma_thresh if self.monitor.baseline_buffer else 0

            # PAUSE MENU TRIGGER LOGIC
            if self.game_trigger == 2:
                self.game_trigger = 0 
                
                if self.logger: 
                    self.logger.log("Pause triggered")
                self.frame_event_code = "PAUSE_TRIGGER"
                
                paused = True
                scan_start_time = time.time()
                pause_option = 0 
                
                overlay = pygame.Surface((window_width, window_height))
                overlay.set_alpha(200) 
                overlay.fill((20,20,40))

                while self.current_area < current_thresh and self.openflag:
                    self.clock.tick(60)
                    QApplication.processEvents() 
                    
                    window.blit(overlay, (0,0))
                    wait_text = self.text_font.render("RILASCIA PER PAUSA", True, (255, 255, 0))
                    wait_rect = wait_text.get_rect(center=(window_width//2, window_height//2))
                    window.blit(wait_text, wait_rect)
                    pygame.display.flip()
                
                self.monitor.reset_monitor()
                self.game_trigger = 0 
                pause_menu_start = time.time()

                while paused and self.openflag:
                    self.clock.tick(60)
                    elapsed = time.time() - scan_start_time
                    if elapsed >= 3.5:
                        scan_start_time = time.time()
                        pause_option = 1 - pause_option

                    window.blit(overlay, (0,0))
                    
                    title_surf = self.text_font.render("PAUSA", True, (255, 255, 255))
                    title_rect = title_surf.get_rect(center=(window_width//2, window_height//2 - 100))
                    window.blit(title_surf, title_rect)
                    
                    opts = ["RIPRENDI", "ESCI"]
                    for i, opt in enumerate(opts):
                        if i == pause_option:
                            color = (0, 120, 215) 
                            text = f">> {opt} <<"
                            bg_rect = pygame.Rect(0, 0, 300, 60)
                            bg_rect.center = (window_width//2, window_height//2 + i*80)
                            pygame.draw.rect(window, color, bg_rect, border_radius=10)
                            text_color = (255,255,255)
                        else:
                            text = opt
                            text_color = (150, 150, 150)
                        
                        opt_surf = font.render(text, True, text_color)
                        opt_rect = opt_surf.get_rect(center=(window_width//2, window_height//2 + i*80))
                        window.blit(opt_surf, opt_rect)
                    
                    instr_text = "Guarda vicino per scegliere l'opzione illuminata"
                    instr_surf = font.render(instr_text, True, (200, 200, 200))
                    window.blit(instr_surf, (window_width//2 - instr_surf.get_width()//2, window_height - 100))
                    
                    pygame.display.flip()
                    QApplication.processEvents() 
                    
                    if self.game_trigger == 1:
                        self.game_trigger = 0 
                        if time.time() - pause_menu_start > 1.5: 
                            if pause_option == 0: 
                                paused = False
                                pygame.mixer.Channel(0).play(self.lifegain_sound)
                            else: 
                                paused = False
                                self.openflag = False
                                print("Uscita confermata")
                    
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.openflag = False
                            paused = False
                
                self.monitor.reset_monitor()
                self.game_trigger = 0

            # LAUNCH TRIGGER LOGIC
            if self.game_trigger == 1:
                self.game_trigger = 0 
                
                if self.logger: 
                    self.logger.log("Constriction detected: launch triggered")
                if self.plotter: 
                    self.plotter.mark_constriction("short")
                
                self.frame_event_code = "LAUNCH"
                self.launch_shuttle_step = self.shuttle_speed 
                self.launch_planet_step = self.planet_speed
                print("Decollo iniziato")

                # LAUNCH ANIMATION LOOP
                while self.y_shuttle > button_height and not self.collision_flag:
                    self.clock.tick(60)
                    QApplication.processEvents() 

                    for event in pygame.event.get():
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            if button_rect.collidepoint(event.pos):
                                print("Pulsante Esci premuto in volo")
                                self.openflag = False
                                break
                    
                    if not self.openflag: 
                        break 

                    # IN-FLIGHT PAUSE LOGIC
                    if self.game_trigger == 2:
                        self.game_trigger = 0 
                        if self.logger: 
                            self.logger.log("Game Interrupted during flight")
                        print("Gioco interrotto durante il volo")

                        paused = True
                        scan_start_time = time.time()
                        pause_option = 0 
                        
                        overlay = pygame.Surface((window_width, window_height))
                        overlay.set_alpha(200) 
                        overlay.fill((20,20,40))

                        while self.current_area < current_thresh and self.openflag:
                            self.clock.tick(60)
                            QApplication.processEvents()
                            
                            window.blit(overlay, (0,0))
                            wait_text = self.text_font.render("RILASCIA PER PAUSA", True, (255, 255, 0))
                            wait_rect = wait_text.get_rect(center=(window_width//2, window_height//2))
                            window.blit(wait_text, wait_rect)
                            pygame.display.flip()
                        
                        self.monitor.reset_monitor()
                        self.game_trigger = 0
                        pause_menu_start = time.time()

                        while paused and self.openflag:
                            self.clock.tick(60)
                            elapsed = time.time() - scan_start_time
                            if elapsed >= 3.5:
                                scan_start_time = time.time()
                                pause_option = 1 - pause_option

                            window.blit(overlay, (0,0))
                            
                            title_surf = self.text_font.render("PAUSA", True, (255, 255, 255))
                            title_rect = title_surf.get_rect(center=(window_width//2, window_height//2 - 100))
                            window.blit(title_surf, title_rect)
                            
                            opts = ["RIPRENDI", "ESCI"]
                            for i, opt in enumerate(opts):
                                if i == pause_option:
                                    color = (0, 120, 215) 
                                    text = f">> {opt} <<"
                                    bg_rect = pygame.Rect(0, 0, 300, 60)
                                    bg_rect.center = (window_width//2, window_height//2 + i*80)
                                    pygame.draw.rect(window, color, bg_rect, border_radius=10)
                                    text_color = (255,255,255)
                                else:
                                    text = opt
                                    text_color = (150, 150, 150)
                                
                                opt_surf = font.render(text, True, text_color)
                                opt_rect = opt_surf.get_rect(center=(window_width//2, window_height//2 + i*80))
                                window.blit(opt_surf, opt_rect)
                            
                            instr_text = "Guarda vicino per scegliere l'opzione illuminata"
                            instr_surf = font.render(instr_text, True, (200, 200, 200))
                            window.blit(instr_surf, (window_width//2 - instr_surf.get_width()//2, window_height - 100))
                            
                            pygame.display.flip()
                            QApplication.processEvents()
                            
                            if self.game_trigger == 1:
                                self.game_trigger = 0
                                if time.time() - pause_menu_start > 1.5:
                                    if pause_option == 0: 
                                        paused = False
                                        pygame.mixer.Channel(0).play(self.lifegain_sound)
                                    else: 
                                        paused = False
                                        self.openflag = False
                                        print("Uscita confermata")
                            
                            for event in pygame.event.get():
                                if event.type == pygame.QUIT:
                                    self.openflag = False
                                    paused = False
                        
                        self.monitor.reset_monitor()
                        self.game_trigger = 0
                        break

                    self.y_shuttle -= self.launch_shuttle_step 
                    self.x_planet -= self.launch_planet_step   
                    
                    if self.var_planet_start:
                        if self.planet_start == 0: self.planet_speed = abs(self.planet_speed)
                        else: self.planet_speed = -abs(self.planet_speed)

                    if self.sinflag:
                        self.y_planet += self.siny[self.siny_ind_planet]
                        self.siny_ind_planet = (self.siny_ind_planet + 1) % len(self.siny)

                    if self.asteroid_flag: 
                        self.x_asteroid -= self.asteroid_speed
                        if self.x_asteroid < -self.asteroid_size:
                            self.asteroid_flag = False

                    window.blit(starrysky, (0,0)) 

                    if self.y_shuttle > button_height + self.shuttle_height:
                        self.shuttlebuffer = window.subsurface(pygame.Rect(
                        self.x_shuttle, self.y_shuttle,
                        self.shuttle_width, self.shuttle_height)).copy()
                    
                    window.blit(shuttle, (self.x_shuttle, self.y_shuttle))
                    window.blit(planet, (self.x_planet, self.y_planet))
                    if self.asteroid_flag:
                        window.blit(asteroid, (self.x_asteroid, self.y_asteroid))
                    
                    for i in range(self.lives): 
                        window.blit(life, (window_width// 4 + i*self.shuttle_width, button_height + 10))
                    pygame.draw.rect(window, button_color, button_rect, border_radius=button_radius)
                    pygame.draw.rect(window, score_rect_color, score_rect, border_radius=score_rect_radius)
                    window.blit(button_text_surface, (text_x, text_y))
                    window.blit(score_surface, (score_x, score_y))

                    pygame.display.flip()

                    self.collision_check()
                    
                    if self.collision_flag:
                        if self.lives > 0:
                            # RESET IN-FLIGHT OBSTACLES
                            planet_ind = random.randint(0, len(self.planet_list) -1)
                            planet = pygame.image.load(os.path.join(image_dir, self.planet_list[planet_ind])).convert_alpha()
                            if self.planet_list[planet_ind] == "urano.png":
                                planet = pygame.transform.scale(planet, (int(self.planet_size*250/360),self.planet_size))
                            else:
                                planet = pygame.transform.scale(planet, (self.planet_size,self.planet_size))
                            
                            self.x_planet = window_width - self.planet_size
                            self.y_planet = random.randint(2*button_height, self.y_planet_limit)
                            self.asteroid_flag = False 
                        else:
                            self.openflag = False  

                        self.collision_flag = False 
                        if self.y_shuttle < self.y_shuttle_base:
                            break   
                    
                self.y_shuttle = self.y_shuttle_base

            # OUTER LOOP IDLE COLLISION CHECK
            self.collision_check()

            if self.collision_flag:
                if self.lives > 0:
                    if self.logger : 
                        self.logger.log("Collision detected")
                        
                    planet_ind = random.randint(0, len(self.planet_list) -1)
                    planet = pygame.image.load(os.path.join(image_dir, self.planet_list[planet_ind])).convert_alpha()
                    if self.planet_list[planet_ind] == "urano.png":
                        planet = pygame.transform.scale(planet, (int(self.planet_size*250/360),self.planet_size))
                    else:
                        planet = pygame.transform.scale(planet, (self.planet_size,self.planet_size))
                    
                    self.x_planet = window_width - self.planet_size
                    self.y_planet = random.randint(2*button_height, self.y_planet_limit)
                    self.asteroid_flag = False
                else:
                    self.openflag = False 

                self.collision_flag = False
                
            pygame.display.flip()

        pygame.quit()
        print("Gioco concluso") 

        if self.logger: 
            self.logger.log(f"Game Over")
            
        self.end_game()
        self.game_active = False

    def end_game(self):
        """Processes final score evaluations, saves logs, and displays Game Over screen."""
        print("Game Ending")

        self.clear_ui()

        if self.plotter:
            self.plotter.save_plot()
            self.plotter = DataPlotter(self.foldername, f"Space Shuttle_{int(time.time())}")

        # BUILD GAME OVER UI
        self.state_start_time = time.time()
        welcome_message = QLabel("CONGRATULAZIONI!", self)
        welcome_message.setFont(QFont("Calibri", 30, weight=QFont.Bold))
        welcome_message.setAlignment(Qt.AlignCenter)
        welcome_message.setStyleSheet("color: white;")

        if self.score == 1:
            explanation_text = "Hai visitato 1 pianeta\n arrivando al livello 1 del gioco!\n"
        else:
            explanation_text = "Hai visitato " + str(self.score) + " pianeti\n arrivando al livello " + str(self.level + 1) + " del gioco!\n"

        scores_path = os.path.join(self.foldername, "Punteggi.txt")
        
        if not os.path.exists(scores_path):
            with open(scores_path, 'w') as f: 
                f.write("0")

        with open(scores_path, 'r') as file:
            scores_file = file.read()
            scores = scores_file.split()
            previous_scores = np.array(scores, dtype=int)

        if len(previous_scores) >= 3:
            top_scores = np.sort(np.partition(previous_scores, -3)[-3:])[::-1]
        else:
            top_scores = np.sort(previous_scores)[::-1]

        if len(top_scores) > 0 and self.score > top_scores[-1]:
            explanation_text += "Hai fatto un nuovo record!\n"
            top_scores = np.append(top_scores, self.score)
            top_scores = np.sort(top_scores)[::-1][:3]
        
        with open(scores_path, 'a') as file:
            file.write("\n" + str(self.score))

        explanation_text += "I tuoi punteggi migliori: " + str(top_scores)
        
        explanation_message = QLabel(explanation_text, self)
        explanation_message.setFont(QFont("Calibri", 20))
        explanation_message.setAlignment(Qt.AlignCenter)        
        explanation_message.setStyleSheet("color: white;")

        self.main_layout.addWidget(welcome_message)
        self.main_layout.addSpacing(25)
        self.main_layout.addWidget(explanation_message)
        
        # EXIT LOOP TRIGGER
        self.monitor.reset_monitor()
        self.state = "WAIT_EXIT"
        if self.logger: 
            self.logger.log("Waiting for exit gesture in Game Over screen")
