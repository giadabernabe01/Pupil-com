"""UDP + process bridge between Pupil-com and Space Evaders (Unity)."""

from __future__ import annotations

import ctypes
import json
import socket
import subprocess
import time
from pathlib import Path


class UnityGameBridge:
    """Launch SpaceEvaders.exe and forward short PAR events as UDP presses."""

    def __init__(self, host="127.0.0.1", port=47890, exe_path="", startup_delay=2.0):
        self.host = host
        self.port = int(port)
        self.exe_path = exe_path
        self.startup_delay = float(startup_delay)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._proc = None
        self._exe_name = None
        self._running_cached = False
        self._running_check_t = 0.0

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

        self.stop_unity()
        self._exe_name = path.name

        # Launch elevated (UAC "run as administrator")
        # ShellExecuteW "runas" — needed when normal Popen hits WinError 5
        rc = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            str(path),
            None,
            str(path.parent),
            1,  # SW_SHOWNORMAL
        )
        # Per MSDN: return value > 32 means success
        if rc <= 32:
            raise PermissionError(
                f"Avvio come amministratore fallito (codice {rc}) per:\n{path}\n"
                "Se hai annullato UAC, riprova e conferma Sì."
            )

        self._proc = True  # marker: launched (no Popen handle across UAC)
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
        payload = {"type": str(cmd_type)}
        payload.update(fields)
        data = json.dumps(payload).encode("utf-8")
        self._sock.sendto(data, (self.host, self.port))

    def send_pause(self):
        self.send_command("pause")

    def send_resume(self):
        self.send_command("resume")

    def send_exit(self):
        """Ask Unity to quit (send a few times — UDP is best-effort)."""
        for _ in range(3):
            try:
                self.send_command("exit")
            except Exception:
                break
            time.sleep(0.05)

    def send_tracking_lost(self):
        self.send_command("tracking_lost")

    def send_tracking_ok(self):
        self.send_command("tracking_ok")

    def _force_check_running(self):
        """Immediate process check (bypasses cache)."""
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
        try:
            flags = (
                subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0
            )
            out = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {self._exe_name}"],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            self._running_cached = self._exe_name.lower() in out.lower()
        except Exception:
            self._running_cached = bool(self._proc)
        return self._running_cached

    def _kill_process(self, elevated=False):
        if not self._exe_name:
            return
        if elevated:
            # Unity was started with runas — normal taskkill often gets Access Denied
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    "taskkill.exe",
                    f"/F /IM {self._exe_name}",
                    None,
                    0,  # SW_HIDE
                )
            except Exception:
                pass
            return

        try:
            flags = (
                subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0
            )
            subprocess.run(
                ["taskkill", "/IM", self._exe_name, "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                check=False,
            )
        except Exception:
            pass

    def stop_unity(self):
        """Graceful UDP exit, then force-kill (elevated if needed)."""
        if not self._exe_name:
            self._proc = None
            self._running_cached = False
            return

        # 1) Ask Unity to quit itself
        try:
            self.send_exit()
        except Exception:
            pass

        # 2) Wait for clean shutdown
        deadline = time.time() + 2.5
        while time.time() < deadline:
            if not self._force_check_running():
                break
            time.sleep(0.2)

        # 3) Still alive → taskkill, then elevated taskkill
        if self._force_check_running():
            self._kill_process(elevated=False)
            time.sleep(0.4)
            if self._force_check_running():
                self._kill_process(elevated=True)
                time.sleep(0.8)

        self._proc = None
        self._running_cached = False
        self._running_check_t = 0.0

    def close(self):
        self.stop_unity()
        try:
            self._sock.close()
        except Exception:
            pass
