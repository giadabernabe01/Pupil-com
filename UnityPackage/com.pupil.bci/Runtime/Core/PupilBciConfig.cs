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

        [Tooltip("Seconds under threshold before short PAR.")]
        public float shortConstrDur = 0.2f;

        [Tooltip("Seconds under threshold before long PAR (only if enableLongPar).")]
        public float longConstrDur = 3f;

        public float extraConstrDur = 5f;

        [Tooltip("Long PAR events (game exit menus, etc.). Off by default.")]
        public bool enableLongPar = false;

        public bool enableExtraPar = false;

        [Header("Tracking")]
        [Tooltip("Seconds of invalid pupil area before OnTrackingLost.")]
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
