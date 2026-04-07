import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from PyQt5 import QtWidgets

# ----------------CONFIGURATION------------------
# 1. Enter the timestamp of the session you want to recover (from your screenshot)
TARGET_TIMESTAMP = "165831" 

# 2. Enter the path to the folder containing the .txt files
# (Use r"" to handle backslashes on Windows)
DATA_FOLDER = r"C:\Users\jadel\OneDrive\Desktop\University\Magistrale\tesi\GUI_pl\Vittorio_02"
# -----------------------------------------------

def restore_plot():
    print(f"Attempting to restore plot for session: {TARGET_TIMESTAMP}")

    # Based on your previous code's naming convention:
    # "Testing_filt_" contains the Pupil Area values
    # "Testing_Filtered_" contains the Time values
    
    y_path = os.path.join(DATA_FOLDER, f"Testing_filt_{TARGET_TIMESTAMP}.txt")
    x_path = os.path.join(DATA_FOLDER, f"Testing_Filtered_{TARGET_TIMESTAMP}.txt")

    if not os.path.exists(y_path) or not os.path.exists(x_path):
        print("Error: Could not find the data files.")
        print(f"Looking for: {y_path}")
        print(f"Looking for: {x_path}")
        return

    try:
        # Load data
        y_data = np.loadtxt(y_path)
        x_data = np.loadtxt(x_path)

        # Basic validation
        if len(y_data) != len(x_data):
            print(f"Warning: Data length mismatch. Y={len(y_data)}, X={len(x_data)}")
            # Trim to the shorter length to avoid crash
            min_len = min(len(y_data), len(x_data))
            y_data = y_data[:min_len]
            x_data = x_data[:min_len]

        # Adjust time to start at 0
        if len(x_data) > 0:
            x_data = x_data - x_data[0]

        # Generate Plot
        plt.figure(figsize=(10, 6))
        plt.plot(x_data, y_data, label='Filtered Area (Restored)', color='blue')
        
        plt.title(f"Restored Session: {TARGET_TIMESTAMP}")
        plt.xlabel("Time (s)")
        plt.ylabel("Pupil Area")
        plt.legend()
        plt.grid(True)

        # Save
        save_name = f"Restored_Plot_{TARGET_TIMESTAMP}.png"
        save_path = os.path.join(DATA_FOLDER, save_name)
        plt.savefig(save_path)
        print(f"Success! Plot saved to: {save_path}")
        plt.show()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    restore_plot()