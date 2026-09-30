using UnityEngine;
using Pupil.Bci;

namespace Pupil.ComApp
{
    /// <summary>
    /// Persistent BCI session across Pupil-com scenes: Hub + PAR bar + Gazepoint setup + voice.
    /// Created from Main Menu if missing. Does not live inside com.pupil.bci.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public sealed class PupilSession : MonoBehaviour
    {
        public static PupilSession Instance { get; private set; }

        [Header("Space Evaders")]
        [Tooltip("Exact Unity scene name of your existing Space Evaders / Galaxy / ParTraining scene.")]
        [SerializeField] string spaceEvadersScene = PupilSceneNames.SpaceEvadersDefault;

        [Header("Timings")]
        [SerializeField] float menuScanSec = 3.0f;
        [SerializeField] float ynScanSec = 3.5f;
        [SerializeField] float trainingInitSec = 5f;
        [SerializeField] float trainingShortTaskSec = 2f;
        [SerializeField] float trainingLongTaskSec = 5f;
        [SerializeField] float trainingFarSec = 3f;
        [SerializeField] float keyboardScanSec = 2.4f;
        [SerializeField] float menuCooldownSec = 2.5f;

        PupilBciHub _hub;
        PupilVoice _voice;
        PupilLiveSignalStrip _strip;
        PupilBciConfig _config;

        public PupilBciHub Hub => _hub;
        public PupilVoice Voice => _voice;
        public string SpaceEvadersScene => spaceEvadersScene;
        public float MenuScanSec => menuScanSec;
        public float YnScanSec => ynScanSec;
        public float TrainingInitSec => trainingInitSec;
        public float TrainingShortTaskSec => trainingShortTaskSec;
        public float TrainingLongTaskSec => trainingLongTaskSec;
        public float TrainingFarSec => trainingFarSec;
        public float KeyboardScanSec => keyboardScanSec;
        public float MenuCooldownSec => menuCooldownSec;

        public static PupilSession EnsureExists(string spaceEvadersSceneOverride = null)
        {
            if (Instance != null)
            {
                if (!string.IsNullOrWhiteSpace(spaceEvadersSceneOverride))
                    Instance.spaceEvadersScene = spaceEvadersSceneOverride;
                return Instance;
            }

            var go = new GameObject("PupilSession");
            var session = go.AddComponent<PupilSession>();
            if (!string.IsNullOrWhiteSpace(spaceEvadersSceneOverride))
                session.spaceEvadersScene = spaceEvadersSceneOverride;
            return session;
        }

        void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }

            Instance = this;
            DontDestroyOnLoad(gameObject);
            BuildBci();
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
        }

        void BuildBci()
        {
            _hub = GetComponent<PupilBciHub>() ?? gameObject.AddComponent<PupilBciHub>();
            _config = PupilBciConfig.CreateRuntimeDefaults();
            _config.enableLongPar = true; // training / pause / keyboard
            _hub.ApplyConfig(_config);

            _voice = GetComponent<PupilVoice>() ?? gameObject.AddComponent<PupilVoice>();
            _strip = GetComponent<PupilLiveSignalStrip>() ?? gameObject.AddComponent<PupilLiveSignalStrip>();
            _strip.Bind(_hub);

            if (GetComponent<PupilGazepointSetupOverlay>() == null)
                gameObject.AddComponent<PupilGazepointSetupOverlay>();

            if (!_hub.GazepointProcessRunning)
                _hub.TryOpenGazepoint(out _);
        }

        public void SetSpaceEvadersScene(string sceneName)
        {
            if (!string.IsNullOrWhiteSpace(sceneName))
                spaceEvadersScene = sceneName;
        }
    }
}
