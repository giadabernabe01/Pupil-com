"""UDP + process bridge between Pupil-com and Space Evaders (Unity)."""

from __future__ import annotations

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

    def start_unity(self):
        path = Path(self.exe_path)
        if not str(self.exe_path).strip():
            raise FileNotFoundError(
                "unity_game.exe_path mancante in parameters.json"
            )
        if not path.exists():
            raise FileNotFoundError(f"Unity exe non trovata: {path}")

        self.stop_unity()
        self._proc = subprocess.Popen([str(path)])
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
        return self._proc is not None and self._proc.poll() is None

    def stop_unity(self):
        if self._proc is None:
            return
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        self._proc = None

    def close(self):
        self.stop_unity()
        try:
            self._sock.close()
        except Exception:
            pass
