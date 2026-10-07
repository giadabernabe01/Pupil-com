using System.Collections;
using UnityEngine;

namespace Pupil.Bci
{
    /// <summary>
    /// Setup coach for Gazepoint. Can be dismissed so the app stays fully usable
    /// with keyboard/mouse when no eye-tracker is present (development).
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
        [Tooltip("Allow dismissing the overlay and using the app with keyboard/mouse only.")]
        [SerializeField] bool allowContinueWithoutDevice = true;
        [Tooltip("After this many seconds without a good link, stop stealing window focus.")]
        [SerializeField] float stopFocusStealAfterSec = 4f;

        string _launchFeedback = "";
        float _feedbackUntil;
        bool _autoLaunchTried;
        float _nextRefocus;
        float _enabledAt;
        bool _dismissed;
        Coroutine _reconnectCo;

        public bool IsDismissed => _dismissed;

        public void Dismiss()
        {
            _dismissed = true;
            Debug.Log("[PupilBci] Setup overlay dismissed — app usable without Gazepoint.");
        }

        void OnEnable()
        {
            if (hub == null)
                hub = GetComponent<PupilBciHub>() ?? FindObjectOfType<PupilBciHub>();
            _autoLaunchTried = false;
            _nextRefocus = 0f;
            _enabledAt = Time.unscaledTime;
            _dismissed = false;
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
            if (hub == null || _dismissed) return;

            if (autoLaunchOnce && !_autoLaunchTried
                && hub.Phase == PupilBciPhase.WaitingForGazepoint
                && !hub.GazepointProcessRunning
                && Time.unscaledTime >= autoLaunchAfterSeconds)
            {
                _autoLaunchTried = true;
                TryLaunchAndFocus();
            }

            bool waiting = hub.Phase == PupilBciPhase.WaitingForGazepoint
                           || hub.Phase == PupilBciPhase.WaitingForValidEye;
            bool focusOk = Time.unscaledTime - _enabledAt < Mathf.Max(1f, stopFocusStealAfterSec);
            if (waiting && focusOk && hub.GazepointProcessRunning)
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
            if (hub == null || _dismissed) return;
            if (hideWhenReady && hub.IsReady) return;

            var phase = hub.Phase;
            if (phase == PupilBciPhase.Ready || phase == PupilBciPhase.Idle)
                return;
            if (phase == PupilBciPhase.TrackingLost)
                return;

            float w = Mathf.Min(560f, Screen.width - 40f);
            float h = allowContinueWithoutDevice ? 340f : 300f;
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
                    : "Gazepoint: NON aperto — puoi continuare comunque con tastiera/mouse");

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

            if (allowContinueWithoutDevice)
            {
                GUILayout.Space(8);
                if (GUILayout.Button("Continua senza Gazepoint (tastiera/mouse)", GUILayout.Height(40)))
                    Dismiss();
            }

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
                _launchFeedback = err ?? "Avvio/focus fallito — usa Continua senza Gazepoint.";
                _feedbackUntil = Time.unscaledTime + 8f;
                Debug.LogWarning("[PupilBci] " + _launchFeedback);
            }
        }

        IEnumerator ReconnectAfterLaunch()
        {
            yield return new WaitForSecondsRealtime(Mathf.Max(1f, reconnectAfterLaunchSeconds));
            if (hub != null && !_dismissed)
            {
                hub.FocusGazepointWindow(maximize: maximizeGazepoint);
                hub.RetryConnection();
            }
            _reconnectCo = null;
        }
    }
}
