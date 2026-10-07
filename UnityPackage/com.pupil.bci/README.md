# Pupil BCI (`com.pupil.bci`)

Unity package: **Gazepoint → filter → pupil constriction (PAR) → C# events**.

This package is **BCI only** (connection + detection + live bar helpers).  
The full Pupil-com app (menu / training / sì-no / tastiera) lives in the Unity project as **scenes** — see `UnityPupilComApp/` in this repo.

## Install

1. Package Manager → **+ → Add package from disk…**
2. Select `UnityPackage/com.pupil.bci/package.json`
3. Add **Pupil Bci Hub** (+ Config) to a GameObject, or let the app session create it.

## API (`PupilBciHub`)

| Member | Meaning |
|--------|---------|
| `OnShortPar` | Short constriction |
| `OnLongPar` | Long constriction (off by default in Config) |
| `OnTrackingLost` / `OnTrackingOk` | Signal timeout / recovery |
| `OnSample` | Live area / threshold |
| `TryOpenGazepoint` / `FocusGazepointWindow` | Launch / focus Gazepoint |

## Requirements

- Windows + Gazepoint Control on `127.0.0.1:4242`
