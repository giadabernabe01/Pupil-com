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
        if self.startup_delay > 0:
            time.sleep(self.startup_delay)
        return self._proc

    def send_press(self, confidence=1.0, quality=1.0):
        payload = json.dumps(
            {
                "type": "press",
                "confidence": float(confidence),
                "quality": float(quality),
            }
        ).encode("utf-8")
        self._sock.sendto(payload, (self.host, self.port))

    def send_release(self):
        self._sock.sendto(b'{"type":"release"}', (self.host, self.port))

    def is_running(self):
        if not self._exe_name:
            return False
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {self._exe_name}"],
                text=True,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )
            return self._exe_name.lower() in out.lower()
        except Exception:
            return bool(self._proc)

    def stop_unity(self):
        if self._exe_name:
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
        self._proc = None

    def close(self):
        self.stop_unity()
        try:
            self._sock.close()
        except Exception:
            pass
