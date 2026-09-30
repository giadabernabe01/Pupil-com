using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Pupil.Bci;

namespace Pupil.ComApp
{
    /// <summary>Scene: Pupil_Training</summary>
    public sealed class TrainingController : MonoBehaviour
    {
        PupilSession _session;
        PupilScanList _bootScan;
        Text _message;
        readonly List<Button> _bootButtons = new List<Button>();
        readonly int[] _trials = { 1, 2, 1, 2, 1 };

        enum State { Boot, Baseline, Holding, Far, Cooldown, Finished, Idle }
        State _state;
        float _t0;
        int _trial;
        int _correct;
        bool _shortHit, _longHit, _ok;

        void Start()
        {
            PupilUiBootstrap.EnsureInputAndCamera();
            _session = PupilSession.EnsureExists();
            var canvas = PupilUiKit.CreateOverlayCanvas("PupilTrainingCanvas", 30000);
            var panel = PupilUiKit.Panel(canvas.transform, "Panel",
                new Vector2(0.05f, 0.08f), new Vector2(0.95f, 0.88f),
                new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero, PupilUiKit.Bg);
            panel.offsetMax = new Vector2(-20f, 0f);

            var title = PupilUiKit.Label(panel, "TRAINING", 36, FontStyle.Bold, PupilUiKit.Accent);
            title.rectTransform.anchorMin = new Vector2(0f, 1f);
            title.rectTransform.anchorMax = new Vector2(1f, 1f);
            title.rectTransform.pivot = new Vector2(0.5f, 1f);
            title.rectTransform.sizeDelta = new Vector2(0f, 56f);
            title.rectTransform.anchoredPosition = new Vector2(0f, -8f);

            _message = PupilUiKit.Label(panel, "", 28, FontStyle.Bold, Color.white);
            _message.rectTransform.anchorMin = new Vector2(0.05f, 0.35f);
            _message.rectTransform.anchorMax = new Vector2(0.95f, 0.75f);
            _message.rectTransform.offsetMin = Vector2.zero;
            _message.rectTransform.offsetMax = Vector2.zero;

            var row = new GameObject("Boot", typeof(RectTransform));
            row.transform.SetParent(panel, false);
            var rrt = row.GetComponent<RectTransform>();
            rrt.anchorMin = new Vector2(0.1f, 0.08f);
            rrt.anchorMax = new Vector2(0.9f, 0.28f);
            var h = row.AddComponent<HorizontalLayoutGroup>();
            h.spacing = 24f;
            h.childForceExpandWidth = true;
            h.childForceExpandHeight = true;

            var start = PupilUiKit.MenuButton(row.transform, "Inizia", 80f);
            var back = PupilUiKit.MenuButton(row.transform, "Indietro", 80f);
            start.onClick.AddListener(StartSeq);
            back.onClick.AddListener(PupilSceneRouter.GoMainMenu);
            _bootButtons.Add(start);
            _bootButtons.Add(back);

            _bootScan = new PupilScanList(_session.Voice) { ScanInterval = 3f };
            _bootScan.SetItems(_bootButtons, new[] { "Inizia", "Indietro" });

            _session.Hub.OnShortPar += OnShort;
            _session.Hub.OnLongPar += OnLong;

            _state = State.Boot;
            _message.text = "Scegli Inizia o Indietro";
            _bootScan.Start();
            _session.Voice?.Speak("Training");
        }

        void OnDestroy()
        {
            if (_session?.Hub == null) return;
            _session.Hub.OnShortPar -= OnShort;
            _session.Hub.OnLongPar -= OnLong;
        }

        void StartSeq()
        {
            _bootScan.Stop();
            foreach (var b in _bootButtons) b.gameObject.SetActive(false);
            _trial = 0;
            _correct = 0;
            _state = State.Baseline;
            _t0 = Time.unscaledTime;
            _message.text = "Baseline… guarda LONTANO";
            _session.Voice?.Speak("Guarda lontano");
            _session.Hub.ResetFilters();
        }

        void Update()
        {
            if (PupilUiBootstrap.BackPressed())
            {
                PupilSceneRouter.GoMainMenu();
                return;
            }

            var elapsed = Time.unscaledTime - _t0;
            switch (_state)
            {
                case State.Boot:
                case State.Idle:
                    _bootScan.Tick();
                    {
                        var d = PupilUiBootstrap.NavDelta(horizontal: true);
                        if (d != 0) _bootScan.Move(d);
                        if (PupilUiBootstrap.ConfirmPressed())
                            OnShort();
                    }
                    break;
                case State.Baseline:
                    if (elapsed >= _session.TrainingInitSec) NextTrial();
                    break;
                case State.Holding:
                {
                    var need = _trials[_trial] == 1 ? _session.TrainingShortTaskSec : _session.TrainingLongTaskSec;
                    if (_trials[_trial] == 1 && _shortHit) _ok = true;
                    if (_trials[_trial] == 2 && _longHit) _ok = true;
                    _message.text = $"Richiesta {_trial + 1}/5 VICINO ({(_trials[_trial] == 1 ? "breve" : "lunga")}) {Mathf.Max(0, need - elapsed):0.0}s";
                    // Keyboard cheat/manual confirm for training trials
                    if (PupilUiBootstrap.ConfirmPressed())
                    {
                        if (_trials[_trial] == 1) _shortHit = true;
                        else _longHit = true;
                    }
                    if (elapsed >= need)
                    {
                        if (_ok) _correct++;
                        _state = State.Far;
                        _t0 = Time.unscaledTime;
                        _message.text = "Guarda LONTANO";
                        _session.Voice?.Speak("Lontano");
                    }
                    break;
                }
                case State.Far:
                    _state = State.Cooldown;
                    _t0 = Time.unscaledTime;
                    break;
                case State.Cooldown:
                    _message.text = $"Attendi… {Mathf.Max(0, _session.TrainingFarSec - elapsed):0.0}s";
                    if (elapsed >= _session.TrainingFarSec)
                    {
                        _trial++;
                        if (_trial >= _trials.Length)
                        {
                            _state = State.Finished;
                            _t0 = Time.unscaledTime;
                            _message.text = $"Completato: {_correct}/5";
                            _session.Voice?.Speak($"Completato. {_correct} su 5");
                        }
                        else NextTrial();
                    }
                    break;
                case State.Finished:
                    if (elapsed >= 5f)
                    {
                        _state = State.Idle;
                        foreach (var b in _bootButtons) b.gameObject.SetActive(true);
                        _bootScan.Start();
                        _message.text = "Scegli Inizia o Indietro (mouse / frecce / costrizione)";
                    }
                    break;
            }
        }

        void NextTrial()
        {
            _shortHit = _longHit = _ok = false;
            _state = State.Holding;
            _t0 = Time.unscaledTime;
            _session.Voice?.Speak("Vicino");
        }

        void OnShort()
        {
            if (_state == State.Boot || _state == State.Idle)
            {
                if (_bootScan.Index == 0) StartSeq();
                else PupilSceneRouter.GoMainMenu();
                return;
            }
            if (_state == State.Holding) _shortHit = true;
        }

        void OnLong()
        {
            if (_state == State.Holding) _longHit = true;
        }
    }
}
