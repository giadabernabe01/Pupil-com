"""Space Evaders launcher widget: PAR short -> UDP press into Unity.

Includes live filtered-area / threshold feedback (does not change the detector).
"""

import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

from DataProcessing import AreaFilter, ConstrictionMonitor
from HelperClasses import SessionLogger, DataPlotter, DataSaver
from UnityGameBridge import UnityGameBridge


class PupilLiveOverlay(QtWidgets.QWidget):
    """Always-on-top mini monitor so the signal stays visible over Unity."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            QtCore.Qt.Window
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool,
        )
        self.setWindowTitle("PAR live — Space Evaders")
        self.setFixedWidth(360)
        self.setStyleSheet("background-color: #1e1e1e; color: #eee;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Segnale pupilla (filtrato)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #7CFC00;")
        layout.addWidget(title)

        tip = QtWidgets.QLabel(
            "Lontano → area alta  ·  Vicino → area scende sotto soglia"
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("font-size: 12px; color: #aaa;")
        layout.addWidget(tip)

        self.values_label = QtWidgets.QLabel("Area: —   Soglia: —")
        self.values_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.values_label)

        self.bar = QtWidgets.QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(22)
        self.bar.setStyleSheet(
            "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
            "QProgressBar::chunk { background: #2ecc71; border-radius: 3px; }"
        )
        layout.addWidget(self.bar)

        self.state_label = QtWidgets.QLabel("Stato: in attesa")
        self.state_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #ccc;")
        layout.addWidget(self.state_label)

        self.udp_label = QtWidgets.QLabel("UDP: —")
        self.udp_label.setStyleSheet("font-size: 13px; color: #88c;")
        layout.addWidget(self.udp_label)

        self.press_count = 0

    def update_signal(self, filtered, thresh, under_thresh, status, last_udp_msg=None):
        f = float(filtered) if filtered is not None else 0.0
        t = float(thresh) if thresh is not None else 0.0
        self.values_label.setText(f"Area filt.: {f:.2f}   Soglia: {t:.2f}")

        # Bar: how far above threshold (relaxed) vs below (constricting).
        # 50% = exactly at threshold; >50% = above (far); <50% = below (near).
        if t > 1e-6:
            ratio = f / t
            # map ratio 0.5..1.5 -> 0..1000, clamp
            bar_val = int(max(0.0, min(1.0, (ratio - 0.5))) * 1000)
        else:
            bar_val = 0
        self.bar.setValue(bar_val)

        if status == 1:
            self.state_label.setText("Stato: PAR BREVE rilevato → inviato")
            self.state_label.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #7CFC00;"
            )
            self.bar.setStyleSheet(
                "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
                "QProgressBar::chunk { background: #7CFC00; border-radius: 3px; }"
            )
            self.press_count += 1
            self.udp_label.setText(
                f"UDP press #{self.press_count}  ({time.strftime('%H:%M:%S')})"
            )
        elif status == 2:
            self.state_label.setText("Stato: PAR LUNGO (tieni meno il vicino)")
            self.state_label.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #f39c12;"
            )
        elif under_thresh:
            self.state_label.setText("Stato: sotto soglia (costrizione…)")
            self.state_label.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #e74c3c;"
            )
            self.bar.setStyleSheet(
                "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
                "QProgressBar::chunk { background: #e74c3c; border-radius: 3px; }"
            )
        else:
            self.state_label.setText("Stato: sopra soglia (lontano / rilassato)")
            self.state_label.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #2ecc71;"
            )
            self.bar.setStyleSheet(
                "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
                "QProgressBar::chunk { background: #2ecc71; border-radius: 3px; }"
            )

        if last_udp_msg:
            self.udp_label.setText(last_udp_msg)


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
        self.filtered_val = 0.0

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
        self.live_overlay = None
        self._last_udp_msg = "UDP: —"
        self.t_cool = 2.0
        self.t_init = 3.0
        self.menu_scan_interval = 3.5

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
        self._close_live_overlay()
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

    def _make_inline_signal_box(self):
        """Compact signal readout embedded in the main widget (menu + in-game)."""
        box = QtWidgets.QFrame()
        box.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border: 1px solid #555; "
            "border-radius: 8px; padding: 8px; }"
        )
        v = QtWidgets.QVBoxLayout(box)

        self.signal_title = QtWidgets.QLabel("Monitor segnale (area filtrata)")
        self.signal_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #7CFC00;")
        v.addWidget(self.signal_title)

        self.signal_tip = QtWidgets.QLabel(
            "Ricorda: lontano → vicino per costrizione. Barra verde = rilassato; rossa = sotto soglia."
        )
        self.signal_tip.setWordWrap(True)
        self.signal_tip.setStyleSheet("font-size: 12px; color: #aaa;")
        v.addWidget(self.signal_tip)

        self.signal_values = QtWidgets.QLabel("Area filt.: —   Soglia: —   Raw: —")
        self.signal_values.setStyleSheet("font-size: 14px; color: #eee;")
        v.addWidget(self.signal_values)

        self.signal_bar = QtWidgets.QProgressBar()
        self.signal_bar.setRange(0, 1000)
        self.signal_bar.setValue(0)
        self.signal_bar.setTextVisible(False)
        self.signal_bar.setFixedHeight(18)
        self.signal_bar.setStyleSheet(
            "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
            "QProgressBar::chunk { background: #2ecc71; border-radius: 3px; }"
        )
        v.addWidget(self.signal_bar)

        self.signal_state = QtWidgets.QLabel("Stato: —")
        self.signal_state.setStyleSheet("font-size: 14px; font-weight: bold; color: #ccc;")
        v.addWidget(self.signal_state)
        return box

    def _update_signal_ui(self, raw_area, filtered, thresh, status):
        under = thresh is not None and filtered is not None and thresh > 0 and filtered < thresh
        f = float(filtered) if filtered is not None else 0.0
        t = float(thresh) if thresh is not None else 0.0
        r = float(raw_area) if raw_area is not None else 0.0

        if hasattr(self, "signal_values") and self.signal_values is not None:
            try:
                self.signal_values.setText(
                    f"Area filt.: {f:.2f}   Soglia: {t:.2f}   Raw: {r:.2f}"
                )
                if t > 1e-6:
                    ratio = f / t
                    bar_val = int(max(0.0, min(1.0, (ratio - 0.5))) * 1000)
                else:
                    bar_val = 0
                self.signal_bar.setValue(bar_val)

                if status == 1:
                    self.signal_state.setText("Stato: PAR BREVE → UDP inviato")
                    self.signal_state.setStyleSheet(
                        "font-size: 14px; font-weight: bold; color: #7CFC00;"
                    )
                    chunk = "#7CFC00"
                elif status == 2:
                    self.signal_state.setText("Stato: PAR LUNGO (rilascia prima il vicino)")
                    self.signal_state.setStyleSheet(
                        "font-size: 14px; font-weight: bold; color: #f39c12;"
                    )
                    chunk = "#f39c12"
                elif under:
                    self.signal_state.setText("Stato: sotto soglia (costrizione in corso)")
                    self.signal_state.setStyleSheet(
                        "font-size: 14px; font-weight: bold; color: #e74c3c;"
                    )
                    chunk = "#e74c3c"
                else:
                    self.signal_state.setText("Stato: sopra soglia (lontano / ok)")
                    self.signal_state.setStyleSheet(
                        "font-size: 14px; font-weight: bold; color: #2ecc71;"
                    )
                    chunk = "#2ecc71"

                self.signal_bar.setStyleSheet(
                    "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
                    f"QProgressBar::chunk {{ background: {chunk}; border-radius: 3px; }}"
                )
            except RuntimeError:
                pass  # widget deleted during clear_ui

        if self.live_overlay is not None:
            try:
                self.live_overlay.update_signal(
                    f, t, under, status, last_udp_msg=self._last_udp_msg
                )
            except RuntimeError:
                self.live_overlay = None

    def _open_live_overlay(self):
        self._close_live_overlay()
        self.live_overlay = PupilLiveOverlay()
        # Top-right of primary screen
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.live_overlay.adjustSize()
            w = self.live_overlay.width()
            self.live_overlay.move(geo.right() - w - 24, geo.top() + 40)
        self.live_overlay.show()
        self.live_overlay.raise_()

    def _close_live_overlay(self):
        if self.live_overlay is not None:
            try:
                self.live_overlay.close()
                self.live_overlay.deleteLater()
            except RuntimeError:
                pass
            self.live_overlay = None

    def reset_to_initialization(self):
        self.state = "RESETTING"
        self.game_active = False
        self.frame_event_code = 0
        self._close_live_overlay()
        self.monitor.reset_monitor()
        if hasattr(self.monitor, "baseline_buffer"):
            self.monitor.baseline_buffer.clear()

        self.clear_ui()

        welcome = QtWidgets.QLabel(
            "SPACE EVADERS (Unity)\n\n"
            "PAR breve = azione nel gioco\n"
            "(scudo / salvataggio / colpo).\n\n"
            "Comando: guarda LONTANO, poi VICINO (breve)."
        )
        welcome.setAlignment(QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(welcome)

        self.main_layout.addWidget(self._make_inline_signal_box())

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

        self.status_label = None
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
            "Partita attiva — tieni d'occhio il monitor PAR\n"
            "(finestra in alto a destra, sempre sopra Unity).\n\n"
            "Lontano → vicino breve = azione"
        )
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_label.setStyleSheet(
            "font-size: 18px; color: #7CFC00; font-weight: bold;"
        )
        self.main_layout.addWidget(self.info_label)

        self.main_layout.addWidget(self._make_inline_signal_box())

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

        self._open_live_overlay()
        self._last_udp_msg = "UDP: in ascolto verso Unity…"

        if self.logger:
            self.logger.log("Unity started; live PAR overlay open")

    def update_data(self, raw_area):
        self.current_area = raw_area
        self.filtered_val = self.filter.area_filtering(raw_area)

        if self.filter.timeout_triggered:
            self.show_timeout_dialog()
            return

        current_thresh = self.monitor.current_sma_thresh
        exit_thresh = self.monitor.exit_thresh
        status = self.monitor.constriction_detector(self.filtered_val)

        # Live UI every frame (menu + game) — detector unchanged
        self._update_signal_ui(raw_area, self.filtered_val, current_thresh, status)

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
                stamp = time.strftime("%H:%M:%S")
                self._last_udp_msg = f"UDP press inviato @ {stamp}"
                if self.logger:
                    self.logger.log("Short PAR -> Unity UDP press")
                if hasattr(self, "status_label") and self.status_label:
                    try:
                        self.status_label.setText(f"PAR inviato a Unity ({stamp})")
                    except RuntimeError:
                        pass
            return

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
