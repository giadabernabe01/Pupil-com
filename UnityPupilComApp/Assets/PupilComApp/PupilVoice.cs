using System;
using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using System.Threading;
using UnityEngine;

namespace Pupil.ComApp
{
    /// <summary>Windows SAPI voice — announces highlighted menu items.</summary>
    public sealed class PupilVoice : MonoBehaviour
    {
        [SerializeField] bool enabledVoice = true;
        [SerializeField] int rate;

        readonly ConcurrentQueue<string> _queue = new ConcurrentQueue<string>();
        Thread _thread;
        volatile bool _running;
        string _lastSpoken;

        public void Speak(string text)
        {
            if (!enabledVoice || string.IsNullOrWhiteSpace(text)) return;
            text = text.Trim();
            if (string.Equals(text, _lastSpoken, StringComparison.OrdinalIgnoreCase)) return;
            _lastSpoken = text;
            while (_queue.TryDequeue(out _)) { }
            _queue.Enqueue(text);
        }

        public void ResetLast() => _lastSpoken = null;

        void OnEnable()
        {
            if (_running) return;
            _running = true;
            _thread = new Thread(Worker) { IsBackground = true, Name = "PupilCom.Voice" };
            _thread.Start();
        }

        void OnDisable()
        {
            _running = false;
            if (_thread != null && _thread.IsAlive) _thread.Join(500);
            _thread = null;
        }

        void Worker()
        {
            while (_running)
            {
                if (!_queue.TryDequeue(out var text))
                {
                    Thread.Sleep(40);
                    continue;
                }
                try { SpeakSapi(text, rate); }
                catch (Exception e) { Debug.LogWarning("[PupilCom] TTS: " + e.Message); }
            }
        }

        static void SpeakSapi(string text, int rate)
        {
            var type = Type.GetTypeFromProgID("SAPI.SpVoice");
            if (type == null) throw new InvalidOperationException("SAPI.SpVoice non disponibile");
            object voice = Activator.CreateInstance(type);
            try
            {
                type.InvokeMember("Rate", System.Reflection.BindingFlags.SetProperty, null, voice, new object[] { rate });
                try
                {
                    var voices = type.InvokeMember("GetVoices", System.Reflection.BindingFlags.InvokeMethod, null, voice, new object[] { "", "" });
                    if (voices != null)
                    {
                        var voicesType = voices.GetType();
                        var count = Convert.ToInt32(voicesType.InvokeMember("Count", System.Reflection.BindingFlags.GetProperty, null, voices, null));
                        for (var i = 0; i < count; i++)
                        {
                            var token = voicesType.InvokeMember("Item", System.Reflection.BindingFlags.InvokeMethod, null, voices, new object[] { i });
                            var desc = Convert.ToString(token.GetType().InvokeMember("GetDescription", System.Reflection.BindingFlags.InvokeMethod, null, token, null)) ?? "";
                            if (desc.IndexOf("ital", StringComparison.OrdinalIgnoreCase) >= 0
                                || desc.IndexOf("it-IT", StringComparison.OrdinalIgnoreCase) >= 0)
                            {
                                type.InvokeMember("Voice", System.Reflection.BindingFlags.SetProperty, null, voice, new object[] { token });
                                break;
                            }
                        }
                    }
                }
                catch { /* default voice */ }

                type.InvokeMember("Speak", System.Reflection.BindingFlags.InvokeMethod, null, voice, new object[] { text, 0 });
            }
            finally
            {
                if (Marshal.IsComObject(voice)) Marshal.ReleaseComObject(voice);
            }
        }
    }
}
