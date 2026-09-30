using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Pupil.ComApp
{
    public static class PupilUiBootstrap
    {
        /// <summary>
        /// Overlay UI needs an EventSystem for mouse clicks.
        /// A camera removes the Game view "No cameras rendering" warning.
        /// </summary>
        public static void EnsureInputAndCamera()
        {
            if (Object.FindObjectOfType<EventSystem>() == null)
            {
                var es = new GameObject("EventSystem");
                es.AddComponent<EventSystem>();
                es.AddComponent<StandaloneInputModule>();
            }

            if (Camera.main == null && Object.FindObjectOfType<Camera>() == null)
            {
                var camGo = new GameObject("PupilUiCamera");
                var cam = camGo.AddComponent<Camera>();
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(0.08f, 0.08f, 0.1f, 1f);
                cam.orthographic = true;
                cam.cullingMask = 0; // UI Overlay doesn't need world rendering
                cam.depth = -100;
            }
        }

        public static bool ConfirmPressed() =>
            Input.GetKeyDown(KeyCode.Return)
            || Input.GetKeyDown(KeyCode.KeypadEnter)
            || Input.GetKeyDown(KeyCode.Space);

        public static bool BackPressed() =>
            Input.GetKeyDown(KeyCode.Escape)
            || Input.GetKeyDown(KeyCode.Backspace);

        /// <summary>Vertical lists: Up/Down / W/S. Horizontal: Left/Right / A/D.</summary>
        public static int NavDelta(bool horizontal = false)
        {
            if (horizontal)
            {
                if (Input.GetKeyDown(KeyCode.RightArrow) || Input.GetKeyDown(KeyCode.D)) return 1;
                if (Input.GetKeyDown(KeyCode.LeftArrow) || Input.GetKeyDown(KeyCode.A)) return -1;
            }
            else
            {
                if (Input.GetKeyDown(KeyCode.DownArrow) || Input.GetKeyDown(KeyCode.S)) return 1;
                if (Input.GetKeyDown(KeyCode.UpArrow) || Input.GetKeyDown(KeyCode.W)) return -1;
            }
            return 0;
        }
    }
}
