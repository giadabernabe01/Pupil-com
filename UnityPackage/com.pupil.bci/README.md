# Pupil BCI (`com.pupil.bci`)

Unity package: **Gazepoint → filter → pupil constriction (PAR) → C# events**.

Scope is intentionally small — not a port of the full Pupil-com PyQt app.

## Install in a Unity project

1. Open **Window → Package Manager**
2. **+ → Add package from disk…**
3. Select this folder’s `package.json`:
   `…/Pupil-com/UnityPackage/com.pupil.bci/package.json`
4. Add an empty GameObject, attach **Pupil Bci Hub**, assign a **Pupil Bci Config** asset (Create → Pupil BCI → Config).

## Public API (`PupilBciHub`)

| Member | Meaning |
|--------|---------|
| `OnShortPar` | Short constriction (game “press”) |
| `OnLongPar` | Long constriction (off by default) |
| `OnTrackingLost` / `OnTrackingOk` | Signal timeout / recovery |
| `OnSample` | Every processed frame (area, threshold, …) |
| `FilteredArea`, `Threshold`, `IsUnderThreshold` | Live values |

## Wire Space Evaders

Replace UDP `press` listeners with:

```csharp
hub.OnShortPar += () => { /* same as former UDP press */ };
```

See `Runtime/Integration/PupilBciActionBridge.cs` for a drop-in pattern, and `Samples~/BasicParDemo/`.

## Requirements

- Gazepoint Control running, TCP `127.0.0.1:4242`
- ENABLE pupil + BPOG streams (the client sends SET commands on connect)

## Not included

Training UI, keyboard, Shuttle, Drive upload, Pupil Labs Core.
