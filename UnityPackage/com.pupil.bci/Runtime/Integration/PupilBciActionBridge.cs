using UnityEngine;
using UnityEngine.Events;

namespace Pupil.Bci
{
    /// <summary>
    /// Drop-in bridge for games that previously listened to Python UDP "press".
    /// Subscribe gameplay (e.g. fire / jump) to <see cref="onPress"/> or the C# event.
    /// </summary>
    public sealed class PupilBciActionBridge : MonoBehaviour
    {
        [SerializeField] PupilBciHub hub;
        [SerializeField] bool pauseOnTrackingLost = true;
        [SerializeField] UnityEvent onPress;
        [SerializeField] UnityEvent onTrackingLost;
        [SerializeField] UnityEvent onTrackingOk;

        public event System.Action Pressed;

        /// <summary>
        /// When true, still accepts a legacy UDP listener component if present on the same object.
        /// Leave false when fully on the C# package.
        /// </summary>
        [SerializeField] bool allowLegacyUdpFallback;

        void OnEnable()
        {
            if (hub == null)
                hub = FindObjectOfType<PupilBciHub>();

            if (hub == null)
            {
                Debug.LogError("[PupilBci] ActionBridge: no PupilBciHub found.");
                return;
            }

            hub.OnShortPar += HandlePress;
            hub.OnTrackingLost += HandleLost;
            hub.OnTrackingOk += HandleOk;

            if (allowLegacyUdpFallback)
                Debug.LogWarning("[PupilBci] Legacy UDP fallback flag is on — prefer Hub.OnShortPar only.");
        }

        void OnDisable()
        {
            if (hub == null)
                return;
            hub.OnShortPar -= HandlePress;
            hub.OnTrackingLost -= HandleLost;
            hub.OnTrackingOk -= HandleOk;
        }

        void HandlePress()
        {
            Pressed?.Invoke();
            onPress?.Invoke();
        }

        void HandleLost()
        {
            if (pauseOnTrackingLost)
                Time.timeScale = 0f;
            onTrackingLost?.Invoke();
        }

        void HandleOk()
        {
            if (pauseOnTrackingLost)
                Time.timeScale = 1f;
            onTrackingOk?.Invoke();
        }
    }
}
