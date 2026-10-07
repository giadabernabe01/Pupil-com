using UnityEngine;

namespace Pupil.Bci
{
    [CreateAssetMenu(fileName = "PupilBciConfig", menuName = "Pupil BCI/Config", order = 0)]
    public sealed class PupilBciConfig : ScriptableObject
    {
        [Header("Gazepoint")]
        public string host = "127.0.0.1";
        public int port = 4242;

        [Tooltip("Optional full path to Gazepoint.exe (bin64). Leave empty to auto-detect.")]
        public string gazepointExePath = @"C:\Program Files (x86)\Gazepoint\Gazepoint\bin64\Gazepoint.exe";

        [Header("Sampling")]
        public int fps = 60;

        [Header("Constriction")]
        [Tooltip("Threshold multiplier on baseline SMA (Python parameters.json default 0.85).")]
        [Range(0.5f, 1f)]
        public float threshold = 0.85f;

        [Tooltip("Seconds under threshold before short PAR. ~0.3s keeps responsiveness; blinks still cancelled by signal-loss confirm.")]
        public float shortConstrDur = 0.3f;

        [Tooltip("Seconds under threshold before long PAR (only if enableLongPar).")]
        public float longConstrDur = 3f;

        public float extraConstrDur = 5f;

        [Tooltip("Long PAR events (game exit menus, etc.). Off by default.")]
        public bool enableLongPar = false;

        public bool enableExtraPar = false;

        [Tooltip("If true, blinks / eye-lost (LPV=0) abort an in-progress constriction and never fire PAR.")]
        public bool blockParWhenEyeInvalid = true;

        [Tooltip("If filtered area falls below this fraction of baseline SMA, treat as eye closed (not PAR). Intentional near-focus stays above ~0.5–0.7.")]
        [Range(0.15f, 0.7f)]
        public float eyeClosedFraction = 0.45f;

        [Header("Anti false-positive (constriction.py #3 / #4)")]
        [Tooltip("During a drop: cancel if invalid-frame ratio exceeds this (mitigation #3).")]
        [Range(0.15f, 0.8f)]
        public float dropInvalidRatioMax = 0.35f;

        [Tooltip("During a drop: cancel after this many consecutive invalid samples (~0.2s @ 60Hz).")]
        public int dropInvalidConsecMax = 12;

        [Tooltip("After AreaFilter EBF blink suppress, block new PAR for this many seconds (mitigation #4).")]
        public float refractoryAfterEbfSec = 0.35f;

        [Tooltip("After a short-PAR candidate, wait this long; if Gazepoint loses the eye (blink/close), cancel the PAR.")]
        public float shortParConfirmSec = 0.1f;

        [Tooltip("After hard signal loss, block new PAR briefly (Hub gate; in addition to EBF refractory).")]
        public float afterSignalLostRefractorySec = 0.1f;

        [Header("Tracking")]
        [Tooltip("Seconds of invalid pupil area before OnTrackingLost (Python AreaFilter uses 5s).")]
        public float trackingLostSec = 5f;

        [Header("Connection / baseline setup")]
        [Tooltip("Seconds of valid pupil signal required before baseline starts.")]
        public float validEyeSettleSeconds = 1.5f;

        [Tooltip("Seconds to collect baseline (look FAR / relaxed) before detecting PAR.")]
        public float baselineSeconds = 2.5f;

        [Tooltip("Minimum filtered area considered a live eye (Gazepoint).")]
        public float minValidArea = 50f;

        public static PupilBciConfig CreateRuntimeDefaults()
        {
            var c = CreateInstance<PupilBciConfig>();
            c.name = "PupilBciConfig (runtime)";
            return c;
        }
    }
}
