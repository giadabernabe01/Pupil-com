using UnityEngine;
using UnityEngine.UI;

namespace Pupil.Bci.Samples
{
    /// <summary>
    /// Runtime demo: creates Hub + canvas bar + press counter. Add to an empty scene and Press Play
    /// with Gazepoint Control running.
    /// </summary>
    public sealed class BasicParDemoBootstrap : MonoBehaviour
    {
        [SerializeField] bool createHud = true;
        [SerializeField] bool logEvents = true;

        PupilBciHub _hub;
        Text _status;
        Text _counter;
        int _presses;

        void Start()
        {
            var config = ScriptableObject.CreateInstance<PupilBciConfig>();
            config.name = "DemoConfig";

            // Disable until config is applied so Awake/OnEnable don't start with defaults only.
            var hubGo = new GameObject("PupilBciHub");
            hubGo.SetActive(false);
            _hub = hubGo.AddComponent<PupilBciHub>();
            _hub.ApplyConfig(config, logEvents);
            hubGo.SetActive(true);

            if (createHud)
                BuildHud();

            _hub.OnShortPar += () =>
            {
                _presses++;
                if (_counter != null)
                    _counter.text = $"PAR presses: {_presses}";
                Debug.Log($"[BasicParDemo] Short PAR #{_presses}");
            };

            _hub.OnTrackingLost += () =>
            {
                if (_status != null)
                    _status.text = "TRACKING LOST — check Gazepoint";
            };
            _hub.OnTrackingOk += () =>
            {
                if (_status != null)
                    _status.text = "Tracking OK";
            };
            _hub.OnSample += s =>
            {
                if (_status == null || s.TrackingLost)
                    return;
                _status.text = _hub.IsBaselineReady
                    ? $"Area {s.FilteredArea:0}  Thresh {s.Threshold:0}"
                    : "Collecting baseline…";
            };
        }

        void BuildHud()
        {
            var canvasGo = new GameObject("PupilBciDemoCanvas");
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasGo.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasGo.AddComponent<GraphicRaycaster>();

            var panel = CreateUiObject("Panel", canvasGo.transform);
            var rt = panel.GetComponent<RectTransform>();
            rt.anchorMin = new Vector2(1f, 0.5f);
            rt.anchorMax = new Vector2(1f, 0.5f);
            rt.pivot = new Vector2(1f, 0.5f);
            rt.sizeDelta = new Vector2(140f, 420f);
            rt.anchoredPosition = new Vector2(-16f, 0f);
            panel.AddComponent<Image>().color = new Color(0.12f, 0.12f, 0.12f, 0.92f);

            _status = CreateText(panel.transform, "Status", "Connecting…", 14, new Vector2(0.5f, 1f), new Vector2(0, -24));
            _counter = CreateText(panel.transform, "Counter", "PAR presses: 0", 16, new Vector2(0.5f, 1f), new Vector2(0, -56));

            var fillGo = CreateUiObject("Fill", panel.transform);
            var fillRt = fillGo.GetComponent<RectTransform>();
            fillRt.anchorMin = new Vector2(0.5f, 0.08f);
            fillRt.anchorMax = new Vector2(0.5f, 0.72f);
            fillRt.pivot = new Vector2(0.5f, 0f);
            fillRt.sizeDelta = new Vector2(28f, 0f);
            fillGo.AddComponent<Image>().color = new Color(0.2f, 0.2f, 0.2f);

            var fillInner = CreateUiObject("FillInner", fillGo.transform);
            var innerRt = fillInner.GetComponent<RectTransform>();
            innerRt.anchorMin = Vector2.zero;
            innerRt.anchorMax = Vector2.one;
            innerRt.offsetMin = Vector2.zero;
            innerRt.offsetMax = Vector2.zero;
            var fill = fillInner.AddComponent<Image>();
            fill.color = new Color(0.18f, 0.8f, 0.44f);
            fill.type = Image.Type.Filled;
            fill.fillMethod = Image.FillMethod.Vertical;
            fill.fillOrigin = (int)Image.OriginVertical.Bottom;
            fill.fillAmount = 0.5f;

            var bar = panel.AddComponent<PupilSignalBar>();
            bar.Bind(_hub, null, fill, _status);
        }

        static GameObject CreateUiObject(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            return go;
        }

        static Text CreateText(Transform parent, string name, string msg, int size, Vector2 anchor, Vector2 pos)
        {
            var go = CreateUiObject(name, parent);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = anchor;
            rt.anchorMax = anchor;
            rt.pivot = new Vector2(0.5f, 1f);
            rt.sizeDelta = new Vector2(130f, 40f);
            rt.anchoredPosition = pos;
            var t = go.AddComponent<Text>();
            t.font = BuiltinUiFont();
            t.fontSize = size;
            t.alignment = TextAnchor.UpperCenter;
            t.color = Color.white;
            t.text = msg;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            return t;
        }

        static Font BuiltinUiFont()
        {
            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (font == null)
                font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            return font;
        }
    }
}
