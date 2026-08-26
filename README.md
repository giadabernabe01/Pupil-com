# _PUPIL-COM_: A BRAIN-COMPUTER INTERFACE FOR COMMUNICATION AND ENTERTAINMENT, EVEN IN A COMPLETELY LOCKED-IN STATE.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![GUI](https://img.shields.io/badge/GUI-PyQt5-green.svg)
![Domain](https://img.shields.io/badge/Domain-Biomedical%20Signal%20Processing-orange)

>This project's aim is to provide a fully functional BCI that allows communication through the Pupillary Accomodation Reflex (PAR), an autonomic nervous system response voluntarily elicitable through a shift in gaze depth only.
>Each time the user shifts focus from a far to a near target, the pupil reduces its size up to 50-70%: these voluntary constrictions are mapped by the interface as commands, and their duration determines the nature of the command.


## Key features
- **Autonomous BCI Navigation:** Maps voluntary gaze-depth shifts (PAR) into short, long, and extra-long commands.
- **Multi-Device Compatibility:** Integrated streaming support for both **Pupil Core** (Pupil Labs) and **GP3** (Gazepoint).
- **Integrated Applications:**
  - **Training** for threshold calibration and signal detection scoring.
  - **Sì o No :** for supervisor-assisted, binary communication.
  - **Tastiera:** predictive typing keyboard for extended text generation.
  - **Gioco:** interactive 2D game for active engagement and assessment.
- **Live Signal Monitoring:** real-time feedback on pupillary area and constriction thresholds.
- **Personalisation:** parameters adjustable to subject-specific needs.

## Hardware & Software Requirements
- **Hardware:**
  - Commercial Eye Tracker: Pupil Labs Core (via ZMQ) OR Gazepoint GP3 (via Open Gaze API).
  - PC running Windows 10/11.
- **Software Dependencies:**
  - Python 3.8+
  - Pupil Capture (if using Pupil Core) or Gazepoint Control (if using GP3).
 
## Getting started
1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/Pupil-com.git](https://github.com/your-username/Pupil-com.git)
   cd Pupil-com
2. Install required packages
   ```bash
   pip install -r requirements.txt
3. Run the application
   ```bash
   python main.py
   

## GUI overview and documentation
The GUI (in Italian language) is built to allow autonomous use and it can be fully navigated by the user with the PAR, after minimal external intervention to start the session.

For detailed step-by-step instructions on initialisation, eye-tracker configuration, parameter tuning, and full application usage, please refer to the dedicated guide:

--> Read the Full User Guide (USER_GUIDE.md)

## Repository structure
```text
  Pupil-com/
  ├── docs/               # Documentation assets and user guide
  ├── src/                # Source code (GUI, DSP algorithms, IPC handlers)
  │   ├── gui/            # PyQt interface windows and layouts
  │   ├── core/           # Signal processing and eye-tracker API handlers
  │   └── utils/          # Helper scripts and configuration loaders
  ├── USER_GUIDE.md       # Comprehensive step-by-step user manual
  ├── requirements.txt    # Python library dependencies
  ├── main.py             # Application entry point
  ├── LICENSE             # Project license
  └── README.md           # Repository overview
```

## Citation and Acknowledgements
This project was developed in collaboration with the Department of Neuroscience "Rita Levi Montalcini" (University of Turin) and Politecnico di Torino.

If you use this work, codebase, or method in an academic context, please cite:

```bibtex
  @mastersthesis{bernabe2026pupilcom,
    author       = {Giada Bernabè},
    title        = {Pupil-com: a portable pupil-based BCI for autonomous communication in Completely Locked-In State},
    school       = {Politecnico di Torino},
    year         = {2026},
    type         = {Master's Thesis}
  }
```

## LICENSE
This project is released under the MIT license. See the LICENSE file for details.


### Initialisation instructions
Double click on the Pupil-com logo on the PC desktop:

<img width="167" height="168" alt="image" src="https://github.com/user-attachments/assets/c634057d-e297-4492-a052-8dcabe7f1876" />

The interface can run on two different commercial eye-tracking devices (the wearable glass-frame Pupil Core, by Pupil Labs, and the remote camera GP3, by Gazepoint): choose the device you are performing the acquisition on and type the subject's name, or skip for an anonymous session.

<img width="593" height="469" alt="welcome_screen(figure2 13)" src="https://github.com/user-attachments/assets/6d56d7d6-328b-4770-ad7a-17a03896cc47" />

Click the button "Avvia il dispositivo" at the bottom of the screen to start the acquisition via the eye-tracker.

<img width="512" height="459" alt="2 14" src="https://github.com/user-attachments/assets/7b6c0b9c-e2f1-4cd0-a8dc-c6f185dcafe8" />

The third-party application is initialised in an external window that shows the eye-tracking device's camera view. Adjust its position to ensure the user's pupils are correctly detected and the acquisition is stable over time.

<img width="960" height="540" alt="GP3_acq_software(figure 2 7)" src="https://github.com/user-attachments/assets/738f22c8-ffc5-485a-a186-d9cb7d6e368d" />

Maximise the main menu window, make sure the pupillary area (message "Area registrata: ..." and digital eye in the top part of the screen) is being updated live. Click the green button "Dispositivo pronto" to start the scanning view. From now on, the GUI is fully in the user's control.

### Parameters
To adjust parameters according to the subject's needs and physiological response, click the three dots in the upper right corner, to open the settings dialog.

<img width="1279" height="975" alt="image" src="https://github.com/user-attachments/assets/ab3d1605-65a4-4025-ae5c-d35c3574ff63" />

Here, you can adjust the threshold value, commands duration, scanning times and application-specific parameters.

<img width="500" height="638" alt="params" src="https://github.com/user-attachments/assets/09154408-6ad8-44bc-8cef-4fe0bd4b6378" />

### User navigation
All the GUI commands are based on a voluntary pupillary constriction (PAR):
- a short PAR (duration < 3 s);
- a long PAR (duration > 3 s and < 5 s);
- an extra-long PAR (duration > 5 s).

**MAIN MENU**: four applications available. The user must select their choice by performing a PAR when the respective button is highlighted.

<img width="1279" height="975" alt="system_armed_GUI(figure2 15)" src="https://github.com/user-attachments/assets/a856f955-99d6-45f7-b4fa-9ecdaad6d40d" />


**TRAINING**: guided exercise to familiarise with PAR elicitation, settle the most suitable threshold for the subject and make sure the algorithm is correctly detecting constrictions.
Five consecutive PARs are requested by the system and the score is shown at the end, along with a graph of the pupillary area and the instants PAR events were detected.

<img width="1279" height="974" alt="training_result(figure2 16)" src="https://github.com/user-attachments/assets/edc74624-622f-4731-8809-b40a5a27a2e3" />


**SI O NO**: simple binary interface to ask yes/no questions. The external supervisor must ask the question and click a random point on the screen to start the answers scanner mode.
The user may answer the question by selecting their choice when highlighted with a short PAR. 

The pause and exit menu is accessible with a long PAR, and the user must choose between "Resume" and "Exit" with a short PAR when the preferred option is highlighted.

<img width="1279" height="879" alt="yn_interface(figure2 17)" src="https://github.com/user-attachments/assets/07b6dc6f-1344-4e3c-937c-de72f60ef961" />


**TASTIERA**: typing machine with predictive suggestions. The alternate scanner highlights one full row at a time, until the user performs a short PAR to select the current highlight.
Then, the keys in that specific row are highlighted one at a time, and the user must choose the desired character with another short PAR. Each character entry updates the predictive suggestions in the upper part of the keyboard, offering three options for the user to type faster. The user must perform a long PAR to access the suggestions list and a short PAR when the preferred option is highlighted. 

The pause and exit menu is accessible with an extra-long PAR, and the user must choose between "Resume" and "Exit" with a short PAR when the preferred option is highlighted. 

<img width="512" height="389" alt="keyboard_layout(figure2 19)" src="https://github.com/user-attachments/assets/2eea6eb2-7b71-46b6-97bd-4e56faab3716" />


**GIOCO**: a 2D scrolling game in which the user controls a space shuttle with short PARs. The goal is to hit as many scrolling planets as possible by launching the ship with the right timing. The user has 5 Lives at the beginning of the game, loses one each time they miss a planet and gains one every 5 successful planet hits.  

The pause and exit menu is accessible with a long PAR, and the user must choose between "Resume" and "Exit" with a short PAR when the preferred option is highlighted.

<img width="512" height="410" alt="game_layout(figure2 21)" src="https://github.com/user-attachments/assets/7cd72acf-c7c8-4b97-b587-91e7f3c7ce09" />
