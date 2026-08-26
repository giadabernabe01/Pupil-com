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
This project is released under the MIT license. See the [LICENSE](LICENSE) file for details.
