using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.UI;
using Pupil.Bci;

namespace Pupil.ComApp
{
    /// <summary>Scene: Pupil_Keyboard — clean row/column layout, margin for PAR strip.</summary>
    public sealed class KeyboardController : MonoBehaviour
    {
        static readonly string[][] Keys =
        {
            new[] { "R", "S", "E", "T", "L", "P" },
            new[] { "A", "N", "C", "B", "M", "G" },
            new[] { "I", "V", "D", "F", "U", "H" },
            new[] { "O", "QU", "Z", "Y", "J", "!" },
            new[] { "K", "W", "X", "?", ".", "," }
        };

        static readonly string[] Words =
        {
            "CIAO", "COME", "NON", "SI", "NO", "GRAZIE", "AIUTO", "ACQUA", "CIBO", "DOLORE",
            "MAMMA", "PAPA", "CASA", "VOGLIO", "BENE", "MALE", "OGGI", "ADESSO", "STOP", "OK"
        };

        PupilSession _session;
        Text _buffer, _hint;
        readonly Button[] _sugg = new Button[3];
        readonly List<List<Button>> _matrix = new List<List<Button>>();
        Button _space, _canc, _back;
        GameObject _pauseOverlay;
        Button _pauseResume, _pauseExit;
        GridLayoutGroup _grid;
        RectTransform _gridBand;
        readonly StringBuilder _text = new StringBuilder();

        enum State { Init, Row, Col, Suggest, Pause }
        State _state;
        float _scanStart;
        int _row, _col, _suggIdx, _pauseOpt;

        void Start()
        {
            PupilUiBootstrap.EnsureInputAndCamera();
            _session = PupilSession.EnsureExists();

            var canvas = PupilUiKit.CreateOverlayCanvas("PupilKeyboardCanvas", 30000);
            // Leave right strip for PAR bar
            var root = PupilUiKit.Panel(canvas.transform, "Root",
                Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f),
                Vector2.zero, Vector2.zero, new Color(0.07f, 0.07f, 0.09f, 1f));
            root.offsetMax = new Vector2(-150f, 0f);

            var col = new GameObject("Layout", typeof(RectTransform));
            col.transform.SetParent(root, false);
            var crt = col.GetComponent<RectTransform>();
            Stretch(crt, 0.03f, 0.03f, 0.97f, 0.97f);
            var v = col.AddComponent<VerticalLayoutGroup>();
            v.spacing = 10f;
            v.padding = new RectOffset(12, 12, 12, 12);
            v.childAlignment = TextAnchor.UpperCenter;
            v.childControlWidth = true;
            v.childControlHeight = true;
            v.childForceExpandWidth = true;
            v.childForceExpandHeight = false;

            _buffer = AddBandLabel(col.transform, "…", 32, 56f, FontStyle.Bold, Color.white);
            _hint = AddBandLabel(col.transform, "Inizializzazione…", 18, 36f, FontStyle.Normal, PupilUiKit.Accent);

            // Suggestions
            var sugg = Band(col.transform, "Sugg", 64f);
            var sh = sugg.gameObject.AddComponent<HorizontalLayoutGroup>();
            sh.spacing = 10f;
            sh.childForceExpandWidth = true;
            sh.childForceExpandHeight = true;
            sh.childControlWidth = true;
            sh.childControlHeight = true;
            for (var i = 0; i < 3; i++)
            {
                _sugg[i] = PupilUiKit.MenuButton(sugg, Words[i], 56f);
                var le = _sugg[i].gameObject.AddComponent<LayoutElement>();
                le.flexibleWidth = 1f;
                le.minHeight = 56f;
                var idx = i;
                _sugg[i].onClick.AddListener(() => ApplySuggestion(idx));
            }

            // Key grid — flexible middle
            var gridBand = Band(col.transform, "Grid", 0f);
            var gridLe = gridBand.gameObject.AddComponent<LayoutElement>();
            gridLe.flexibleHeight = 1f;
            gridLe.minHeight = 280f;
            var grid = gridBand.gameObject.AddComponent<GridLayoutGroup>();
            grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
            grid.constraintCount = 6;
            grid.spacing = new Vector2(8f, 8f);
            grid.padding = new RectOffset(4, 4, 4, 4);
            grid.childAlignment = TextAnchor.MiddleCenter;
            // cell size fitted in LateUpdate once rect known
            grid.cellSize = new Vector2(120f, 64f);

