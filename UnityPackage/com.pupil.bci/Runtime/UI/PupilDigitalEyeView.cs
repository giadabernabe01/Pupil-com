using UnityEngine;
using UnityEngine.UI;

namespace Pupil.Bci
{
    /// <summary>
    /// Digital eye like Pupil-com DigitalEyeWidget: iris + pupil from BPOG / area.
    /// </summary>
    public sealed class PupilDigitalEyeView : MonoBehaviour
    {
        [SerializeField] int texSize = 128;
        [SerializeField] float areaToPixelScale = 1.5f;
        [SerializeField] float smooth = 0.15f;

        RawImage _raw;
        Texture2D _tex;
        Color32[] _pixels;

        float _sx = 0.5f, _sy = 0.5f, _sa;
        float _tx = 0.5f, _ty = 0.5f, _ta;
        bool _tracking;

        public void EnsureUi(Transform parent, Vector2 anchoredPos, Vector2 size)
        {
            if (_raw != null) return;
            var go = new GameObject("DigitalEye", typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = new Vector2(0.5f, 1f);
            rt.anchorMax = new Vector2(0.5f, 1f);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.sizeDelta = size;
            rt.anchoredPosition = anchoredPos;
            _raw = go.AddComponent<RawImage>();
            _raw.raycastTarget = false;

            _tex = new Texture2D(texSize, texSize, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp
            };
            _pixels = new Color32[texSize * texSize];
            _raw.texture = _tex;
            ClearLost();
        }

        public void UpdateEye(float bpogX, float bpogY, float area, bool trackingOk)
        {
            _tx = bpogX;
            _ty = bpogY;
            _ta = area;
            if (!_tracking && trackingOk && area > 0f)
            {
                _sx = bpogX;
                _sy = bpogY;
                _sa = area;
            }
            _tracking = trackingOk && area > 0f;
        }

        void LateUpdate()
        {
            if (_tex == null) return;
            _sx += (_tx - _sx) * smooth;
            _sy += (_ty - _sy) * smooth;
            _sa += (_ta - _sa) * smooth;
            if (!_tracking) ClearLost();
            else DrawTracking();
        }

        void ClearLost()
        {
            var bg = new Color32(0x44, 0x44, 0x44, 255);
            var red = new Color32(220, 60, 60, 255);
            Fill(bg);
            DrawCircle(texSize * 0.5f, texSize * 0.5f, texSize / 3f, bg, new Color32(0, 0, 0, 255));
            // X
            DrawLine(texSize * 0.35f, texSize * 0.35f, texSize * 0.65f, texSize * 0.65f, red, 3);
            DrawLine(texSize * 0.65f, texSize * 0.35f, texSize * 0.35f, texSize * 0.65f, red, 3);
            _tex.SetPixels32(_pixels);
            _tex.Apply(false);
        }

        void DrawTracking()
        {
            var iris = new Color32(0x4a, 0x90, 0xe2, 255);
            var black = new Color32(0, 0, 0, 255);
            var outline = new Color32(20, 20, 20, 255);
            Fill(new Color32(18, 18, 18, 0)); // transparent outside

            float cx = texSize * 0.5f;
            float cy = texSize * 0.5f;
            float irisR = texSize / 3f;
            DrawCircle(cx, cy, irisR, iris, outline);

            float ox = (_sx - 0.5f) * irisR;
            float oy = -(_sy - 0.5f) * irisR; // screen Y up vs texture
            float pr = Mathf.Sqrt(Mathf.Max(0f, _sa)) * areaToPixelScale;
            // tex is ~128px; scale factor similar to Qt widget size ratio
            pr *= texSize / 200f;
            pr = Mathf.Clamp(pr, 5f, irisR * 0.9f);
            DrawCircle(cx + ox, cy + oy, pr, black, black);

            _tex.SetPixels32(_pixels);
            _tex.Apply(false);
        }

        void Fill(Color32 c)
        {
            for (var i = 0; i < _pixels.Length; i++)
                _pixels[i] = c;
        }

        void DrawCircle(float cx, float cy, float r, Color32 fill, Color32 edge)
        {
            int x0 = Mathf.Max(0, Mathf.FloorToInt(cx - r - 2));
            int x1 = Mathf.Min(texSize - 1, Mathf.CeilToInt(cx + r + 2));
            int y0 = Mathf.Max(0, Mathf.FloorToInt(cy - r - 2));
            int y1 = Mathf.Min(texSize - 1, Mathf.CeilToInt(cy + r + 2));
            float r2 = r * r;
            float edgeBand = Mathf.Max(1.5f, r * 0.06f);
            for (var y = y0; y <= y1; y++)
            for (var x = x0; x <= x1; x++)
            {
                float dx = x + 0.5f - cx;
                float dy = y + 0.5f - cy;
                float d2 = dx * dx + dy * dy;
                if (d2 > (r + edgeBand) * (r + edgeBand)) continue;
                float d = Mathf.Sqrt(d2);
                _pixels[y * texSize + x] = d > r - edgeBand ? edge : fill;
            }
        }

        void DrawLine(float x0, float y0, float x1, float y1, Color32 c, int thickness)
        {
            int steps = Mathf.CeilToInt(Mathf.Max(Mathf.Abs(x1 - x0), Mathf.Abs(y1 - y0))) + 1;
            for (var i = 0; i <= steps; i++)
            {
                float t = i / (float)steps;
                float x = Mathf.Lerp(x0, x1, t);
                float y = Mathf.Lerp(y0, y1, t);
                for (var oy = -thickness; oy <= thickness; oy++)
                for (var ox = -thickness; ox <= thickness; ox++)
                {
                    int px = Mathf.RoundToInt(x + ox);
                    int py = Mathf.RoundToInt(y + oy);
                    if (px < 0 || py < 0 || px >= texSize || py >= texSize) continue;
                    _pixels[py * texSize + px] = c;
                }
            }
        }

        void OnDestroy()
        {
            if (_tex != null)
                Destroy(_tex);
        }
    }
}
