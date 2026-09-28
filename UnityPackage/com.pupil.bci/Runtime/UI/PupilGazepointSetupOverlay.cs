using System.Collections;
using UnityEngine;

namespace Pupil.Bci
{
    /// <summary>
    /// Setup coach until Hub reaches Ready. Can launch Gazepoint when not running.
    /// </summary>
    public sealed class PupilGazepointSetupOverlay : MonoBehaviour
    {
        [SerializeField] PupilBciHub hub;
        [SerializeField] bool hideWhenReady = true;
        [Tooltip("If Gazepoint is not detected, launch it automatically once.")]
        [SerializeField] bool autoLaunchOnce = true;
        [SerializeField] float autoLaunchAfterSeconds = 1.5f;
        [SerializeField] float reconnectAfterLaunchSeconds = 2.5f;

        string _launchFeedback = "";
        float _feedbackUntil;
        bool _autoLaunchTried;
        Coroutine _reconnectCo;

        void OnEnable()
        {
            if (hub == null)
                hub = GetComponent<PupilBciHub>() ?? FindObjectOfType<PupilBciHub>();
            _autoLaunchTried = false;
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
            if (!autoLaunchOnce || _autoLaunchTried || hub == null) return;
            if (hub.Phase != PupilBciPhase.WaitingForGazepoint) return;
            if (hub.GazepointProcessRunning) return;
            if (Time.unscaledTime < autoLaunchAfterSeconds) return;
            _autoLaunchTried = true;
            TryLaunch();
        }

        void OnGUI()
        {
            if (hub == null) return;
            if (hideWhenReady && hub.IsReady) return;

            var phase = hub.Phase;
            if (phase == PupilBciPhase.Ready || phase == PupilBciPhase.Idle)
                return;

            float w = Mathf.Min(560f, Screen.width - 40f);
            float h = 320f;
            var r = new Rect((Screen.width - w) * 0.5f, (Screen.height - h) * 0.5f, w, h);
            GUI.Box(r, "Setup Gazepoint / Pupil BCI");

            var inner = new Rect(r.x + 16f, r.y + 36f, r.width - 32f, r.height - 48f);
            GUILayout.BeginArea(inner);

            GUILayout.Label($"Stato: {hub.StatusMessage}", GUI.skin.box);
            GUILayout.Space(8);
            GUILayout.Label(hub.SetupHint ?? "");
            GUILayout.Space(8);

            GUILayout.Label(
                hub.GazepointProcessRunning
                    ? "Processo Gazepoint: rilevato"
                    : "Processo Gazepoint: NON rilevato — avvio automatico / pulsante sotto");

            var resolved = GazepointClient.ResolveGazepointExePath(
                hub.Config != null ? hub.Config.gazepointExePath : null);
            GUILayout.Label(
                string.IsNullOrEmpty(resolved)
                    ? "Exe: non trovato"
                    : "Exe: " + resolved,
                GUI.skin.box);

            if (Time.unscaledTime < _feedbackUntil && !string.IsNullOrEmpty(_launchFeedback))
            {
                GUILayout.Space(6);
                GUILayout.Label(_launchFeedback, GUI.skin.box);
            }

            GUILayout.FlexibleSpace();
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Riprova connessione", GUILayout.Height(36)))
                hub.RetryConnection();

            if (GUILayout.Button("Apri Gazepoint", GUILayout.Height(36)))
                TryLaunch();
            GUILayout.EndHorizontal();

            GUILayout.EndArea();
        }

        void TryLaunch()
        {
            if (hub == null) return;
            if (hub.TryOpenGazepoint(out var err))
            {
                _launchFeedback =
                    "Gazepoint in avvio… attendo la porta 4242 (~" +
                    reconnectAfterLaunchSeconds.ToString("0.0") + "s).";
                _feedbackUntil = Time.unscaledTime + 6f;
                if (_reconnectCo != null)
                    StopCoroutine(_reconnectCo);
                _reconnectCo = StartCoroutine(ReconnectAfterLaunch());
            }
            else
            {
                _launchFeedback = err ?? "Avvio fallito.";
                _feedbackUntil = Time.unscaledTime + 8f;
                Debug.LogWarning("[PupilBci] " + _launchFeedback);
            }
        }

        IEnumerator ReconnectAfterLaunch()
        {
            yield return new WaitForSecondsRealtime(Mathf.Max(1f, reconnectAfterLaunchSeconds));
            if (hub != null)
                hub.RetryConnection();
            _reconnectCo = null;
        }
    }
}
