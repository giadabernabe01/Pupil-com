using UnityEngine;

namespace Pupil.Bci
{
    /// <summary>
    /// Example replacement for Space Evaders' UDP "press" listener.
    /// Copy this pattern into the game project (or attach this component and assign Hub + gameplay callback).
    /// </summary>
    public sealed class SpaceEvadersParInputExample : MonoBehaviour
    {
        [SerializeField] PupilBciHub hub;
        [Tooltip("Assign the method that used to run when Python sent UDP press.")]
        [SerializeField] UnityEngine.Events.UnityEvent onParPress;

        void OnEnable()
        {
            if (hub == null)
                hub = FindObjectOfType<PupilBciHub>();
            if (hub != null)
                hub.OnShortPar += HandlePar;
        }

        void OnDisable()
        {
            if (hub != null)
                hub.OnShortPar -= HandlePar;
        }

        void HandlePar()
        {
            onParPress?.Invoke();
        }
    }
}
