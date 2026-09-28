# Integrate PupilBci into Space Evaders

The built `.exe` folders on Desktop are **not** the Unity project. Open the **Space Evaders Unity project source** (folder with `Assets/` and `Packages/`), then:

## 1. Add the package

Package Manager → **+** → **Add package from disk…** → select:

`Pupil-com/UnityPackage/com.pupil.bci/package.json`

## 2. Scene setup

1. Create GameObject `PupilBci`.
2. Add **Pupil Bci Hub**.
3. Create asset: right-click → **Create → Pupil BCI → Config**, assign to the Hub.
4. Add **Pupil Bci Action Bridge** (optional) and wire `onPress` to the same gameplay method that used to fire on UDP press.

## 3. Replace UDP input

Find the component that listens for Python UDP (`press` / `PupilUdp` / similar).

**Before (conceptual):**

```csharp
// UDP JSON { "type": "press" } → InjectPress()
```

**After:**

```csharp
using Pupil.Bci;

public class PlayerActionFromPar : MonoBehaviour
{
    [SerializeField] PupilBciHub hub;

    void OnEnable() => hub.OnShortPar += InjectPress;
    void OnDisable() => hub.OnShortPar -= InjectPress;

    void InjectPress()
    {
        // same body as former UDP press handler
    }
}
```

Or use `PupilBciActionBridge.onPress` in the Inspector.

## 4. Rollback

Keep the UDP listener disabled (not deleted) until the package is validated in lab.

## 5. Remove Python for this game path

Once PAR works in-editor and in builds:

- Do not launch Pupil-com / `UnityGameBridge` for Space Evaders.
- Gazepoint Control must still be running (hardware sidecar).
