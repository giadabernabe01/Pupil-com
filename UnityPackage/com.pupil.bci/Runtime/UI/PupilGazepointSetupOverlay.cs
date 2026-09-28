using System.Collections;
using UnityEngine;

namespace Pupil.Bci
{
    /// <summary>
    /// Setup coach: keep Gazepoint in front (windowed) until eye is tracked / Ready.
    /// </summary>
    public sealed class PupilGazepointSetupOverlay : MonoBehaviour
    {
        [SerializeField] PupilBciHub hub;
        [SerializeField] bool hideWhenReady = true;
        [SerializeField] bool autoLaunchOnce = true;
        [Tooltip("If true, maximize Gazepoint; leave false for a normal window.")]
        [SerializeField] bool maximizeGazepoint = false;
        [SerializeField] float autoLaunchAfterSeconds = 1.2f;
        [SerializeField] float reconnectAfterLaunchSeconds = 2.5f;
        [SerializeField] float refocusWhileWaitingEvery = 2.0f;

        string _launchFeedback = "";
        float _feedbackUntil;
        bool _autoLaunchTried;
        float _nextRefocus;
        Coroutine _reconnectCo;

        void OnEnable()
        {
            if (hub == null)
                hub = GetComponent<PupilBciHub>() ?? FindObjectOfType<PupilBciHub>();
            _autoLaunchTried = false;
            _nextRefocus = 0f;
        }

        void OnDisable()
        {
            if (_reconnectCo != null)
            {
                StopCoroutine(_reconnectCo);
                _reconnectCo = null;
            }
        }

        void Update()
        {
            if (hub == null) return;

            // Auto-open Gazepoint if missing
            if (autoLaunchOnce && !_autoLaunchTried
                && hub.Phase == PupilBciPhase.WaitingForGazepoint
                && !hub.GazepointProcessRunning
                && Time.unscaledTime >= autoLaunchAfterSeconds)
            {
                _autoLaunchTried = true;
                TryLaunchAndFocus();
            }

            // Keep Gazepoint in front until eye is good / Ready
            if (hub.Phase == PupilBciPhase.WaitingForGazepoint
                || hub.Phase == PupilBciPhase.WaitingForValidEye)
            {
                if (Time.unscaledTime >= _nextRefocus)
                {
                    _nextRefocus = Time.unscaledTime + Mathf.Max(1f, refocusWhileWaitingEvery);
                    hub.FocusGazepointWindow(maximize: maximizeGazepoint);
                }
            }
        }

        void OnGUI()
        {
            if (hub == null) return;
            if (hideWhenReady && hub.IsReady) return;

            var phase = hub.Phase;
            if (phase == PupilBciPhase.Ready || phase == PupilBciPhase.Idle)
                return;
            // TrackingLost uses dedicated pause overlay
            if (phase == PupilBciPhase.TrackingLost)
                return;

            float w = Mathf.Min(560f, Screen.width - 40f);
            float h = 300f;
            var r = new Rect((Screen.width - w) * 0.5f, 24f, w, h);
            GUI.Box(r, "Setup Gazepoint / Pupil BCI");

            var inner = new Rect(r.x + 16f, r.y + 36f, r.width - 32f, r.height - 48f);
            GUILayout.BeginArea(inner);

            GUILayout.Label($"Stato: {hub.StatusMessage}", GUI.skin.box);
            GUILayout.Space(6);
            GUILayout.Label(hub.SetupHint ?? "");
            GUILayout.Space(6);
            GUILayout.Label(
                hub.GazepointProcessRunning
                    ? "Gazepoint: aperto — posiziona l'occhio fino a segnale stabile"
                    : "Gazepoint: NON aperto — lo avvio in finestra");

            if (Time.unscaledTime < _feedbackUntil && !string.IsNullOrEmpty(_launchFeedback))
            {
                GUILayout.Space(6);
                GUILayout.Label(_launchFeedback, GUI.skin.box);
            }

            GUILayout.FlexibleSpace();
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Riprova connessione", GUILayout.Height(36)))
                hub.RetryConnection();
            if (GUILayout.Button("Apri Gazepoint (finestra)", GUILayout.Height(36)))
                TryLaunchAndFocus();
            GUILayout.EndHorizontal();

            GUILayout.EndArea();
        }

        void TryLaunchAndFocus()
        {
            if (hub == null) return;
            if (hub.TryOpenGazepoint(out var err))
            {
                _launchFeedback = "Gazepoint in finestra — inquadra l'occhio, poi aspetta Ready.";
                _feedbackUntil = Time.unscaledTime + 6f;
                if (_reconnectCo != null)
                    StopCoroutine(_reconnectCo);
                _reconnectCo = StartCoroutine(ReconnectAfterLaunch());
            }
            else
            {
                _launchFeedback = err ?? "Avvio/focus fallito.";
                _feedbackUntil = Time.unscaledTime + 8f;
                Debug.LogWarning("[PupilBci] " + _launchFeedback);
            }
        }

        IEnumerator ReconnectAfterLaunch()
        {
            yield return new WaitForSecondsRealtime(Mathf.Max(1f, reconnectAfterLaunchSeconds));
            if (hub != null)
            {
                hub.FocusGazepointWindow(maximize: maximizeGazepoint);
                hub.RetryConnection();
            }
            _reconnectCo = null;
        }
    }
}
