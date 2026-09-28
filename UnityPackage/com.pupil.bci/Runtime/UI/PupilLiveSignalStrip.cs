using UnityEngine;
using UnityEngine.UI;

namespace Pupil.Bci
{
    /// <summary>
    /// Live vertical PAR strip (same idea as Pupil-com Qt overlay):
    /// fill rises when relaxed (area above threshold), drops when looking near.
    /// Threshold marker sits at mid-bar (area == threshold → 50% fill).
    /// </summary>
    public sealed class PupilLiveSignalStrip : MonoBehaviour
    {
        [SerializeField] PupilBciHub hub;
        [SerializeField] bool buildUiIfMissing = true;
        [SerializeField] float stripWidth = 132f;
        [SerializeField] float stripHeight = 460f;

        Image _fill;
        RectTransform _threshMark;
        Text _title;
        Text _values;
        Text _hint;
        Text _state;
        float _flashUntil;
        int _pressCount;

        public void Bind(PupilBciHub target)
        {
            Unsubscribe();
            hub = target;
            Subscribe();
        }

        void OnEnable()
        {
            if (hub == null)
                hub = GetComponent<PupilBciHub>() ?? FindObjectOfType<PupilBciHub>();
            if (buildUiIfMissing && _fill == null)
                BuildUi();
            Subscribe();
        }

        void OnDisable() => Unsubscribe();

        void Subscribe()
        {
            if (hub == null) return;
            hub.OnSample -= OnSample;
            hub.OnShortPar -= OnShort;
            hub.OnPhaseChanged -= OnPhase;
            hub.OnSample += OnSample;
            hub.OnShortPar += OnShort;
            hub.OnPhaseChanged += OnPhase;
            RefreshPhase(hub.Phase, hub.StatusMessage);
        }

        void Unsubscribe()
        {
            if (hub == null) return;
            hub.OnSample -= OnSample;
            hub.OnShortPar -= OnShort;
            hub.OnPhaseChanged -= OnPhase;
        }

        void OnShort()
        {
            _pressCount++;
            _flashUntil = Time.unscaledTime + 0.4f;
            if (_state != null)
            {
                _state.text = $"PAR → gioco  #{_pressCount}";
                _state.color = new Color(0.49f, 0.99f, 0f);
            }
        }

        void OnPhase(PupilBciPhase phase) => RefreshPhase(phase, hub != null ? hub.StatusMessage : "");

        void RefreshPhase(PupilBciPhase phase, string status)
        {
            if (_state == null) return;
            if (Time.unscaledTime < _flashUntil) return;
            _state.color = phase == PupilBciPhase.Ready
                ? new Color(0.18f, 0.8f, 0.44f)
                : phase == PupilBciPhase.TrackingLost || phase == PupilBciPhase.WaitingForGazepoint
                    ? new Color(0.95f, 0.4f, 0.35f)
                    : new Color(0.95f, 0.75f, 0.2f);
            _state.text = string.IsNullOrEmpty(status) ? phase.ToString() : status;
        }

        void OnSample(PupilSample s)
        {
            if (_fill == null) return;

            float t = s.Threshold;
            float a = s.FilteredArea;
            // Python overlay mapping: ratio = A/S ; bar = clamp(ratio - 0.5)
            float ratio = t > 1e-6f ? a / t : 0f;
            float bar = Mathf.Clamp01(ratio - 0.5f);
            _fill.fillAmount = bar;

            bool flash = Time.unscaledTime < _flashUntil;
            if (flash)
                _fill.color = new Color(0.49f, 0.99f, 0f);
            else if (s.TrackingLost || hub.Phase == PupilBciPhase.WaitingForGazepoint)
                _fill.color = new Color(0.45f, 0.2f, 0.2f);
            else if (s.UnderThreshold)
                _fill.color = new Color(0.91f, 0.3f, 0.24f); // near / constriction
            else
                _fill.color = new Color(0.18f, 0.8f, 0.44f); // far / ok

            if (_values != null)
            {
                _values.text = hub.Phase == PupilBciPhase.WaitingForGazepoint
                    ? "—"
                    : $"A {a:0}\nS {(t > 1e-6f ? t.ToString("0") : "—")}";
            }

            if (_hint != null)
                _hint.text = s.UnderThreshold ? "↓ vicino" : "↑ lontano";

            if (!flash && _state != null && hub != null)
                RefreshPhase(hub.Phase, hub.StatusMessage);
        }

