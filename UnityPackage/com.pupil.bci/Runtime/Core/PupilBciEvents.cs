using System;
using UnityEngine;
using UnityEngine.Events;

namespace Pupil.Bci
{
    [Serializable]
    public class PupilSampleEvent : UnityEvent<PupilSample> { }

    /// <summary>One processed frame snapshot.</summary>
    [Serializable]
    public struct PupilSample
    {
        public float RawArea;
        public float FilteredArea;
        public float Threshold;
        public float BpogX;
        public float BpogY;
        public bool UnderThreshold;
        public int Status; // 0 none, 1 short, 2 long, 3 extra
        public bool TrackingLost;
    }

    /// <summary>
    /// Optional UnityEvent wrappers for Inspector wiring (in addition to C# events on the Hub).
    /// </summary>
    [Serializable]
    public class PupilBciUnityEvents
    {
        public UnityEvent OnShortPar;
        public UnityEvent OnLongPar;
        public UnityEvent OnExtraPar;
        public UnityEvent OnTrackingLost;
        public UnityEvent OnTrackingOk;
        public PupilSampleEvent OnSample;
    }
}
