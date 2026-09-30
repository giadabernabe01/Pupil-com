# Pupil-com App (Unity scenes) — NOT the BCI plugin

This folder is the **application** (menu + training + sì/no + tastiera).  
The **plugin** `com.pupil.bci` stays Gazepoint + PAR only.

## Install into Space Evaders Unity project

1. Ensure package `com.pupil.bci` is already added (Package Manager → from disk).
2. Copy `UnityPupilComApp/Assets/PupilComApp/` into your Unity project `Assets/PupilComApp/`.
3. Menu **Pupil Com → Create App Scenes + Build Settings**  
   Creates:
   - `Pupil_MainMenu`
   - `Pupil_Training`
   - `Pupil_YesNo`
   - `Pupil_Keyboard`
4. On `MainMenuController`, set **Space Evaders Scene** to the **exact name** of your existing game scene (e.g. `Prototype_GalaxyCampaign`).
5. File → Build Settings: keep that game scene in the list; put `Pupil_MainMenu` first if you want the app to boot there.
6. Optional: add `ReturnToPupilMenu` on the Space Evaders scene (long PAR / Esc → main menu).

## Navigation

Scenes load with `SceneManager`.  
`PupilSession` (Hub + barra + voce + Gazepoint) is `DontDestroyOnLoad` and survives scene changes.
