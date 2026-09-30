using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using Pupil.Bci;

namespace Pupil.ComApp
{
    /// <summary>
    /// Scene: Pupil_YesNo
    /// Start answer scan with keyboard (Space/Enter); select with PAR / mouse / arrows.
    /// No pause overlay after an answer; only the chosen option is highlighted.
    /// </summary>
    public sealed class YesNoController : MonoBehaviour
    {
        PupilSession _session;
        PupilScanList _scan;
        Text _ans;
        Button _yes, _no;
        readonly List<Button> _answers = new List<Button>();

        enum State { Init, Scanning, ShowingAnswer }
        State _state;
        int _qa;
        float _cooldownUntil;

        void Start()
        {
            PupilUiBootstrap.EnsureInputAndCamera();
            _session = PupilSession.EnsureExists();
            var canvas = PupilUiKit.CreateOverlayCanvas("PupilYesNoCanvas", 30000);
            var panel = PupilUiKit.Panel(canvas.transform, "Panel",
                new Vector2(0.05f, 0.08f), new Vector2(0.95f, 0.88f),
                new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero, PupilUiKit.Bg);
            panel.offsetMax = new Vector2(-20f, 0f);

            var title = PupilUiKit.Label(panel, "Sì o No?", 36, FontStyle.Bold, PupilUiKit.Accent);
            title.rectTransform.anchorMin = new Vector2(0f, 1f);
            title.rectTransform.anchorMax = new Vector2(1f, 1f);
            title.rectTransform.pivot = new Vector2(0.5f, 1f);
            title.rectTransform.sizeDelta = new Vector2(0f, 50f);
            title.rectTransform.anchoredPosition = new Vector2(0f, -10f);

            _ans = PupilUiKit.Label(panel, "", 24, FontStyle.Bold, Color.white);
            _ans.rectTransform.anchorMin = new Vector2(0.05f, 0.72f);
            _ans.rectTransform.anchorMax = new Vector2(0.95f, 0.88f);
            _ans.rectTransform.offsetMin = Vector2.zero;
            _ans.rectTransform.offsetMax = Vector2.zero;

            var row = new GameObject("YN", typeof(RectTransform));
            row.transform.SetParent(panel, false);
            var rrt = row.GetComponent<RectTransform>();
            rrt.anchorMin = new Vector2(0.08f, 0.28f);
            rrt.anchorMax = new Vector2(0.92f, 0.68f);
            var h = row.AddComponent<HorizontalLayoutGroup>();
            h.spacing = 40f;
            h.childForceExpandWidth = true;
            h.childForceExpandHeight = true;

            _yes = PupilUiKit.MenuButton(row.transform, "SI", 160f);
            _no = PupilUiKit.MenuButton(row.transform, "NO", 160f);
            _answers.Add(_yes);
            _answers.Add(_no);

            var back = PupilUiKit.MenuButton(panel, "Indietro", 70f);
            var brt = back.GetComponent<RectTransform>();
            brt.anchorMin = new Vector2(0.25f, 0.06f);
            brt.anchorMax = new Vector2(0.75f, 0.06f);
            brt.pivot = new Vector2(0.5f, 0f);
            brt.sizeDelta = new Vector2(0f, 70f);
            brt.anchoredPosition = new Vector2(0f, 20f);
            back.onClick.AddListener(PupilSceneRouter.GoMainMenu);

            _scan = new PupilScanList(_session.Voice) { ScanInterval = _session.YnScanSec };
            _scan.SetItems(_answers, new[] { "Sì", "No" });

            _session.Hub.OnShortPar += OnShort;
            // Long PAR intentionally ignored here — no pause menu after answers

            _state = State.Init;
            ResetButtonsLook();
            _ans.text = "Premi SPAZIO / INVIO per avviare la domanda.\nPoi costrizione (o frecce+Invio) per rispondere.";
            _session.Voice?.Speak("Sì o No. Premi spazio per iniziare");
        }

        void OnDestroy()
        {
            if (_session?.Hub == null) return;
            _session.Hub.OnShortPar -= OnShort;
        }

        void Update()
        {
            if (PupilUiBootstrap.BackPressed())
            {
                PupilSceneRouter.GoMainMenu();
                return;
            }
            if (Time.unscaledTime < _cooldownUntil) return;

            if (_state == State.Init)
            {
                // Start only from keyboard (caregiver), not from PAR
                if (PupilUiBootstrap.ConfirmPressed())
                    StartQuestion();
                return;
            }

            if (_state == State.Scanning)
            {
                _scan.ScanInterval = _session.YnScanSec;
                _scan.Tick();
                var d = PupilUiBootstrap.NavDelta(horizontal: true);
                if (d != 0) _scan.Move(d);
                if (PupilUiBootstrap.ConfirmPressed())
                    ConfirmAnswer();
            }
            else if (_state == State.ShowingAnswer)
            {
                if (Time.unscaledTime >= _cooldownUntil)
                {
                    _state = State.Init;
                    ResetButtonsLook();
                    _ans.text = "Premi SPAZIO / INVIO per la prossima domanda.";
                }
            }
        }

        void OnShort()
        {
            if (Time.unscaledTime < _cooldownUntil) return;
            // PAR only selects during scanning — does not start the question
            if (_state == State.Scanning)
                ConfirmAnswer();
        }

        void StartQuestion()
        {
            _qa++;
            _state = State.Scanning;
            ResetButtonsLook();
            _ans.text = $"Domanda {_qa} — vicino quando è illuminata la risposta";
            _scan.Start();
            _session.Voice?.Speak("Sì");
        }

        void ConfirmAnswer()
        {
            if (_state != State.Scanning) return;
            var label = _scan.CurrentLabel;
            _scan.Stop(clearHighlight: false);
            _scan.MarkSelectedOnly();
            _ans.text = "Hai risposto: " + label;
            _session.Voice?.Speak(label);
            _state = State.ShowingAnswer;
            _cooldownUntil = Time.unscaledTime + 2f;
        }

        void ResetButtonsLook()
        {
            _yes.GetComponentInChildren<Text>().text = "SI";
            _no.GetComponentInChildren<Text>().text = "NO";
            PupilUiKit.SetButtonVisual(_yes, false);
            PupilUiKit.SetButtonVisual(_no, false);
        }
    }
}
