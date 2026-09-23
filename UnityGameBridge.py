"""UDP + process bridge between Pupil-com and Space Evaders (Unity)."""

from __future__ import annotations

import ctypes
import json
import socket
import subprocess
import time
from ctypes import wintypes
from pathlib import Path


class UnityGameBridge:
    """Launch SpaceEvaders.exe and forward short PAR events as UDP presses."""

    def __init__(
        self,
        host="127.0.0.1",
        port=47890,
        exe_path="",
        startup_delay=2.0,
        fullscreen=False,
        window_width=1280,
        window_height=720,
        monitor=0,
    ):
        self.host = host
        self.port = int(port)
        self.exe_path = exe_path
        self.startup_delay = float(startup_delay)
        self.fullscreen = bool(fullscreen)
        self.window_width = int(window_width) if window_width else 0
        self.window_height = int(window_height) if window_height else 0
        # Unity -monitor is 1-based; 0 = omit (default / primary)
        self.monitor = int(monitor) if monitor else 0
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._proc = None
        self._exe_name = None
        self._running_cached = False
        self._running_check_t = 0.0
        self._cached_pids = []
        self._closing = False
        self._launched_elevated = False

    def _launch_args(self):
        """Unity standalone CLI so the window is movable on multi-monitor setups."""
        parts = []
        if self.fullscreen:
            parts.append("-screen-fullscreen 1")
        else:
            parts.append("-screen-fullscreen 0")
            if self.window_width > 0:
                parts.append(f"-screen-width {self.window_width}")
            if self.window_height > 0:
                parts.append(f"-screen-height {self.window_height}")
        if self.monitor > 0:
            parts.append(f"-monitor {self.monitor}")
        return " ".join(parts)

    def start_unity(self):
        path = Path(self.exe_path).expanduser()
        if not str(self.exe_path).strip():
            raise FileNotFoundError(
                "unity_game.exe_path mancante in parameters.json"
            )

        try:
            path = path.resolve(strict=True)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Unity exe non trovata: {path}") from e

        if not path.is_file():
            raise FileNotFoundError(
                f"unity_game.exe_path non è un file .exe: {path}"
            )

        # Cleanup leftovers without UAC (exit path is the only elevate-kill)
        if self._exe_name:
            self.stop_unity(allow_elevate=False)
        self._exe_name = path.name
        self._closing = False

        launch_params = self._launch_args()
        launched = False

        # Prefer normal launch (0 UAC). Elevate only if Access Denied.
        try:
            args = [str(path)]
            if launch_params:
                args.extend(launch_params.split())
            subprocess.Popen(
                args,
                cwd=str(path.parent),
                creationflags=subprocess.DETACHED_PROCESS
                if hasattr(subprocess, "DETACHED_PROCESS")
                else 0,
            )
            launched = True
        except OSError as e:
            # WinError 5 = access denied, 740 = elevation required → one UAC via runas
            winerr = getattr(e, "winerror", None)
            if winerr not in (5, 740) and e.errno not in (13,):
                raise

        if not launched:
            rc = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                str(path),
                launch_params or None,
                str(path.parent),
                1,  # SW_SHOWNORMAL
            )
            if rc <= 32:
                raise PermissionError(
                    f"Avvio come amministratore fallito (codice {rc}) per:\n{path}\n"
                    "Se hai annullato UAC, riprova e conferma Sì."
                )
            self._launched_elevated = True
        else:
            self._launched_elevated = False

        self._proc = True  # marker: launched (no reliable Popen handle across UAC)
        self._running_cached = True
        self._running_check_t = time.time()
        if self.startup_delay > 0:
            time.sleep(self.startup_delay)
        return self._proc

    def send_press(self, confidence=1.0, quality=1.0):
        self.send_command(
            "press", confidence=float(confidence), quality=float(quality)
        )

    def send_release(self):
        self.send_command("release")

    def send_command(self, cmd_type, **fields):
        """Send a control/gameplay UDP message to Unity (press, pause, resume, exit, …)."""
        if self._sock is None:
            return
        payload = {"type": str(cmd_type)}
        payload.update(fields)
        data = json.dumps(payload).encode("utf-8")
        try:
            self._sock.sendto(data, (self.host, self.port))
        except Exception:
            pass

    def send_pause(self):
        """Spam pause a few times — UDP is unreliable and builds may drop one packet."""
        for _ in range(5):
            self.send_command("pause")
            time.sleep(0.04)

    def send_resume(self):
        for _ in range(3):
            self.send_command("resume")
            time.sleep(0.04)

    def send_exit(self):
        """Ask Unity to quit (send a few times — UDP is best-effort)."""
        for _ in range(5):
            self.send_command("exit")
            time.sleep(0.05)

    def send_tracking_lost(self):
        self.send_command("tracking_lost")

    def send_tracking_ok(self):
        self.send_command("tracking_ok")

    def _creation_flags(self):
        return (
            subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0
        )

    def _list_pids(self):
        """PIDs for the Unity exe (handles names with spaces)."""
        if not self._exe_name:
            return []
        try:
            # /FI value must be one argv so spaces in the exe name stay intact
            out = subprocess.check_output(
                [
                    "tasklist",
                    "/FI",
                    f"IMAGENAME eq {self._exe_name}",
                    "/FO",
                    "CSV",
                    "/NH",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=self._creation_flags(),
            )
        except Exception:
            self._cached_pids = []
            return []

        import csv
        import io

        pids = []
        target = self._exe_name.lower()
        for row in csv.reader(io.StringIO(out)):
            if len(row) >= 2 and row[0].lower() == target:
                try:
                    pids.append(int(row[1]))
                except ValueError:
                    continue
        self._cached_pids = pids
        return pids

    def _force_check_running(self):
        self._running_check_t = 0.0
        self._running_cached = None
        return self.is_running()

    def is_running(self):
        """Cached process check — never call tasklist every pupil frame."""
        if not self._exe_name:
            return False
        now = time.time()
        if (
            now - self._running_check_t < 1.5
            and self._running_cached is not None
        ):
            return self._running_cached
        self._running_check_t = now
        pids = self._list_pids()
        self._running_cached = len(pids) > 0
        if not self._running_cached:
            self._proc = None
            self._cached_pids = []
        return self._running_cached

    def get_main_window_rect(self):
        """Largest visible HWND for Space Evaders: (left, top, right, bottom) or None.

        Used to dock the PAR strip / overlays onto the same monitor as Unity.
        """
        if not self.is_running():
            return None
        pids = set(self._cached_pids)
        if not pids:
            pids = set(self._list_pids())
        if not pids:
            return None

        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
        )

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        best = [None]  # (area, left, top, right, bottom)

        def _cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            # Skip owned popups / tool windows without a real title bar app frame
            if user32.GetWindow(hwnd, 4):  # GW_OWNER
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value not in pids:
                return True
            rect = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            w = int(rect.right - rect.left)
            h = int(rect.bottom - rect.top)
            if w < 200 or h < 200:
                return True
            area = w * h
            if best[0] is None or area > best[0][0]:
                best[0] = (
                    area,
                    int(rect.left),
                    int(rect.top),
                    int(rect.right),
                    int(rect.bottom),
                )
            return True

        try:
            user32.EnumWindows(WNDENUMPROC(_cb), 0)
        except Exception:
            return None
        if best[0] is None:
            return None
        return best[0][1:]

    def _kill_all(self, elevated=False):
        """Force-kill every matching process. Elevated path uses ONE UAC prompt."""
        if not self._exe_name:
            return

        pids = self._list_pids()
        if not elevated:
            for pid in pids:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=self._creation_flags(),
                        check=False,
                    )
                except Exception:
                    pass
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/IM", self._exe_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=self._creation_flags(),
                    check=False,
                )
            except Exception:
                pass
            return

        # ONE elevated taskkill — quotes required for "Space Evaders.exe"
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                "taskkill.exe",
                f'/F /T /IM "{self._exe_name}"',
                None,
                0,
            )
        except Exception:
            pass

    def stop_unity(self, allow_elevate=True):
        """Graceful UDP exit, then force-kill.

        allow_elevate=True (user exit): at most ONE UAC prompt for taskkill.
        allow_elevate=False (pre-start cleanup): never prompt UAC.
        """
        if self._closing:
            return
        self._closing = True

        try:
            if not self._exe_name:
                self._proc = None
                self._running_cached = False
                return

            # Already dead?
            if not self._force_check_running():
                self._proc = None
                self._running_cached = False
                return

            # 1) Ask Unity to quit itself
            try:
                self.send_exit()
            except Exception:
                pass

            deadline = time.time() + 2.0
            while time.time() < deadline:
                if not self._force_check_running():
                    break
                time.sleep(0.15)

            # 2) Normal kill (no UAC)
            if self._force_check_running():
                self._kill_all(elevated=False)
                time.sleep(0.5)

            # 3) At most ONE elevated kill on user exit (UAC once) if still alive
            if allow_elevate and self._force_check_running():
                self._kill_all(elevated=True)
                deadline = time.time() + 3.0
                while time.time() < deadline:
                    if not self._force_check_running():
                        break
                    time.sleep(0.25)

            self._proc = None
            self._running_cached = False
            self._running_check_t = 0.0
            self._launched_elevated = False
        finally:
            self._closing = False

    def close(self):
        """Stop Unity (if needed) and close the UDP socket. Idempotent."""
        try:
            self.stop_unity()
        except Exception:
            pass
        sock = self._sock
        self._sock = None
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