        void BuildUi()
        {
            var canvasGo = new GameObject("PupilLiveSignalCanvas");
            canvasGo.transform.SetParent(transform, false);
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 500;
            var scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            canvasGo.AddComponent<GraphicRaycaster>();

            var panel = Create("Panel", canvasGo.transform);
            var prt = panel.GetComponent<RectTransform>();
            prt.anchorMin = new Vector2(1f, 0.5f);
            prt.anchorMax = new Vector2(1f, 0.5f);
            prt.pivot = new Vector2(1f, 0.5f);
            prt.sizeDelta = new Vector2(stripWidth, stripHeight);
            prt.anchoredPosition = new Vector2(-14f, 0f);
            panel.AddComponent<Image>().color = new Color(0.12f, 0.12f, 0.12f, 0.92f);

            _title = CreateText(panel.transform, "PAR", 18, FontStyle.Bold, new Color(0.49f, 0.99f, 0f),
                new Vector2(0.5f, 1f), new Vector2(0, -14), new Vector2(stripWidth - 16, 28));

            _values = CreateText(panel.transform, "A —\nS —", 14, FontStyle.Normal, new Color(0.85f, 0.85f, 0.85f),
                new Vector2(0.5f, 1f), new Vector2(0, -48), new Vector2(stripWidth - 16, 40));

            // Bar background
            var barBg = Create("BarBg", panel.transform);
            var bgRt = barBg.GetComponent<RectTransform>();
            bgRt.anchorMin = new Vector2(0.5f, 0.12f);
            bgRt.anchorMax = new Vector2(0.5f, 0.72f);
            bgRt.pivot = new Vector2(0.5f, 0.5f);
            bgRt.sizeDelta = new Vector2(36f, 0f);
            barBg.AddComponent<Image>().color = new Color(0.22f, 0.22f, 0.22f, 1f);

            var fillGo = Create("Fill", barBg.transform);
            var fillRt = fillGo.GetComponent<RectTransform>();
            fillRt.anchorMin = Vector2.zero;
            fillRt.anchorMax = Vector2.one;
            fillRt.offsetMin = new Vector2(3, 3);
            fillRt.offsetMax = new Vector2(-3, -3);
            _fill = fillGo.AddComponent<Image>();
            _fill.color = new Color(0.18f, 0.8f, 0.44f);
            _fill.type = Image.Type.Filled;
            _fill.fillMethod = Image.FillMethod.Vertical;
            _fill.fillOrigin = (int)Image.OriginVertical.Bottom;
            _fill.fillAmount = 0.5f;

            // Threshold tick at 50% (area == soglia)
            var mark = Create("Thresh", barBg.transform);
            _threshMark = mark.GetComponent<RectTransform>();
            _threshMark.anchorMin = new Vector2(0f, 0.5f);
            _threshMark.anchorMax = new Vector2(1f, 0.5f);
            _threshMark.pivot = new Vector2(0.5f, 0.5f);
            _threshMark.sizeDelta = new Vector2(8f, 3f);
            _threshMark.anchoredPosition = Vector2.zero;
            mark.AddComponent<Image>().color = new Color(1f, 0.85f, 0.2f, 1f);

            var threshLbl = CreateText(panel.transform, "soglia", 11, FontStyle.Normal, new Color(1f, 0.85f, 0.2f),
                new Vector2(0.5f, 0.5f), new Vector2(42f, 20f), new Vector2(56, 18));
            // place near mid of bar area
            var tl = threshLbl.rectTransform;
            tl.anchorMin = new Vector2(0.5f, 0.42f);
            tl.anchorMax = new Vector2(0.5f, 0.42f);

            _hint = CreateText(panel.transform, "↑ lontano\n↓ vicino", 12, FontStyle.Normal, new Color(0.65f, 0.65f, 0.65f),
                new Vector2(0.5f, 0f), new Vector2(0, 70), new Vector2(stripWidth - 16, 36));

            _state = CreateText(panel.transform, "…", 12, FontStyle.Bold, Color.white,
                new Vector2(0.5f, 0f), new Vector2(0, 28), new Vector2(stripWidth - 16, 48));
        }

        static GameObject Create(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            return go;
        }

        static Text CreateText(Transform parent, string msg, int size, FontStyle style, Color color,
            Vector2 anchor, Vector2 pos, Vector2 sizeDelta)
        {
            var go = Create("Text", parent);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = anchor;
            rt.anchorMax = anchor;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.sizeDelta = sizeDelta;
            rt.anchoredPosition = pos;
            var t = go.AddComponent<Text>();
            t.font = BuiltinUiFont();
            t.fontSize = size;
            t.fontStyle = style;
            t.alignment = TextAnchor.MiddleCenter;
            t.color = color;
            t.text = msg;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            return t;
        }

        static Font BuiltinUiFont()
        {
            // Unity 6+: Arial.ttf removed — use LegacyRuntime.ttf
            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (font == null)
                font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            return font;
        }
    }
}
