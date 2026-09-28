using UnityEngine;
using UnityEngine.UI;

namespace Pupil.Bci
{
    /// <summary>
    /// Minimal vertical signal bar (debug HUD). Assign a UI Slider (vertical) or Image fill.
    /// </summary>
    public sealed class PupilSignalBar : MonoBehaviour
    {
        [SerializeField] PupilBciHub hub;
        [SerializeField] Slider slider;
        [SerializeField] Image fillImage;
        [SerializeField] Text label;
        [SerializeField] Color okColor = new Color(0.18f, 0.8f, 0.44f);
        [SerializeField] Color underColor = new Color(0.91f, 0.3f, 0.24f);
        [SerializeField] Color parColor = new Color(0.49f, 0.99f, 0f);

        float _flashUntil;

        public void Bind(PupilBciHub targetHub, Slider targetSlider = null, Image targetFill = null, Text targetLabel = null)
        {
            Unsubscribe();
            hub = targetHub;
            if (targetSlider != null) slider = targetSlider;
            if (targetFill != null) fillImage = targetFill;
            if (targetLabel != null) label = targetLabel;
            Subscribe();
        }

        void OnEnable() => Subscribe();

        void OnDisable() => Unsubscribe();

        void Subscribe()
        {
            if (hub == null)
                hub = FindObjectOfType<PupilBciHub>();
            if (hub == null)
                return;
            hub.OnSample -= HandleSample;
            hub.OnShortPar -= HandleShort;
            hub.OnSample += HandleSample;
            hub.OnShortPar += HandleShort;
        }

        void Unsubscribe()
        {
            if (hub == null)
                return;
            hub.OnSample -= HandleSample;
            hub.OnShortPar -= HandleShort;
        }

        void HandleShort()
        {
            _flashUntil = Time.unscaledTime + 0.25f;
        }

        void HandleSample(PupilSample s)
        {
            float t = s.Threshold;
            float ratio = t > 1e-6f ? s.FilteredArea / t : 0f;
            // Match Python overlay: map ratio 0.5..1.5-ish into 0..1
            float bar = Mathf.Clamp01((ratio - 0.5f));

            if (slider != null)
                slider.value = bar;
            if (fillImage != null)
            {
                fillImage.fillAmount = bar;
                if (Time.unscaledTime < _flashUntil)
                    fillImage.color = parColor;
                else if (s.UnderThreshold)
                    fillImage.color = underColor;
                else
                    fillImage.color = okColor;
            }

            if (label != null)
            {
                label.text = s.TrackingLost
                    ? "TRACKING LOST"
                    : $"A {s.FilteredArea:0}  S {s.Threshold:0}";
            }
        }
    }
}
