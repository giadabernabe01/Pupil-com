import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import tkinter as tk
from tkinter import filedialog, messagebox
import os

def main():
    # Hide the empty Tkinter background window
    root = tk.Tk()
    root.withdraw()

    # Create the interactive Matplotlib figure ONCE before the loop
    fig, ax = plt.subplots(figsize=(12, 6))
    
    file_count = 0
    loaded_files = []
    
    # Get a list of distinct colors so each file has its own color
    colors = cm.get_cmap('tab10').colors

    while True:
        # Open a standard file selection dialog looking for CSVs
        file_path = filedialog.askopenfilename(
            title="Seleziona il file CSV da analizzare",
            filetypes=[("CSV Files", "*.csv")]
        )

        # If user clicks "Cancel" on the file dialog, exit the loop
        if not file_path:
            break

        filename = os.path.basename(file_path)
        print(f"Caricamento dati da: {filename}...")
        
        # Read the CSV file
        try:
            df = pd.read_csv(file_path)
            
            # Clean up column names (removes accidental spaces from the CSV headers)
            df.columns = df.columns.str.strip()

            # Verify required columns exist
            if not {'Filtered_Area', 'Threshold'}.issubset(df.columns):
                print(f"ATTENZIONE: Il CSV '{filename}' non contiene le colonne richieste. Verrà saltato.")
                continue

            loaded_files.append(filename)
            
            # Pick a unique color for this specific file
            file_color = colors[file_count % len(colors)]

            # Plot the main data streams using the row index (Frames) as the X-axis
            # We append the filename to the label so the legend tells us which is which
            ax.plot(df.index, df['Filtered_Area'], label=f'Filtered ({filename})', color=file_color, linewidth=1.5)
            ax.plot(df.index, df['Threshold'], label=f'Threshold ({filename})', color=file_color, linestyle='--', linewidth=1.5, alpha=0.7)

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
                        c = 'green'
                    elif 'SCORE' in event_name or 'LIFE_GAIN' in event_name:
                        c = 'gold'
                    else:
                        c = 'purple'
                        
                    ax.axvline(x=idx, color=c, linestyle=':', alpha=0.5)
                    # Add text label at the top of the line
                    ax.text(idx, ax.get_ylim()[1]*0.95, f" {event_name}", 
                            rotation=90, verticalalignment='top', color=c, fontsize=8, fontweight='bold')

            file_count += 1
            
        except Exception as e:
            print(f"Errore durante la lettura del CSV {filename}: {e}")

        # Ask the user if they want to load another file on top of this one
        add_another = messagebox.askyesno("Aggiungi file", "Vuoi aggiungere un altro file CSV allo stesso grafico?")
        
        if not add_another:
            break # Exit the loop if they say NO

    # Only show the plot if at least one file was successfully loaded
    if file_count > 0:
        # Customize Layout
        ax.set_title(f"Analisi Offline: {len(loaded_files)} sessioni sovrapposte")
        ax.set_xlabel("Frames")
        ax.set_ylabel("Pupil Area")
        
        # Shrink the font size of the legend slightly so it doesn't block the screen if you load 5+ files
        ax.legend(loc="upper right", fontsize='small')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        
        # Show the interactive window!
        print("Mostrando il grafico interattivo. Chiudi la finestra per terminare lo script.")
        plt.show()
    else:
        print("Nessun file elaborato. Chiusura in corso...")

if __name__ == "__main__":
    main()