            for (var r = 0; r < Keys.Length; r++)
            {
                var row = new List<Button>();
                for (var c = 0; c < Keys[r].Length; c++)
                {
                    var key = Keys[r][c];
                    var b = PupilUiKit.MenuButton(gridBand, key, 64f);
                    var captured = key;
                    b.onClick.AddListener(() => TypeKey(captured));
                    row.Add(b);
                }
                _matrix.Add(row);
            }

            _grid = grid;
            _gridBand = gridBand;

            // Bottom: SPAZIO | CANCELLA | MENU
            var bottom = Band(col.transform, "Bottom", 72f);
            var bh = bottom.gameObject.AddComponent<HorizontalLayoutGroup>();
            bh.spacing = 10f;
            bh.childForceExpandWidth = true;
            bh.childForceExpandHeight = true;
            bh.childControlWidth = true;
            bh.childControlHeight = true;
            _space = PupilUiKit.MenuButton(bottom, "SPAZIO", 64f);
            _canc = PupilUiKit.MenuButton(bottom, "CANCELLA", 64f);
            _back = PupilUiKit.MenuButton(bottom, "MENÙ", 64f);
            _space.gameObject.AddComponent<LayoutElement>().flexibleWidth = 2f;
            _canc.gameObject.AddComponent<LayoutElement>().flexibleWidth = 1f;
            _back.gameObject.AddComponent<LayoutElement>().flexibleWidth = 1f;
            _space.onClick.AddListener(() => TypeKey(" "));
            _canc.onClick.AddListener(() => TypeKey("CANC"));
            _back.onClick.AddListener(PupilSceneRouter.GoMainMenu);

            // Pause overlay
            _pauseOverlay = new GameObject("Pause", typeof(RectTransform));
            _pauseOverlay.transform.SetParent(root, false);
            Stretch(_pauseOverlay.GetComponent<RectTransform>(), 0f, 0f, 1f, 1f);
            _pauseOverlay.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.82f);
            var pauseCol = Band(_pauseOverlay.transform, "PauseCol", 0f);
            Stretch(pauseCol, 0.2f, 0.3f, 0.8f, 0.7f);
            var pv = pauseCol.gameObject.AddComponent<VerticalLayoutGroup>();
            pv.spacing = 20f;
            pv.childForceExpandWidth = true;
            pv.childControlHeight = true;
            AddBandLabel(pauseCol, "PAUSA", 40, 60f, FontStyle.Bold, Color.yellow);
            var prow = Band(pauseCol, "PR", 90f);
            var ph = prow.gameObject.AddComponent<HorizontalLayoutGroup>();
            ph.spacing = 16f;
            ph.childForceExpandWidth = true;
            ph.childForceExpandHeight = true;
            _pauseResume = PupilUiKit.MenuButton(prow, "RIPRENDI", 80f);
            _pauseExit = PupilUiKit.MenuButton(prow, "MENU", 80f);
            _pauseOverlay.SetActive(false);

            _session.Hub.OnShortPar += OnShort;
            _session.Hub.OnLongPar += OnLong;

            _state = State.Init;
            _scanStart = Time.unscaledTime;
            _session.Voice?.Speak("Tastiera");

