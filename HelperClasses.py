import os
import time
import datetime
import matplotlib.pyplot as plt
import numpy as np
import csv
import pickle
import matplotlib.pyplot as plt
from DriveUploader import DriveUploaderThread

ACTIVE_UPLOAD_THREADS = [] # Google Drive global variable

MAIN_DRIVE_FOLDER_ID = "1VpNhj7DEMyA-NYGaMWn8563J0OqrOgbM"

CURRENT_SESSION_DRIVE_FOLDER_ID = MAIN_DRIVE_FOLDER_ID

def get_local_results_path():
    """Ensures the 'Experimental Results' folder exists locally."""
    base_path = "Experimental_Results"
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    return base_path

def set_session_drive_folder(folder_id):
    """Updates the target Drive folder for the current session."""
    global CURRENT_SESSION_DRIVE_FOLDER_ID
    CURRENT_SESSION_DRIVE_FOLDER_ID = folder_id

class SessionLogger:
    def __init__(self, folder_path, session_name):
        self.filepath = os.path.join(folder_path, "session_log.txt")
        self.session_name = session_name
        self.log(f"--- SESSION STARTED: {session_name} ---")

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}][{self.session_name}]{message}\n"
        print(entry.strip()) # Print to console
        with open(self.filepath, "a") as f:
            f.write(entry)

class DataPlotter:
    def __init__(self, folder_path, session_name):
        self.folder_path = folder_path
        self.session_name = session_name
        self.start_time = time.time()

        # Lists to store data for plotting
        self.timestamps = []
        self.filtered_data = []
        self.thresholds = []

        self.short_constrictions = []
        self.long_constrictions = []
    
    def add_data(self, val, threshold=0.0):
        t = time.time() - self.start_time
        self.timestamps.append(t)
        self.filtered_data.append(val)
        self.thresholds.append(threshold)

    def mark_constriction(self, c_type = "short"):
        t = time.time() - self.start_time
        if c_type == "long":
            self.long_constrictions.append(t)
        else:
            self.short_constrictions.append(t)

    def save_plot(self):
        if not self.timestamps: return

        plt.figure(figsize=(10,6))
        plt.plot(self.timestamps, self.filtered_data, label='Filtered Area', color='blue')

        if any(t>0 for t in self.thresholds):
            plt.plot(self.timestamps, self.thresholds, label='Threshold', color='black', linestyle='--')
        
        # Add red lines for short constriction
        for i, ct in enumerate(self.short_constrictions):
            label = 'Short Constriction' if i == 0 else ""
            plt.axvline(x=ct, color='red', linestyle='-', alpha=0.7, label=label)
        # Add green lines for short constriction
        for i, ct in enumerate(self.long_constrictions):
            label = 'Long Constriction' if i == 0 else ""
            plt.axvline(x=ct, color='green', linestyle='-', alpha=0.7, label=label)
            
        plt.title(f"Session: {self.session_name}")
        plt.xlabel("Time (s)")
        plt.ylabel("Pupil Area")
        plt.legend()
        plt.grid(True)

        # Save with timestamp to avoid overwriting
        filename = f"{self.session_name}_{datetime.datetime.now().strftime("%H%M%S.%f")[:-3]}.png"
        save_path = os.path.join(self.folder_path, filename)
        plt.savefig(save_path)
        plt.close()
        print(f"Plot saved locally to {save_path}")

        self._start_upload(save_path) # Google Drive upload

    def _start_upload(self, file_path):
        """Helper to safely start the upload thread"""
        uploader = DriveUploaderThread(file_path, folder_id=CURRENT_SESSION_DRIVE_FOLDER_ID)
        uploader.finished_signal.connect(lambda name, success: print(f"[Drive] Uploaded {name} successfully!"))
        uploader.error_signal.connect(lambda err: print(f"[Drive] Upload failed: {err}"))
        
        ACTIVE_UPLOAD_THREADS.append(uploader)
        uploader.finished.connect(lambda: ACTIVE_UPLOAD_THREADS.remove(uploader) if uploader in ACTIVE_UPLOAD_THREADS else None)
        
        uploader.start()

class DataSaver:
    def __init__(self, folder_path, session_name):
        self.folder_path = folder_path
        self.session_name = session_name
        
        # Data Columns
        self.data_rows = []
        self.start_time = time.time()

    def add_data(self, raw, filtered, threshold, event_code, extra_value="", gaze_x=None, gaze_y=None):
        """Call this every frame to record a data point."""
        timestamp = time.time()

        row = [
            timestamp, 
            f"{raw:.2f}",       
            f"{filtered:.2f}", 
            f"{threshold:.2f}", 
            event_code, 
            extra_value        
        ]

        if gaze_x is not None and gaze_y is not None:
            row.extend([f"{gaze_x:.4f}", f"{gaze_y:.4f}"])
        
        self.data_rows.append(row)

    def save_file(self, extra_column_name=" "):
        """Call this at the end of the session to generate the CSV."""
        if not self.data_rows: 
            return
        
        timestamp_str = datetime.datetime.now().strftime("%H%M%S")
        filename = f"{self.session_name}_Data_{timestamp_str}.csv"
        save_path = os.path.join(self.folder_path, filename)

        header = ["Timestamp", "Raw_Area", "Filtered_Area", "Threshold", "Event_Code", extra_column_name]
        
        if len(self.data_rows[0]) > 6:
            header.extend(["Gaze_X", "Gaze_Y"])
            
        try:
            with open(save_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header) # Write Header
                writer.writerows(self.data_rows) # Write all data
            
            print(f"CSV saved locally to {save_path}")

            uploader = DriveUploaderThread(save_path, folder_id=CURRENT_SESSION_DRIVE_FOLDER_ID)
            uploader.finished_signal.connect(lambda name, success: print(f"[Drive] Uploaded {name} successfully!"))
            uploader.error_signal.connect(lambda err: print(f"[Drive] Upload failed: {err}"))
            
            ACTIVE_UPLOAD_THREADS.append(uploader)
            uploader.finished.connect(lambda: ACTIVE_UPLOAD_THREADS.remove(uploader) if uploader in ACTIVE_UPLOAD_THREADS else None)
            
            uploader.start()
            
        except Exception as e:
            print(f"Error saving CSV: {e}")

        

