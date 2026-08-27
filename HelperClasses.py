import os
import time
import datetime
import csv
import pickle
import numpy as np
import matplotlib.pyplot as plt
import pyttsx3
from PyQt5.QtCore import QThread, pyqtSignal
from DriveUploader import DriveUploaderThread

# ---------------------------------------------------------
# GOOGLE DRIVE CONFIGURATION
# ---------------------------------------------------------
ACTIVE_UPLOAD_THREADS = [] 
USE_DRIVE = False
MAIN_DRIVE_FOLDER_ID = "1VpNhj7DEMyA-NYGaMWn8563J0OqrOgbM"
CURRENT_SESSION_DRIVE_FOLDER_ID = MAIN_DRIVE_FOLDER_ID

def get_local_results_path():
    """Ensures the local Experimental Results folder exists."""
    base_path = "Experimental_Results"
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    return base_path

def set_session_drive_folder(folder_id):
    """Updates the target Drive folder for the current session."""
    global CURRENT_SESSION_DRIVE_FOLDER_ID
    CURRENT_SESSION_DRIVE_FOLDER_ID = folder_id

# ---------------------------------------------------------
# SESSION LOGGER
# ---------------------------------------------------------
class SessionLogger:
    """Handles basic text logging for system events."""
    def __init__(self, folder_path, session_name):
        self.filepath = os.path.join(folder_path, "session_log.txt")
        self.session_name = session_name
        self.log(f"--- SESSION STARTED: {session_name} ---")

    def log(self, message):
        """Writes event to local log file and prints to console."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}][{self.session_name}]{message}\n"
        print(entry.strip()) 
        with open(self.filepath, "a") as f:
            f.write(entry)

# ---------------------------------------------------------
# DATA PLOTTER
# ---------------------------------------------------------
class DataPlotter:
    """Handles real-time data tracking and plot generation."""
    def __init__(self, folder_path, session_name):
        self.folder_path = folder_path
        self.session_name = session_name
        self.start_time = time.time()

        # PLOT DATA BUFFERS
        self.timestamps = []
        self.filtered_data = []
        self.thresholds = []
        self.exit_thresholds = []

        self.short_constrictions = []
        self.long_constrictions = []
        self.short_constriction_requests = []
        self.long_constriction_requests = []
    
    def add_data(self, val, threshold, exit_threshold):
        """Appends frame data for plotting."""
        t = time.time() - self.start_time
        self.timestamps.append(t)
        self.filtered_data.append(val)
        self.thresholds.append(threshold)
        
        if exit_threshold is not None: 
            self.exit_thresholds.append(exit_threshold) 
        else: 
            self.exit_thresholds.append(float('nan'))

    def mark_constriction(self, c_type="short"):
        """Records detected constriction events."""
        t = time.time() - self.start_time
        if c_type == "long":
            self.long_constrictions.append(t)
        else:
            self.short_constrictions.append(t)

    def mark_constriction_requests(self, c_type):
        """Records requested constriction events for testing phase."""
        t = time.time() - self.start_time
        if c_type == 'LONG':
            self.long_constriction_requests.append(t)
        else:
            self.short_constriction_requests.append(t)

    def save_plot(self):
        """Generates, saves locally, and uploads the final graph."""
        if not self.timestamps: 
            return

        plt.figure(figsize=(10,6))
        plt.plot(self.timestamps, self.filtered_data, label='Filtered Area', color='blue')

        if any(t > 0 for t in self.thresholds):
            plt.plot(self.timestamps, self.thresholds, label='Threshold', color='black', linestyle='--')
            plt.plot(self.timestamps, self.exit_thresholds, label='Exit threshold', color='red', linestyle='--')
        
        # SHORT EVENTS (Solid Red)
        for i, ct in enumerate(self.short_constrictions):
            label = 'Short Constriction' if i == 0 else ""
            plt.axvline(x=ct, color='red', linestyle='-', alpha=0.7, label=label)
            
        # LONG EVENTS (Solid Green)
        for i, ct in enumerate(self.long_constrictions):
            label = 'Long Constriction' if i == 0 else ""
            plt.axvline(x=ct, color='green', linestyle='-', alpha=0.7, label=label)

        # SHORT REQUESTS (Dotted Red)
        for i, ct in enumerate(self.short_constriction_requests):
            label = 'Short constriction request' if i == 0 else ""
            plt.axvline(x=ct, color='red', linestyle='--', alpha=0.7, label=label)
            
        # LONG REQUESTS (Dotted Green)
        for i, ct in enumerate(self.long_constriction_requests):
            label = 'Long constriction request' if i == 0 else ""
            plt.axvline(x=ct, color='green', linestyle='--', alpha=0.7, label=label)
            
        plt.title(f"Session: {self.session_name}")
        plt.xlabel("Time (s)")
        plt.ylabel("Pupil Area (pixels^2)")
        plt.legend()
        plt.grid(True)

        # SAVE LOCALLY
        filename = f"{self.session_name}_{datetime.datetime.now().strftime('%H%M%S.%f')[:-3]}.png"
        save_path = os.path.join(self.folder_path, filename)
        plt.savefig(save_path)
        plt.close()
        print(f"Plot saved locally to {save_path}")

        # GOOGLE DRIVE UPLOAD
        self._start_upload(save_path) 

    def _start_upload(self, file_path):
        """Helper to safely handle threaded uploads."""
        uploader = DriveUploaderThread(file_path, folder_id=CURRENT_SESSION_DRIVE_FOLDER_ID)
        uploader.finished_signal.connect(lambda name, success: print(f"[Drive] Uploaded {name} successfully!"))
        uploader.error_signal.connect(lambda err: print(f"[Drive] Upload failed: {err}"))
        
        ACTIVE_UPLOAD_THREADS.append(uploader)
        uploader.finished.connect(lambda: ACTIVE_UPLOAD_THREADS.remove(uploader) if uploader in ACTIVE_UPLOAD_THREADS else None)
        uploader.start()

# ---------------------------------------------------------
# DATA SAVER
# ---------------------------------------------------------
class DataSaver:
    """Handles CSV generation for pupil data."""
    def __init__(self, folder_path, session_name):
        self.folder_path = folder_path
        self.session_name = session_name
        self.data_rows = []
        self.start_time = time.time()

    def add_data(self, raw, filtered, threshold, exit_threshold, event_code, extra_value=None, frame_instruction_code=None, gaze_x=None, gaze_y=None):
        """Appends a single frame's data row to memory."""
        timestamp = time.time()
        formatted_exit = f"{exit_threshold:.2f}" if exit_threshold is not None else ""

        row = [
            timestamp, 
            f"{raw:.2f}",       
            f"{filtered:.2f}", 
            f"{threshold:.2f}",
            formatted_exit, 
            event_code,       
        ]

        if extra_value is not None:
            row.extend([f"{extra_value}"])
        if frame_instruction_code is not None:
            row.extend([f"{frame_instruction_code}"])
        if gaze_x is not None and gaze_y is not None:
            row.extend([f"{gaze_x:.4f}", f"{gaze_y:.4f}"])
        
        self.data_rows.append(row)

    def save_file(self, extra_column_name=" "):
        """Generates CSV from memory and triggers upload."""
        if not self.data_rows: 
            return
        
        timestamp_str = datetime.datetime.now().strftime("%H%M%S")
        filename = f"{self.session_name}_Data_{timestamp_str}.csv"
        save_path = os.path.join(self.folder_path, filename)

        # CSV HEADER
        header = ["Timestamp", "Raw_Area", "Filtered_Area", "Threshold", "Exit_Threshold", "Event_Code", extra_column_name]
        
        if len(self.data_rows[0]) > 7:
            header.extend(["Gaze_X", "Gaze_Y"])
            
        # LOCAL SAVE
        try:
            with open(save_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(self.data_rows)
            
            print(f"CSV saved locally to {save_path}")

            # UPLOAD TO DRIVE
            uploader = DriveUploaderThread(save_path, folder_id=CURRENT_SESSION_DRIVE_FOLDER_ID)
            uploader.finished_signal.connect(lambda name, success: print(f"[Drive] Uploaded {name} successfully!"))
            uploader.error_signal.connect(lambda err: print(f"[Drive] Upload failed: {err}"))
            
            ACTIVE_UPLOAD_THREADS.append(uploader)
            uploader.finished.connect(lambda: ACTIVE_UPLOAD_THREADS.remove(uploader) if uploader in ACTIVE_UPLOAD_THREADS else None)
            uploader.start()
            
        except Exception as e:
            print(f"Error saving CSV: {e}")

# ---------------------------------------------------------
# TTS THREAD WORKER
# ---------------------------------------------------------
class TTSWorkerThread(QThread):
    """Asynchronous Text-to-Speech generation thread."""
    audio_ready_signal = pyqtSignal(str) 

    def __init__(self, text, file_path):
        super().__init__()
        self.text = text
        self.file_path = file_path

    def run(self):
        # SAPI5 ENGINE SETUP (Isolated from main GUI thread to prevent freezing)
        speaker = pyttsx3.init()
        speaker.setProperty('voice', 'italian')
        speaker.setProperty('rate', 150)
        
        # WAV GENERATION
        speaker.save_to_file(self.text, self.file_path)
        speaker.runAndWait()
        
        # UI NOTIFICATION
        self.audio_ready_signal.emit(self.file_path)