            Canvas.ForceUpdateCanvases();
            FitGrid(_grid, _gridBand);
        }

        void LateUpdate()
        {
            if (_grid != null && _gridBand != null)
                FitGrid(_grid, _gridBand);
        }

        static void FitGrid(GridLayoutGroup grid, RectTransform band)
        {
            var r = band.rect;
            if (r.width < 10f || r.height < 10f) return;
            float cw = (r.width - grid.padding.horizontal - grid.spacing.x * 5f) / 6f;
            float ch = (r.height - grid.padding.vertical - grid.spacing.y * 4f) / 5f;
            grid.cellSize = new Vector2(Mathf.Max(48f, cw), Mathf.Max(40f, ch));
        }

        static RectTransform Band(Transform parent, string name, float height)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var le = go.AddComponent<LayoutElement>();
            if (height > 0f)
            {
                le.preferredHeight = height;
                le.minHeight = height;
            }
            return go.GetComponent<RectTransform>();
        }

        static Text AddBandLabel(Transform parent, string msg, int size, float height, FontStyle style, Color color)
        {
            var band = Band(parent, "Lbl", height);
            var t = PupilUiKit.Label(band, msg, size, style, color);
            Stretch(t.rectTransform, 0f, 0f, 1f, 1f);
            t.rectTransform.sizeDelta = Vector2.zero;
            return t;
        }

        static void Stretch(RectTransform rt, float x0, float y0, float x1, float y1)
        {
            rt.anchorMin = new Vector2(x0, y0);
            rt.anchorMax = new Vector2(x1, y1);
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            rt.pivot = new Vector2(0.5f, 0.5f);
        }

        void OnDestroy()
        {
            if (_session?.Hub == null) return;
            _session.Hub.OnShortPar -= OnShort;
            _session.Hub.OnLongPar -= OnLong;
        }

        void Update()
        {
            if (PupilUiBootstrap.BackPressed())
            {
                PupilSceneRouter.GoMainMenu();
                return;
            }

            var interval = Mathf.Max(0.8f, _session.KeyboardScanSec);
            if (_state == State.Init)
            {
                if (Time.unscaledTime - _scanStart >= 2f || PupilUiBootstrap.ConfirmPressed())
                {
                    _state = State.Row;
                    _row = 0;
                    _scanStart = Time.unscaledTime;
                    HighlightRow();
                    SpeakRow();
                    _hint.text = "Mouse · frecce+Invio · costrizione · Esc=menu";
                }
                return;
            }

            if (_state == State.Row)
            {
                var d = PupilUiBootstrap.NavDelta(false);
                if (d != 0)
                {
                    _row = Mod(_row + d, _matrix.Count + 1);
                    _scanStart = Time.unscaledTime;
                    HighlightRow();
                    SpeakRow();
                }
                if (PupilUiBootstrap.ConfirmPressed()) { OnShort(); return; }
            }
            else if (_state == State.Col)
            {
                var d = PupilUiBootstrap.NavDelta(true);
                if (d != 0)
                {
                    _col = Mod(_col + d, _row < _matrix.Count ? _matrix[_row].Count : 2);
                    _scanStart = Time.unscaledTime;
                    HighlightCol();
                    SpeakCol();
                }
                if (PupilUiBootstrap.ConfirmPressed()) { OnShort(); return; }
            }
            else if (_state == State.Suggest)
            {
                var d = PupilUiBootstrap.NavDelta(true);
                if (d != 0)
                {
                    _suggIdx = Mod(_suggIdx + d, 3);
                    _scanStart = Time.unscaledTime;
                    HighlightSuggest();
                    _session.Voice?.Speak(_sugg[_suggIdx].GetComponentInChildren<Text>().text);
                }
                if (PupilUiBootstrap.ConfirmPressed()) { OnShort(); return; }
            }
            else if (_state == State.Pause)
            {
                var d = PupilUiBootstrap.NavDelta(true);
                if (d != 0)
                {
                    _pauseOpt = 1 - _pauseOpt;
                    PupilUiKit.SetButtonVisual(_pauseResume, _pauseOpt == 0);
                    PupilUiKit.SetButtonVisual(_pauseExit, _pauseOpt == 1);
                    _session.Voice?.Speak(_pauseOpt == 0 ? "Riprendi" : "Menu");
                    _scanStart = Time.unscaledTime;
                }
                if (PupilUiBootstrap.ConfirmPressed()) { OnShort(); return; }
            }

            if (Time.unscaledTime - _scanStart < interval) return;
            _scanStart = Time.unscaledTime;

            if (_state == State.Row)
            {
                _row = (_row + 1) % (_matrix.Count + 1);
                HighlightRow();
                SpeakRow();
            }
            else if (_state == State.Col)
            {
                _col = (_col + 1) % (_row < _matrix.Count ? _matrix[_row].Count : 2);
                HighlightCol();
                SpeakCol();
            }
            else if (_state == State.Suggest)
            {
                _suggIdx = (_suggIdx + 1) % 3;
                HighlightSuggest();
                _session.Voice?.Speak(_sugg[_suggIdx].GetComponentInChildren<Text>().text);
            }
            else if (_state == State.Pause)
            {
                _pauseOpt = 1 - _pauseOpt;
                PupilUiKit.SetButtonVisual(_pauseResume, _pauseOpt == 0);
                PupilUiKit.SetButtonVisual(_pauseExit, _pauseOpt == 1);
                _session.Voice?.Speak(_pauseOpt == 0 ? "Riprendi" : "Menu");
            }
        }

        static int Mod(int v, int m)
        {
            var r = v % m;
            return r < 0 ? r + m : r;
        }

        void OnShort()
        {
            if (_state == State.Init) return;
            if (_state == State.Pause)
            {
                if (_pauseOpt == 0)
                {
                    _pauseOverlay.SetActive(false);
                    _state = State.Row;
                    _row = 0;
                    _scanStart = Time.unscaledTime;
                    HighlightRow();
                    SpeakRow();
                }
                else PupilSceneRouter.GoMainMenu();
                return;
            }
            if (_state == State.Row)
            {
                _state = State.Col;
                _col = 0;
                _scanStart = Time.unscaledTime;
                HighlightCol();
                SpeakCol();
                return;
            }
            if (_state == State.Col)
            {
                if (_row < _matrix.Count) TypeKey(Keys[_row][_col]);
                else if (_col == 0) TypeKey(" ");
                else TypeKey("CANC");
                _state = State.Row;
                _row = 0;
                _scanStart = Time.unscaledTime;
                HighlightRow();
                SpeakRow();
                return;
            }
            if (_state == State.Suggest)
            {
                ApplySuggestion(_suggIdx);
                _state = State.Row;
                _row = 0;
                _scanStart = Time.unscaledTime;
                HighlightRow();
            }
        }

        void OnLong()
        {
            if (_state == State.Init) return;
            if (_state == State.Col)
            {
                _state = State.Suggest;
                _suggIdx = 0;
                _scanStart = Time.unscaledTime;
                HighlightSuggest();
                _hint.text = "Suggerimenti";
                _session.Voice?.Speak("Suggerimenti");
                return;
            }
            _pauseOverlay.SetActive(true);
            _state = State.Pause;
            _pauseOpt = 0;
            PupilUiKit.SetButtonVisual(_pauseResume, true);
            PupilUiKit.SetButtonVisual(_pauseExit, false);
            _session.Voice?.Speak("Pausa");
        }

        void TypeKey(string key)
        {
            if (key == "CANC")
            {
                if (_text.Length > 0) _text.Length--;
            }
            else
            {
                _text.Append(key);
                _session.Voice?.Speak(key == " " ? "spazio" : key);
            }
            _buffer.text = _text.Length == 0 ? "…" : _text.ToString();
            UpdateSuggestions();
        }

        void ApplySuggestion(int idx)
        {
            var word = _sugg[idx].GetComponentInChildren<Text>().text;
            var s = _text.ToString();
            var sp = s.LastIndexOf(' ');
            _text.Length = sp < 0 ? 0 : sp + 1;
            _text.Append(word).Append(' ');
            _buffer.text = _text.ToString();
            UpdateSuggestions();
            _session.Voice?.Speak(word);
        }

        void UpdateSuggestions()
        {
            var s = _text.ToString().Trim();
            var last = s;
            var sp = s.LastIndexOf(' ');
            if (sp >= 0) last = s.Substring(sp + 1);
            last = last.ToUpperInvariant();
            var found = new List<string>();
            if (!string.IsNullOrEmpty(last))
            {
                foreach (var w in Words)
                {
                    if (w.StartsWith(last) && !found.Contains(w)) found.Add(w);
                    if (found.Count >= 3) break;
                }
            }
            for (var i = 0; i < 3; i++)
            {
                _sugg[i].GetComponentInChildren<Text>().text = i < found.Count ? found[i] : Words[i];
                PupilUiKit.SetButtonVisual(_sugg[i], false);
            }
        }

        void Clear()
        {
            foreach (var row in _matrix)
                foreach (var b in row) PupilUiKit.SetButtonVisual(b, false);
            PupilUiKit.SetButtonVisual(_space, false);
            PupilUiKit.SetButtonVisual(_canc, false);
            PupilUiKit.SetButtonVisual(_back, false);
            foreach (var s in _sugg) PupilUiKit.SetButtonVisual(s, false);
        }

        void HighlightRow()
        {
            Clear();
            if (_row < _matrix.Count)
                foreach (var b in _matrix[_row]) PupilUiKit.SetButtonVisual(b, true);
            else
            {
                PupilUiKit.SetButtonVisual(_space, true);
                PupilUiKit.SetButtonVisual(_canc, true);
            }
        }

        void HighlightCol()
        {
            Clear();
            if (_row < _matrix.Count)
                PupilUiKit.SetButtonVisual(_matrix[_row][_col], true);
            else
            {
                PupilUiKit.SetButtonVisual(_space, _col == 0);
                PupilUiKit.SetButtonVisual(_canc, _col == 1);
            }
        }

        void HighlightSuggest()
        {
            Clear();
            for (var i = 0; i < 3; i++)
                PupilUiKit.SetButtonVisual(_sugg[i], i == _suggIdx);
        }

        void SpeakRow() =>
            _session.Voice?.Speak(_row < _matrix.Count ? "riga " + (_row + 1) : "spazio e cancella");

        void SpeakCol()
        {
            if (_row < _matrix.Count) _session.Voice?.Speak(Keys[_row][_col]);
            else _session.Voice?.Speak(_col == 0 ? "spazio" : "cancella");
        }
    }
}
