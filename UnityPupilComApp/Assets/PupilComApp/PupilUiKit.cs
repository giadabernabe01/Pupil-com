using UnityEngine;
using UnityEngine.UI;

namespace Pupil.ComApp
{
    public static class PupilUiKit
    {
        public static readonly Color Bg = new Color(0.12f, 0.12f, 0.14f, 0.96f);
        public static readonly Color Active = new Color(0f, 0.47f, 0.84f, 1f);
        public static readonly Color Inactive = new Color(0.27f, 0.27f, 0.27f, 1f);
        public static readonly Color Detected = new Color(0.55f, 0.2f, 0.15f, 1f);
        public static readonly Color Accent = new Color(0.49f, 0.99f, 0f, 1f);

        public static Font Font()
        {
            var f = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            return f != null ? f : Resources.GetBuiltinResource<Font>("Arial.ttf");
        }

        public static Canvas CreateOverlayCanvas(string name, int sortingOrder)
        {
            var go = new GameObject(name);
            var canvas = go.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.overrideSorting = true;
            canvas.sortingOrder = sortingOrder;
            var scaler = go.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            go.AddComponent<GraphicRaycaster>();
            return canvas;
        }

        public static RectTransform Panel(Transform parent, string name, Vector2 anchorMin, Vector2 anchorMax,
            Vector2 pivot, Vector2 size, Vector2 anchoredPos, Color color)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.pivot = pivot;
            rt.sizeDelta = size;
            rt.anchoredPosition = anchoredPos;
            go.AddComponent<Image>().color = color;
            return rt;
        }

        public static Text Label(Transform parent, string msg, int size, FontStyle style, Color color,
            TextAnchor align = TextAnchor.MiddleCenter)
        {
            var go = new GameObject("Label", typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            // Do NOT stretch to full parent by default (caused huge overlapping blocks).
            rt.anchorMin = new Vector2(0.5f, 0.5f);
            rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.sizeDelta = new Vector2(800f, 48f);
            var t = go.AddComponent<Text>();
            t.font = Font();
            t.fontSize = size;
            t.fontStyle = style;
            t.color = color;
            t.alignment = align;
            t.text = msg;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.raycastTarget = false;
            return t;
        }

        public static Button MenuButton(Transform parent, string caption, float height)
        {
            var go = new GameObject(caption, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            go.GetComponent<RectTransform>().sizeDelta = new Vector2(0f, height);
            var img = go.AddComponent<Image>();
            img.color = Inactive;
            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;
            var label = Label(go.transform, caption, 28, FontStyle.Bold, Color.white);
            var lrt = label.rectTransform;
            lrt.anchorMin = Vector2.zero;
            lrt.anchorMax = Vector2.one;
            lrt.offsetMin = new Vector2(8f, 4f);
            lrt.offsetMax = new Vector2(-8f, -4f);
            lrt.sizeDelta = Vector2.zero;
            return btn;
        }

        public static void SetButtonVisual(Button btn, bool active, bool detected = false)
        {
            if (btn == null) return;
            var img = btn.GetComponent<Image>();
            if (img == null) return;
            img.color = detected ? Detected : (active ? Active : Inactive);
        }
    }
}
