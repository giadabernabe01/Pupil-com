using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Pupil.ComApp
{
    public sealed class PupilScanList
    {
        readonly List<Button> _items = new List<Button>();
        readonly List<string> _speakAs = new List<string>();
        readonly PupilVoice _voice;

        public float ScanInterval = 3.5f;
        public int Index { get; private set; }
        public bool Running { get; private set; }
        public int Count => _items.Count;

        float _scanStart;
        int _lastSpoken = -1;

        public PupilScanList(PupilVoice voice) => _voice = voice;

        public void SetItems(IList<Button> buttons, IList<string> speakLabels = null)
        {
            _items.Clear();
            _speakAs.Clear();
            for (var i = 0; i < buttons.Count; i++)
            {
                _items.Add(buttons[i]);
                var speak = speakLabels != null && i < speakLabels.Count && !string.IsNullOrEmpty(speakLabels[i])
                    ? speakLabels[i]
                    : buttons[i]?.GetComponentInChildren<Text>()?.text ?? $"voce {i + 1}";
                _speakAs.Add(speak);

                // Mouse: clicking a button highlights + announces it
                var captured = i;
                if (buttons[i] != null)
                {
                    buttons[i].onClick.AddListener(() => FocusIndex(captured, announce: true));
                }
            }
            Index = 0;
            _lastSpoken = -1;
            _scanStart = Time.unscaledTime;
            RefreshVisuals();
        }

        public void Start()
        {
            Running = true;
            Index = 0;
            _lastSpoken = -1;
            _scanStart = Time.unscaledTime;
            _voice?.ResetLast();
            RefreshVisuals();
            Announce();
        }

        public void Stop(bool clearHighlight = true)
        {
            Running = false;
            if (!clearHighlight) return;
            for (var i = 0; i < _items.Count; i++)
                PupilUiKit.SetButtonVisual(_items[i], false);
        }

        public void Tick()
        {
            if (!Running || _items.Count == 0) return;
            if (Time.unscaledTime - _scanStart < ScanInterval) return;
            Move(1, announce: true);
        }

        /// <summary>Manual step (keyboard). Resets auto-scan timer.</summary>
        public void Move(int delta, bool announce = true)
        {
            if (_items.Count == 0) return;
            Index = (Index + delta) % _items.Count;
            if (Index < 0) Index += _items.Count;
            _scanStart = Time.unscaledTime;
            RefreshVisuals();
            if (announce) Announce(force: true);
        }

        public void FocusIndex(int index, bool announce = true)
        {
            if (_items.Count == 0) return;
            Index = Mathf.Clamp(index, 0, _items.Count - 1);
            _scanStart = Time.unscaledTime;
            RefreshVisuals();
            if (announce) Announce(force: true);
        }

        public Button Current =>
            _items.Count > 0 && Index >= 0 && Index < _items.Count ? _items[Index] : null;

        public string CurrentLabel =>
            _speakAs.Count > 0 && Index >= 0 && Index < _speakAs.Count ? _speakAs[Index] : "";

        public void MarkDetected()
        {
            // Only illuminate the chosen item — do not paint others red (confusing).
            for (var i = 0; i < _items.Count; i++)
                PupilUiKit.SetButtonVisual(_items[i], active: i == Index, detected: false);
        }

        public void MarkSelectedOnly()
        {
            for (var i = 0; i < _items.Count; i++)
            {
                if (i == Index)
                    PupilUiKit.SetButtonVisual(_items[i], active: true);
                else
                    PupilUiKit.SetButtonVisual(_items[i], active: false);
            }
        }

        void RefreshVisuals()
        {
            for (var i = 0; i < _items.Count; i++)
                PupilUiKit.SetButtonVisual(_items[i], i == Index);
        }

        void Announce(bool force = false)
        {
            if (!force && Index == _lastSpoken) return;
            _lastSpoken = Index;
            if (Index >= 0 && Index < _speakAs.Count)
            {
                _voice?.ResetLast();
                _voice?.Speak(_speakAs[Index]);
            }
        }
    }
}
