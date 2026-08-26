# _PUPIL-COM_: A BRAIN-COMPUTER INTERFACE FOR COMMUNICATION AND ENTERTAINMENT, EVEN IN A COMPLETELY LOCKED-IN STATE.

This project's aim is to provide a fully functional BCI that allows communication through the Pupillary Accomodation Reflex (PAR), an autonomic nervous system response voluntarily elicitable through a shift in gaze depth only.

Each time the user shifts focus from a far to a near target, the pupil reduces its size up to 50-70%: these voluntary constrictions are mapped by the interface as commands, and their duration determines the nature of the command (link to "commands" section).

## GUI overview
The GUI (in Italian language) is built to allow autonomous use and it can be fully navigated by the user with the PAR, after minimal external intervention to start the session.

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

<img width="1279" height="879" alt="yn_interface(figure2 17)" src="https://github.com/user-attachments/assets/07b6dc6f-1344-4e3c-937c-de72f60ef961" />


**TASTIERA**: typing machine with predictive suggestions. The alternate scanner highlights one full row at a time, until the user performs a short PAR to select the current highlight.
Then, the keys in that specific row are highlighted one at a time, and the user must choose the desired character with another short PAR.

