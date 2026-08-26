# _PUPIL-COM_ USERS GUIDE
## Initialisation instructions
Run main.py script (or double click on the Pupil-com logo on the PC desktop):

<img width="167" height="168" alt="image" src="https://github.com/user-attachments/assets/c634057d-e297-4492-a052-8dcabe7f1876" />

The interface runs on two different commercial eye-tracking devices (the wearable glass-frame Pupil Core, by Pupil Labs, and the remote camera GP3, by Gazepoint): choose the device you are performing the acquisition on and type the subject's name, or skip for an anonymous session.

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

## Post-hoc analysis
Each session is saved in the "Experimental Results" folder according to these naming rules:
- "SUBJECTNAME_XX" (XX indicating the session number with that same SUBJECTNAME) for sessions started by inserting a username.
- "SESSIONTIMESTAMP" for anonymous sessions started by pressing the skip button.

For each session, a detailed activity logfile is accessible, and for each application use are available:
- a timestamped .jpg figure displaying the pupillary area vs time and instants of short (red), long (green) and extra-long (black) PAR detected, along with the adaptive threshold value vs time. Useful for immediate inspection of the signal.
- a .csv file including raw and filtered area signal through the entire acquisition, along with threshold value, event type, and extra columns conveying application-specifi information (commands, actions etc.). Useful for deeper analysis of the signal and the system's response.
