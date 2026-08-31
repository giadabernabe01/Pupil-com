# _PUPIL-COM_ OFFICIAL DOCUMENTATION

This document provides a users manual for *Pupil-com* setup, from first installation to session initialisation and GUI navigation. Furthermore, it offers technical insights on the system's architecture and full state-machine diagrams for the core modules.

## Table of Contents
1. [Users guide](#1-users-guide)
   - [Installation and updates](#installation-updates)
   - [Hardware Setup](#hardware-setup)
   - [Session Initialisation](#session-initialisation)
   - [GUI Navigation](#GUI-navigation)
2. [System Architecture](#2-system-architecture)
3. [State Machines Diagrams](#3-state-machines-diagrams)
    - [Training Module](#training-module)
    - [Yes/No Module](#yes-no-module)
    - [Keyboard Module](#keyboard-module)
    - [Game Module (Space Shuttle)](#game-module)
4. [Data Logging and Output](#data-logging-and-output)
  
---

## 1. Users guide

### Installation and updates
_Pupil-com_ can be run either as a standalone application or directly from the source code.

- Standalone Application:
   1. Download the latest `.exe` release from the GitHub repository. No installation is required.
   2. Place the executable in a dedicated folder on your PC. Make sure the `credentials.json` file provided by the developer is in the same folder.
   3. **First-time setup:** On the very first launch, a browser window will pop up asking for Google Drive authorization. Log in with your Google account and grant permissions. A `token.json` file will be automatically generated in your folder to keep you logged in for future sessions.
   4. Updates are managed by downloading the latest `.exe` release and replacing the old executable in the same folder. Your tokens and settings will remain intact.
- Source Code: Ensure Python 3.8 (or above) is installed on your machine. Clone the repository and install all necessary dependencies by opening a terminal in the project directory and running pip install -r requirements.txt.

### Hardware Setup
The communication system design meets standard BCI requirements and integrates features specifically required for PAR performance and monitoring. The setup comprises the following elements:

- *Acquisition module*: The eye-tracking device (wearable or remote), performing live pupillometry and providing real-time data.

- *Computational unit*: The PC, receiving a live data stream from the acquisition module and running the program for the graphical user interface (GUI).

- *GUI display*: A monitor, showing a scanning-mode interface that the subject interacts with, and working as the far target.

- *Audio output*: External speakers to vocalise cues and selections within the GUI.

- *External input devices*: Mouse and keyboard for the initialisation of the GUI and fine-tuning of parameters by the researcher or caregiver.

- *Universal laboratory stand*: Holding the close target, a transparent plexiglass rectangle with a blue circular dot that the subject fixates their gaze on.

- *Seat*: For the subject to comfortably sit and maintain stillness while shifting their depth of focus.

<img width="2816" height="1536" alt="general_setup (figure2 1)" src="https://github.com/user-attachments/assets/458929bf-b1ce-45fa-8f00-e353ae901148" />


_Pupil-com_ currently supports Pupil Core (wearable glasses) and Gazepoint GP3 (remote tripod-mounted tracker) as acquisition modules.

- Pupil Core: Place the headset on the user's face and connect the device to your PC via USB. Launch the native Pupil Capture software and ensure the eye camera is focused and properly detecting the pupil before enabling Pupil-com's Main Menu.

- Gazepoint GP3: Mount the tracker on its tripod and connect it via USB. Launch the Gazepoint Control software, and ensure the server is active before enabling Pupil-com's Main Menu.

### Session Initialisation
Run main.py script (or double click on the Pupil-com logo on the PC desktop):

<img width="167" height="168" alt="image" src="https://github.com/user-attachments/assets/c634057d-e297-4492-a052-8dcabe7f1876" />

A welcome dialog opens up: choose the eye-tracking device you are performing the acquisition on and type the subject's name, or press skip for an anonymous session.

<img width="593" height="469" alt="welcome_screen(figure2 13)" src="https://github.com/user-attachments/assets/6d56d7d6-328b-4770-ad7a-17a03896cc47" />

Click the button "Avvia il dispositivo" at the bottom of the screen to start the acquisition via the eye-tracker.

<img width="512" height="459" alt="2 14" src="https://github.com/user-attachments/assets/7b6c0b9c-e2f1-4cd0-a8dc-c6f185dcafe8" />

The third-party application is initialised in an external window that shows the eye-tracking device's camera view. Adjust its position to ensure the user's pupils are correctly detected and the acquisition is stable over time.

<img width="960" height="540" alt="GP3_acq_software(figure 2 7)" src="https://github.com/user-attachments/assets/738f22c8-ffc5-485a-a186-d9cb7d6e368d" />

Maximise the main menu window, make sure the pupillary area (message "Area registrata: ..." and digital eye in the top part of the screen) is being updated live. Click the green button "Dispositivo pronto" to start the scanning view. From now on, the GUI is fully in the user's control.

## Parameters
To adjust parameters according to the subject's needs and physiological response, click the three dots in the upper right corner, to open the settings dialog.

<img width="1279" height="975" alt="image" src="https://github.com/user-attachments/assets/ab3d1605-65a4-4025-ae5c-d35c3574ff63" />

Here, you can adjust the threshold value, commands duration, scanning times and application-specific parameters.

<img width="500" height="638" alt="params" src="https://github.com/user-attachments/assets/09154408-6ad8-44bc-8cef-4fe0bd4b6378" />

## User navigation
All the GUI commands are based on a voluntary pupillary constriction (PAR):
- a short PAR (duration < 3 s);
- a long PAR (duration > 3 s and < 5 s);
- an extra-long PAR (duration > 5 s).

### MAIN MENU 
The main menu features four applications. The user must select their choice by performing a PAR when the respective button is highlighted.

<img width="1279" height="975" alt="system_armed_GUI(figure2 15)" src="https://github.com/user-attachments/assets/a856f955-99d6-45f7-b4fa-9ecdaad6d40d" />


### TRAINING
It consists of a guided exercise to familiarise with PAR elicitation, settle the most suitable threshold for the subject and make sure the algorithm is correctly detecting constrictions.
Five consecutive PARs are requested by the system and the score is shown at the end, along with a graph of the pupillary area and the instants PAR events were detected.

<img width="1279" height="974" alt="training_result(figure2 16)" src="https://github.com/user-attachments/assets/edc74624-622f-4731-8809-b40a5a27a2e3" />


### SI O NO 
The application is a simple binary interface to ask yes/no questions. The external supervisor must ask the question and click a random point on the screen to start the answers scanner mode.
The user may answer the question by selecting their choice when highlighted with a short PAR. 

The pause and exit menu is accessible with a long PAR, and the user must choose between "Resume" and "Exit" with a short PAR when the preferred option is highlighted.

<img width="1279" height="879" alt="yn_interface(figure2 17)" src="https://github.com/user-attachments/assets/07b6dc6f-1344-4e3c-937c-de72f60ef961" />


### TASTIERA
The application is a typing machine with predictive suggestions. The alternate scanner highlights one full row at a time, until the user performs a short PAR to select the current highlight.
Then, the keys in that specific row are highlighted one at a time, and the user must choose the desired character with another short PAR. Each character entry updates the predictive suggestions in the upper part of the keyboard, offering three options for the user to type faster. The user must perform a long PAR to access the suggestions list and a short PAR when the preferred option is highlighted. 

The pause and exit menu is accessible with an extra-long PAR, and the user must choose between "Resume" and "Exit" with a short PAR when the preferred option is highlighted. 

<img width="512" height="389" alt="keyboard_layout(figure2 19)" src="https://github.com/user-attachments/assets/2eea6eb2-7b71-46b6-97bd-4e56faab3716" />


### GIOCO
The application is a 2D scrolling game in which the user controls a space shuttle with short PARs. The goal is to hit as many scrolling planets as possible by launching the ship with the right timing. The user has 5 Lives at the beginning of the game, loses one each time they miss a planet and gains one every 5 successful planet hits.  

The pause and exit menu is accessible with a long PAR, and the user must choose between "Resume" and "Exit" with a short PAR when the preferred option is highlighted.

<img width="512" height="410" alt="game_layout(figure2 21)" src="https://github.com/user-attachments/assets/7cd72acf-c7c8-4b97-b587-91e7f3c7ce09" />

---

## 2. System Architecture
Pupil-com is built on **PyQt5** and utilises a multi-threaded architecture to decouple the UI from the high-frequency eye-tracking data streams (130Hz or 60Hz depending on the hardware).
Data is routed through:
1. **Hardware Receivers** (`QThread` for Pupil Core / Gazepoint GP3)
2. **Filters & Monitors** (`AreaFilter`, `ConstrictionMonitor`)
3. **Application State Machines** (The active PyQt Widgets)
4. **Data Savers** (`SessionLogger`, `DataPlotter`, `DataSaver`, `DriveUploaderThread`)

---

## 3. State Machine diagrams
The GUI relies on gaze-independent pupil constrictions. To achieve robust control without physical buttons, each module operates as a strictly timed Finite State Machine (FSM).

### Training Module
The Training Widget is used to calibrate the user's voluntary constriction and evaluate their performance over 5 trials.

```mermaid
stateDiagram-v2
    direction TB
    [*] --> INITIALISATION
    
    INITIALISATION --> BASELINE : Click "START"
    BASELINE --> INSTRUCTION_NEAR : Wait t_init (Baseline calc.)
    
    INSTRUCTION_NEAR --> HOLDING : Audio Cue Played
    HOLDING --> INSTRUCTION_FAR : Wait task duration\n(Success/Fail recorded)
    
    INSTRUCTION_FAR --> COOLDOWN : Audio Cue Played
    COOLDOWN --> INSTRUCTION_NEAR : Next Trial (if < 5)
    
    COOLDOWN --> FINISHED : All 5 Trials Complete
    FINISHED --> COMPLETED_IDLE : Show Score
    COMPLETED_IDLE --> INITIALISATION : Wait 5s
```

### Yes/No Module
```mermaid
stateDiagram-v2
    direction TB
    [*] --> INITIALISATION
    
    INITIALISATION --> IDLE : Wait t_init
    IDLE --> SCANNING : Mouse Click
    
    state "Alternate Scanning" as SCANNING {
        HIGHLIGHT_YES --> HIGHLIGHT_NO : Wait scan duration
        HIGHLIGHT_NO --> HIGHLIGHT_YES : Wait scan duration
    }
    
    SCANNING --> SELECTION_MADE : Short Constriction
    SELECTION_MADE --> IDLE : Reset
    
    SCANNING --> WAIT_RELEASE : Long Constriction
    WAIT_RELEASE --> PAUSED : Pupil Relaxes
    
    state "Pause Menu" as PAUSED {
        HIGHLIGHT_RESUME --> HIGHLIGHT_EXIT : Wait scan duration
        HIGHLIGHT_EXIT --> HIGHLIGHT_RESUME : Wait scan duration
    }
    
    PAUSED --> SCANNING : Short Constriction (Resume)
    PAUSED --> [*] : Short Constriction (Exit to Main Menu)
```


### Keyboard Module
```mermaid
stateDiagram-v2
    direction TB
    [*] --> INITIALISATION
    
    INITIALISATION --> KEYBOARD_ROW : Wait t_init
    
    state "Scanning Loop" as Scanning {
        KEYBOARD_ROW --> KEYBOARD_COL : Short Constriction (Select Row)
        KEYBOARD_ROW --> SUGGESTIONS : Long Constriction (Skip to Words)
        
        KEYBOARD_COL --> KEYBOARD_ROW : Short Constriction (Type Letter)
        KEYBOARD_COL --> SUGGESTIONS : Long Constriction (Skip to Words)
        
        SUGGESTIONS --> KEYBOARD_ROW : Short (Pick Word) / Long (Cancel)
    }
    
    state "Interruption / Pause" as PauseMenu {
        WAIT_RELEASE --> PAUSED : Pupil Relaxes
        PAUSED --> COOLDOWN : Short Constriction on "RESUME"
        PAUSED --> EXIT : Short Constriction on "EXIT"
    }
    
    Scanning --> WAIT_RELEASE : Extra-Long Constriction (Any time)
    COOLDOWN --> Scanning : Cooldown duration ends
    EXIT --> [*] : Return to Main Menu
```

### Shuttle Game Module
```mermaid
stateDiagram-v2
    direction TB
    [*] --> INITIALISATION
    
    INITIALISATION --> WAIT_INPUT : Wait t_init (Baseline calc.)
    WAIT_INPUT --> STARTING : Short/Long Constriction (Menu Selection)
    
    STARTING --> GAME_ACTIVE : Pygame Window Opens
    
    state GAME_ACTIVE {
        direction LR
        Flying --> Paused : Long Constriction
        Paused --> Flying : Short Constriction
    }
    
    GAME_ACTIVE --> WAIT_EXIT : Lives = 0 (Game Over)
    WAIT_EXIT --> COOLDOWN : Wait for exit gesture
    COOLDOWN --> INITIALISATION : Wait t_cool
```

## 4. Data Logging and Storage
To allow post-hoc analysis, all the acquisition files are stored locally in the _Experimental_Results_ folder and automatically pushed to the designated Google Drive folder using the _DriveUploaderThread_. Each session is saved according to these naming rules:
- "SUBJECTNAME_XX" (XX indicating the session number with that same SUBJECTNAME) for sessions started by inserting a username.
- "SESSIONTIMESTAMP" for anonymous sessions started by pressing the skip button.

For each session, a detailed activity logfile is accessible, and for each application use are available:
- a timestamped .jpg figure displaying the pupillary area vs time and instants of short (red), long (green) and extra-long (black) PAR detected, along with the adaptive threshold value vs time. Useful for immediate inspection of the signal.
- a .csv file, for deeper analysis of the signal and the system's response, inlcuding:
    - Timestamp: Synchronised relative time.
    - Raw_Area: Unfiltered pupil area from the hardware.
    - Filtered_Area: Event-Based and Moving Average filtered area.
    - Threshold & Exit_Threshold: Dynamic thresholds for the specific frame.
    - Event_Code: System state or constriction type detected (0=None, 1=Short, 2=Long, 3=Extra).
