"""Space Evaders launcher widget: PAR short -> UDP press into Unity."""

import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

from DataProcessing import AreaFilter, ConstrictionMonitor
from HelperClasses import SessionLogger, DataPlotter, DataSaver
from UnityGameBridge import UnityGameBridge


class UnityGameWidget(QWidget):
    go_back_signal = QtCore.pyqtSignal()

    def __init__(self, screen_width, screen_height, folder_name):
        super().__init__()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.foldername = folder_name

        self.fps = 130
        self.thresh = 0.75
        self.filter = AreaFilter(fps=self.fps, device_type="gazepoint")
        self.monitor = ConstrictionMonitor(
            fps=self.fps, thresh=self.thresh, device_type="gazepoint"
        )
        self.current_area = 0.0

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(self.main_layout)

        self.game_active = False
        self.logger = None
        self.plotter = None
        self.saver = None
        self.bridge = None
        self.params = {}
        self.device_type = "gazepoint"
        self.frame_event_code = 0

        self.reset_to_initialization()

    def start_session(self, folder_path, params, device_type):
        self.foldername = folder_path
        self.logger = SessionLogger(self.foldername, "Space Evaders")
        self.plotter = DataPlotter(self.foldername, "Space Evaders")
        self.saver = DataSaver(self.foldername, "UnityGame")
        self.logger.log("Session Started: Unity Game Widget")

        self.params = params
        self.device_type = device_type

        constrict_config = self.params.get("constriction", {})
        self.short = constrict_config.get("short_constr_dur", 0.5)
        self.long = constrict_config.get("long_constr_dur", 3.0)

        game_config = self.params.get("unity_game", {})
        # reuse shuttle-like timings if unity block omits them
        fallback = self.params.get("game_widget", {})
        self.t_cool = game_config.get("cooldown_dur", fallback.get("cooldown_dur", 2.0))
        self.t_init = game_config.get(
            "initialization_dur", fallback.get("initialization_dur", 3.0)
        )
        self.menu_scan_interval = game_config.get("scan_interval_dur", 3.5)

        active_fps = self.params.get("active_fps", 60)
        threshold = self.params["constriction"].get("threshold", 0.75)

        self.filter = AreaFilter(fps=active_fps, device_type=self.device_type)
        self.monitor = ConstrictionMonitor(
            fps=active_fps,
            thresh=threshold,
            device_type=self.device_type,
            short_dur=self.short,
            long_dur=self.long,
        )

        self.bridge = UnityGameBridge(
            host=game_config.get("udp_host", "127.0.0.1"),
            port=game_config.get("udp_port", 47890),
            exe_path=game_config.get("exe_path", ""),
            startup_delay=game_config.get("startup_delay", 2.0),
        )

        self.reset_to_initialization()

    def end_session(self):
        self.game_active = False
        if self.bridge:
            self.bridge.close()
            self.bridge = None

        if self.logger:
            self.logger.log("Session Ended: Unity Game Widget")
        if self.plotter:
            self.plotter.save_plot()
        if self.saver:
            self.saver.save_file()

        self.logger = None
        self.plotter = None
        self.saver = None

    def clear_ui(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        QApplication.processEvents()

    def reset_to_initialization(self):
        self.state = "RESETTING"
        self.game_active = False
        self.frame_event_code = 0
        self.monitor.reset_monitor()
        if hasattr(self.monitor, "baseline_buffer"):
            self.monitor.baseline_buffer.clear()

        self.clear_ui()

        welcome = QtWidgets.QLabel(
            "SPACE EVADERS (Unity)\n\n"
            "PAR breve = azione nel gioco\n"
            "(scudo / salvataggio / colpo).\n\n"
            "Assicurati che l'exe sia configurata\n"
            "in parameters.json → unity_game.exe_path"
        )
        welcome.setAlignment(QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(welcome)

        self.info_label = QtWidgets.QLabel("Inizializzazione...")
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_label.setStyleSheet(
            "font-size: 20px; color: orange; font-weight: bold;"
        )
        self.main_layout.addWidget(self.info_label)

        self.start_button = QtWidgets.QPushButton("Avvia Space Evaders")
        self.start_button.clicked.connect(self.start_game)
        self.main_layout.addWidget(self.start_button)

        self.back_btn = QtWidgets.QPushButton("Indietro")
        self.back_btn.clicked.connect(self._request_exit)
        self.main_layout.addWidget(self.back_btn)

        self.menu_buttons = [self.start_button, self.back_btn]
        self.menu_scan_index = 0
        self.active_btn_style = (
            "background-color: #0078d7; color: white; font-size: 24px; "
            "font-weight: bold; border: 3px solid white; border-radius: 10px; padding: 15px;"
        )
        self.inactive_btn_style = (
            "background-color: #444; color: #ccc; font-size: 22px; "
            "font-weight: bold; border-radius: 10px; padding: 15px;"
        )
        for btn in self.menu_buttons:
            btn.setStyleSheet(self.inactive_btn_style)

        self.state_start_time = time.time()
        self.menu_scan_start_time = time.time()
        self.state = "INITIALIZATION"

    def _request_exit(self):
        self.end_session()
        self.go_back_signal.emit()

    def show_timeout_dialog(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Errore di Rilevamento")
        msg.setText(
            "Il sistema non riesce a rilevare correttamente la pupilla.\n"
            "Controlla l'inquadratura e clicca riprova."
        )
        msg.addButton("Riprova", QMessageBox.AcceptRole)
        msg.setStyleSheet(
            "QLabel { color: white; font-size: 16px; } "
            "QPushButton { font-size: 16px; padding: 5px; }"
        )
        msg.exec_()
        self.filter.reset()
        self.monitor.reset_monitor()
        self.state_start_time = time.time()

    def start_game(self):
        if not self.bridge:
            QMessageBox.critical(self, "Errore", "Bridge Unity non inizializzato.")
            return

        try:
            self.info_label.setText("Avvio Unity...")
            QApplication.processEvents()
            self.bridge.start_unity()
        except Exception as e:
            if self.logger:
                self.logger.log(f"Unity launch failed: {e}")
            QMessageBox.critical(
                self,
                "Unity non avviata",
                f"Impossibile avviare Space Evaders:\n{e}\n\n"
                "Controlla unity_game.exe_path in parameters.json.",
            )
            return

        self.game_active = True
        self.frame_event_code = 0
        self.clear_ui()

        self.info_label = QtWidgets.QLabel(
            "Partita attiva\n\nPAR breve = azione in Unity\n"
            "Chiudi il gioco o premi Esci per tornare al menù."
        )
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_label.setStyleSheet(
            "font-size: 22px; color: #7CFC00; font-weight: bold;"
        )
        self.main_layout.addWidget(self.info_label)

        self.status_label = QtWidgets.QLabel("In attesa di PAR...")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 18px; color: #ccc;")
        self.main_layout.addWidget(self.status_label)

        exit_btn = QtWidgets.QPushButton("Esci e chiudi Unity")
        exit_btn.clicked.connect(self._request_exit)
        exit_btn.setStyleSheet(
            "background-color: #444; color: #ccc; font-size: 20px; "
            "font-weight: bold; border-radius: 10px; padding: 12px;"
        )
        self.main_layout.addWidget(exit_btn)

        if self.logger:
            self.logger.log("Unity started; waiting for short PAR")

    def update_data(self, raw_area):
        self.current_area = raw_area
        self.filtered_val = self.filter.area_filtering(raw_area)

        if self.filter.timeout_triggered:
            self.show_timeout_dialog()
            return

        current_thresh = self.monitor.current_sma_thresh
        exit_thresh = self.monitor.exit_thresh
        status = self.monitor.constriction_detector(self.filtered_val)

        if self.plotter:
            self.plotter.add_data(self.filtered_val, current_thresh, exit_thresh)

        if self.saver:
            event = (
                getattr(self, "frame_event_code", 0)
                if self.game_active
                else "MENU"
            )
            self.saver.add_data(
                raw_area,
                self.filtered_val,
                current_thresh,
                exit_thresh,
                status,
                event,
            )
            if self.game_active and event != 0:
                self.frame_event_code = 0

        # --- In-game: forward short PAR to Unity ---
        if self.game_active:
            if self.bridge and not self.bridge.is_running():
                if self.logger:
                    self.logger.log("Unity process ended")
                self.end_session()
                self.go_back_signal.emit()
                return

            if status == 1:
                self.frame_event_code = "UNITY_PRESS"
                if self.plotter:
                    self.plotter.mark_constriction("short")
                if self.bridge:
                    self.bridge.send_press()
                if self.logger:
                    self.logger.log("Short PAR -> Unity UDP press")
                if hasattr(self, "status_label") and self.status_label:
                    self.status_label.setText(
                        f"PAR inviato a Unity ({time.strftime('%H:%M:%S')})"
                    )
            # status == 2 reserved for future pause
            return

        # --- Pre-game menu (same idea as Shuttle) ---
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
                self.info_label.setText("GUARDA VICINO PER SELEZIONARE")
                self.info_label.setStyleSheet(
                    "font-size: 22px; color: green; font-weight: bold;"
                )
                self.menu_scan_index = 0
                self.menu_buttons[0].setStyleSheet(self.active_btn_style)
                if self.logger:
                    self.logger.log("Unity menu ready")

        elif self.state == "WAIT_INPUT":
            elapsed_scan = time.time() - self.menu_scan_start_time
            if elapsed_scan >= self.menu_scan_interval:
                self.menu_scan_start_time = time.time()
                self.menu_scan_index = 1 - self.menu_scan_index
                for i, btn in enumerate(self.menu_buttons):
                    btn.setStyleSheet(
                        self.active_btn_style
                        if i == self.menu_scan_index
                        else self.inactive_btn_style
                    )

            if status == 1 or status == 2:
                if self.logger:
                    self.logger.log(
                        f"Unity menu selection: option {self.menu_scan_index}"
                    )
                self.state = "STARTING"
                if self.menu_scan_index == 0:
                    QtCore.QTimer.singleShot(0, self.start_game)
                else:
                    self._request_exit()
                return

        elif self.state == "COOLDOWN":
            if time.time() - self.state_start_time > self.t_cool:
                self.reset_to_initialization()
