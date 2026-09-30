using UnityEngine;
using Pupil.Bci;

namespace Pupil.ComApp
{
    /// <summary>
    /// Optional: add to Space Evaders scene so a long PAR (or key) returns to Pupil main menu.
    /// Hub/bar keep running via PupilSession DontDestroyOnLoad.
    /// </summary>
    public sealed class ReturnToPupilMenu : MonoBehaviour
    {
        [SerializeField] bool returnOnLongPar = true;
        [SerializeField] KeyCode debugKey = KeyCode.Escape;

        void OnEnable()
        {
            var hub = PupilSession.Instance != null ? PupilSession.Instance.Hub : FindObjectOfType<PupilBciHub>();
            if (hub != null && returnOnLongPar)
                hub.OnLongPar += Go;
        }

        void OnDisable()
        {
            var hub = PupilSession.Instance != null ? PupilSession.Instance.Hub : FindObjectOfType<PupilBciHub>();
            if (hub != null)
                hub.OnLongPar -= Go;
        }

        void Update()
        {
            if (Input.GetKeyDown(debugKey))
                Go();
        }

        void Go() => PupilSceneRouter.GoMainMenu();
    }
}
