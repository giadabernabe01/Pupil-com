using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Pupil.Bci;

namespace Pupil.ComApp
{
    /// <summary>Scene: Pupil_MainMenu — start here. UI is built at Play.</summary>
    public sealed class MainMenuController : MonoBehaviour
    {
        [Tooltip("Exact scene name of Space Evaders in this project.")]
        [SerializeField] string spaceEvadersScene = "Prototype_GalaxyCampaign";

        PupilSession _session;
        PupilScanList _scan;
        Text _hint;
        readonly List<Button> _buttons = new List<Button>();
        enum Phase { Wait, Init, Scanning }
        Phase _phase = Phase.Wait;
        float _phaseStart;
        float _cooldownUntil;

        void Start()
        {
            PupilUiBootstrap.EnsureInputAndCamera();

            _session = PupilSession.EnsureExists(spaceEvadersScene);
            _session.SetSpaceEvadersScene(spaceEvadersScene);

            var canvas = PupilUiKit.CreateOverlayCanvas("PupilMainMenuCanvas", 30000);
            var root = PupilUiKit.Panel(canvas.transform, "Root",
                Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f),
                Vector2.zero, Vector2.zero, new Color(0.08f, 0.08f, 0.1f, 1f));
            root.offsetMax = new Vector2(-150f, 0f);

            var title = PupilUiKit.Label(root, "PUPIL-COM", 42, FontStyle.Bold, PupilUiKit.Accent);
            title.rectTransform.anchorMin = new Vector2(0f, 1f);
            title.rectTransform.anchorMax = new Vector2(1f, 1f);
            title.rectTransform.pivot = new Vector2(0.5f, 1f);
            title.rectTransform.sizeDelta = new Vector2(0f, 60f);
            title.rectTransform.anchoredPosition = new Vector2(0f, -8f);

            _hint = PupilUiKit.Label(root,
                "Mouse / frecce+Invio / costrizione — Attendi Ready…",
                20, FontStyle.Normal, Color.white);
            _hint.rectTransform.anchorMin = new Vector2(0f, 1f);
            _hint.rectTransform.anchorMax = new Vector2(1f, 1f);
            _hint.rectTransform.pivot = new Vector2(0.5f, 1f);
            _hint.rectTransform.sizeDelta = new Vector2(-20f, 48f);
            _hint.rectTransform.anchoredPosition = new Vector2(0f, -70f);

            var colHost = new GameObject("Buttons", typeof(RectTransform));
            colHost.transform.SetParent(root, false);
            var crt = colHost.GetComponent<RectTransform>();
            crt.anchorMin = new Vector2(0.1f, 0.08f);
            crt.anchorMax = new Vector2(0.9f, 0.72f);
            crt.offsetMin = Vector2.zero;
            crt.offsetMax = Vector2.zero;
            var col = colHost.AddComponent<VerticalLayoutGroup>();
            col.spacing = 18f;
            col.childControlHeight = false;
            col.childControlWidth = true;
            col.childForceExpandWidth = true;

            Add(colHost.transform, "Training", PupilSceneRouter.GoTraining);
            Add(colHost.transform, "Sì o No", PupilSceneRouter.GoYesNo);
            Add(colHost.transform, "Tastiera", PupilSceneRouter.GoKeyboard);
            Add(colHost.transform, "Space Evaders", PupilSceneRouter.GoSpaceEvaders);

            _scan = new PupilScanList(_session.Voice) { ScanInterval = _session.MenuScanSec };
            _scan.SetItems(_buttons, new[] { "Training", "Sì o No", "Tastiera", "Space Evaders" });

            if (_session.Hub != null)
            {
                _session.Hub.OnShortPar += OnShort;
                _session.Hub.OnReady += OnReady;
                if (_session.Hub.IsReady) BeginInit();
            }
        }

        void OnDestroy()
        {
            if (_session?.Hub == null) return;
            _session.Hub.OnShortPar -= OnShort;
            _session.Hub.OnReady -= OnReady;
        }

        void Add(Transform parent, string label, UnityEngine.Events.UnityAction action)
        {
            var b = PupilUiKit.MenuButton(parent, label, 90f);
            b.onClick.AddListener(action);
            _buttons.Add(b);
        }

        void OnReady() => BeginInit();

        void BeginInit()
        {
            if (_phase != Phase.Wait && _phase != Phase.Init) return;
            _phase = Phase.Init;
            _phaseStart = Time.unscaledTime;
            _hint.text = "Inizializzazione… (mouse già attivo) — guarda lontano";
            _session.Voice?.Speak("Menu principale");
        }

        void Update()
        {
            if (Time.unscaledTime < _cooldownUntil) return;

            if (_phase == Phase.Wait && _session?.Hub != null && _session.Hub.IsReady)
                BeginInit();

            if (_phase == Phase.Init && Time.unscaledTime - _phaseStart >= 2.5f)
            {
                _phase = Phase.Scanning;
                _hint.text = "Menu: mouse / ↑↓+Invio / costrizione";
                _scan.ScanInterval = _session.MenuScanSec;
                _scan.Start();
            }
            else if (_phase == Phase.Scanning)
            {
                _scan.Tick();
                var d = PupilUiBootstrap.NavDelta(horizontal: false);
                if (d != 0) _scan.Move(d);
                if (PupilUiBootstrap.ConfirmPressed())
                    ActivateCurrent();
            }
            else if (_phase == Phase.Wait || _phase == Phase.Init)
            {
                // Keyboard usable even before auto-scan starts
                var d = PupilUiBootstrap.NavDelta(horizontal: false);
                if (d != 0)
                {
                    if (!_scan.Running) { _scan.Start(); _phase = Phase.Scanning; }
                    _scan.Move(d);
                }
                if (PupilUiBootstrap.ConfirmPressed())
                {
                    if (!_scan.Running) { _scan.Start(); _phase = Phase.Scanning; }
                    ActivateCurrent();
                }
            }
        }

        void OnShort() => ActivateCurrent();

        void ActivateCurrent()
        {
            if (_phase != Phase.Scanning && _phase != Phase.Init && _phase != Phase.Wait) return;
            if (Time.unscaledTime < _cooldownUntil) return;
            if (_scan.Count == 0) return;

            var btn = _scan.Current;
            var label = _scan.CurrentLabel;
            _scan.Stop(false);
            _scan.MarkDetected();
            _session.Voice?.Speak(label);
            _cooldownUntil = Time.unscaledTime + _session.MenuCooldownSec;
            // Invoke only navigation actions: temporarily avoid double Focus from scan listener
            btn?.onClick.Invoke();
        }
    }
}
