import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import os

def main():
    # Hide the empty Tkinter background window
    root = tk.Tk()
    root.withdraw()

    # Open a standard file selection dialog looking for CSVs
    file_path = filedialog.askopenfilename(
        title="Seleziona il file CSV da analizzare",
        filetypes=[("CSV Files", "*.csv")]
    )

    if not file_path:
        print("Nessun file selezionato. Chiusura in corso...")
        return

    print(f"Caricamento dati da: {os.path.basename(file_path)}...")
    
    # Read the CSV file
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Errore durante la lettura del CSV: {e}")
        return

    # Clean up column names (removes accidental spaces from the CSV headers)
    df.columns = df.columns.str.strip()

    # Verify required columns exist
    if not {'Filtered_Area', 'Threshold'}.issubset(df.columns):
        print("Il CSV non contiene le colonne 'Filtered_Area' e 'Threshold'.")
        return

    # Create the interactive Matplotlib figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot the main data streams using the row index (Frames) as the X-axis
    ax.plot(df.index, df['Filtered_Area'], label='Filtered Area', color='blue', linewidth=1.5)
    ax.plot(df.index, df['Threshold'], label='Threshold', color='red', linestyle='--', linewidth=1.5)

    # Optional: Plot Vertical Lines for Game Events (Launch, Score, etc.)
    if 'Event_Code' in df.columns:
        # Find rows where Event_Code is not empty, '0', or 'MENU'
        active_events = df[
            (df['Event_Code'].notna()) & 
            (df['Event_Code'].astype(str).str.strip() != '0') & 
            (df['Event_Code'].astype(str).str.strip() != 'MENU')
        ]
        
        for idx, row in active_events.iterrows():
            event_name = str(row['Event_Code']).strip()
            
            # Color coding events for easier reading
            if 'LAUNCH' in event_name:
                color = 'green'
            elif 'SCORE' in event_name or 'LIFE_GAIN' in event_name:
                color = 'gold'
            else:
                color = 'purple'
                
            ax.axvline(x=idx, color=color, linestyle=':', alpha=0.8)
            # Add text label at the top of the line
            ax.text(idx, ax.get_ylim()[1]*0.95, f" {event_name}", 
                    rotation=90, verticalalignment='top', color=color, fontsize=8, fontweight='bold')

    # Customize Layout
    ax.set_title(f"Analisi Offline: {os.path.basename(file_path)}")
    ax.set_xlabel("Frames")
    ax.set_ylabel("Pupil Area")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    
    # Show the interactive window!
    print("Mostrando il grafico interattivo. Chiudi la finestra per terminare lo script.")
    plt.show()

if __name__ == "__main__":
    main()