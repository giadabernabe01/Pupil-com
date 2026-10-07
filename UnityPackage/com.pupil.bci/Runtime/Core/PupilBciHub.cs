using System;
using System.Collections.Generic;
using UnityEngine;

namespace Pupil.Bci
{
    /// <summary>
    /// Orchestrates Gazepoint → filter → PAR with an explicit setup pipeline:
    /// WaitingForGazepoint → WaitingForValidEye → CollectingBaseline → Ready.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public sealed class PupilBciHub : MonoBehaviour
    {
        static PupilBciHub _instance;

        [SerializeField] PupilBciConfig config;
        [SerializeField] bool autoStart = true;
        [SerializeField] bool logEvents;
        [Tooltip("Keep Hub alive across scene loads so PAR / bar work in menus too.")]
        [SerializeField] bool persistAcrossScenes = true;
        [SerializeField] PupilBciUnityEvents unityEvents = new PupilBciUnityEvents();

        GazepointClient _client;
        AreaFilter _filter;
        ConstrictionDetector _detector;
        readonly List<GazepointClient.Sample> _drain = new List<GazepointClient.Sample>(64);

        bool _baselineReady;
        float _baselineStart = -1f;
        float _validEyeSince = -1f;
        bool _wasTrackingLost;
        bool _wasConnected;
        PupilBciPhase _phase = PupilBciPhase.Idle;

        // Short PAR confirm: wait briefly — if Gazepoint loses the eye (blink/close), cancel.
        bool _pendingShortPar;
        float _pendingShortParAt = -1f;
        float _parRefractoryUntil = -1f;

        public event Action OnShortPar;
        public event Action OnLongPar;
        public event Action OnExtraPar;
        public event Action OnTrackingLost;
        public event Action OnTrackingOk;
        public event Action OnReady;
        public event Action<PupilBciPhase> OnPhaseChanged;
        public event Action<PupilSample> OnSample;
        /// <summary>Research/diagnostics: kind + detail (discard reasons, cancels, EBF blinks).</summary>
        public event Action<string, string> OnDiagnostic;

        public float FilteredArea { get; private set; }
        public float RawArea { get; private set; }
        public float Threshold { get; private set; }
        public float BpogX { get; private set; }
        public float BpogY { get; private set; }
        public bool IsUnderThreshold { get; private set; }
        public bool IsTrackingLost { get; private set; }
        public bool IsConnected => _client != null && _client.IsConnected;
        public bool IsBaselineReady => _baselineReady;
        public bool IsReady => _phase == PupilBciPhase.Ready;
        public PupilBciPhase Phase => _phase;
        public string StatusMessage { get; private set; } = "Inattivo";
        public string SetupHint { get; private set; } = "";
        public int ConnectAttempts => _client != null ? _client.ConnectAttempts : 0;
        public string LastConnectionError => _client != null ? _client.LastError : "";
        public bool GazepointProcessRunning => GazepointClient.IsGazepointProcessRunning();
        public PupilBciConfig Config => config;

        public void ApplyConfig(PupilBciConfig newConfig, bool enableLogs = false)
        {
            if (newConfig != null)
                config = newConfig;
            logEvents = enableLogs;

            if (config == null)
                config = PupilBciConfig.CreateRuntimeDefaults();

            RebuildProcessors();
        }

        void Awake()
        {
            if (persistAcrossScenes)
            {
                if (_instance != null && _instance != this)
                {
                    Destroy(gameObject);
                    return;
                }
                _instance = this;
                DontDestroyOnLoad(gameObject);
            }

            if (config == null)
                config = PupilBciConfig.CreateRuntimeDefaults();
            RebuildProcessors();
        }

        void RebuildProcessors()
        {
            _filter = new AreaFilter(config.fps, config.trackingLostSec);
            _detector = new ConstrictionDetector(
                config.fps,
                config.threshold,
                config.shortConstrDur,
                config.longConstrDur,
                config.extraConstrDur,
                config.enableLongPar,
                config.enableExtraPar,
                config.dropInvalidRatioMax,
                config.dropInvalidConsecMax,
                config.refractoryAfterEbfSec);
        }

        void OnEnable()
        {
            if (autoStart)
                StartBci();
        }

        void OnDisable() => StopBci();

        void OnDestroy()
        {
            if (_instance == this)
                _instance = null;
            StopBci();
        }

        public void StartBci()
        {
            if (_client != null && _client.IsRunning)
                return;

            if (_filter == null || _detector == null)
                RebuildProcessors();

            _filter.Reset();
            _detector.ClearBaseline();
            _baselineReady = false;
            _baselineStart = -1f;
            _validEyeSince = -1f;
            _wasTrackingLost = false;
            _wasConnected = false;
            IsTrackingLost = false;
            CancelPendingShortPar();
            _parRefractoryUntil = -1f;

            _client = new GazepointClient(config.host, config.port);
            _client.Start();
            SetPhase(PupilBciPhase.WaitingForGazepoint,
                "In attesa di Gazepoint Control…",
                "1) Accendi l'eye-tracker\n2) Avvia Gazepoint Control\n3) Attendi il tracking\n(riprova automatica sulla porta "
                + config.port + ")");

            if (logEvents)
                Debug.Log($"[PupilBci] Connecting to Gazepoint {config.host}:{config.port}");
        }

        public void StopBci()
        {
            if (_client != null)
            {
                _client.Stop();
                _client.Dispose();
                _client = null;
            }
            SetPhase(PupilBciPhase.Idle, "Fermo", "");
        }

        /// <summary>Force reconnect + restart setup pipeline.</summary>
        public void RetryConnection()
        {
            StopBci();
            StartBci();
        }

        public bool TryOpenGazepoint(out string error)
        {
            var path = config != null ? config.gazepointExePath : null;
            return GazepointWindowFocus.BringToFront(path, maximize: false, out error);
        }

        /// <summary>Focus Gazepoint window if already running (no relaunch). Windowed by default. Windowed by default.</summary>
        public bool FocusGazepointWindow(bool maximize = false) =>
            GazepointWindowFocus.FocusExisting(maximize);

        public void ResetFilters()
        {
            _filter.Reset();
            _detector.ClearBaseline();
            _baselineReady = false;
            _baselineStart = -1f;
            _validEyeSince = -1f;
            IsTrackingLost = false;
            _wasTrackingLost = false;
            CancelPendingShortPar();
            _parRefractoryUntil = -1f;
            if (IsConnected)
                SetPhase(PupilBciPhase.WaitingForValidEye,
                    "Segnale perso — riposiziona lo sguardo",
                    "Guarda dritto / lontano. Aspetta area pupilla valida.");
        }

        public void AbortActiveConstriction()
        {
            _detector?.ResetMonitor();
            CancelPendingShortPar();
        }

        void CancelPendingShortPar()
        {
            _pendingShortPar = false;
            _pendingShortParAt = -1f;
        }

        /// <summary>
        /// True when Gazepoint has lost the eye (closed / blink / out of frame).
        /// That must NEVER count as pupillary constriction.
        /// </summary>
        static bool IsSignalLost(bool pupilValid, float rawArea, bool areaNotValid) =>
            !pupilValid || rawArea <= 1e-3f || areaNotValid;

        void Update()
        {
            if (_client == null)
                return;

            // Phase while not connected (even with empty drain)
            if (!_client.IsConnected)
            {
                if (_wasConnected)
                {
                    _wasConnected = false;
                    _baselineReady = false;
                    _baselineStart = -1f;
                    _validEyeSince = -1f;
                }

                var proc = GazepointProcessRunning;
                SetPhase(PupilBciPhase.WaitingForGazepoint,
                    proc
                        ? $"Gazepoint in esecuzione, ma porta {config.port} chiusa…"
                        : "Gazepoint Control non rilevato",
                    proc
                        ? "Apri Gazepoint Control e abilita lo streaming dati.\nTentativi: " + ConnectAttempts
                          + (string.IsNullOrEmpty(LastConnectionError) ? "" : "\n" + LastConnectionError)
                        : "Avvia Gazepoint Control, poi aspetta o premi Riprova.\nTentativi TCP: " + ConnectAttempts);

                _drain.Clear();
                _client.Drain(_drain); // discard
                return;
            }

            if (!_wasConnected)
            {
                _wasConnected = true;
                _validEyeSince = -1f;
                SetPhase(PupilBciPhase.WaitingForValidEye,
                    "Collegato — cerca l'occhio…",
                    "Posizionati davanti al Gazepoint.\nGuarda LONTANO / rilassato.");
                if (logEvents)
                    Debug.Log("[PupilBci] Gazepoint TCP connected");
            }

            _drain.Clear();
            _client.Drain(_drain);
            if (_drain.Count == 0)
            {
                // Still resolve a deferred short PAR if eye stayed valid.
                TryConfirmPendingShortPar(signalLost: false);
                return;
            }

            // Process every sample in order so a mid-queue signal-loss aborts
            // before a later sample could complete shortDur.
            for (var i = 0; i < _drain.Count; i++)
            {
                var s = _drain[i];
                ProcessSample(s.Area, s.BpogX, s.BpogY, s.PupilValid);
            }
        }

        void ProcessSample(float rawArea, float bx, float by, bool pupilValid)
        {
            RawArea = rawArea;
            BpogX = bx;
            BpogY = by;

            var filtered = _filter.Filter(rawArea);
            if (!filtered.HasValue)
                return;

            FilteredArea = filtered.Value;

            // Mitigation #4: EBF blink suppress → detector refractory (constriction.py)
            if (_filter.EbfBlinkSuppressed)
            {
                EmitDiagnostic("ebf_blink", "AreaFilter ha soppresso uno spike (blink)");
                _detector.NotifyEbfBlink();
                if (!string.IsNullOrEmpty(_detector.LastDiscardReason))
                    EmitDiagnostic("discard_ebf", _detector.LastDiscardReason);
            }

            // Hard rule: no Gazepoint pupil lock ⇒ not a constriction (blink / eyes closed).
            bool signalLost = IsSignalLost(pupilValid, rawArea, _filter.AreaNotValid);
            bool rawValid = pupilValid && rawArea > 1e-3f && rawArea >= config.minValidArea;
            var eyeOk = !signalLost
                && FilteredArea >= config.minValidArea;

            if (_filter.TimeoutTriggered)
            {
                if (!_wasTrackingLost)
                {
                    _wasTrackingLost = true;
                    IsTrackingLost = true;
                    AbortOnSignalLost();
                    SetPhase(PupilBciPhase.TrackingLost,
                        "Occhio non rilevato",
                        "Controlla inquadratura e luce, poi resta fermo.");
                    EmitTrackingLost();
                }
            }
            else if (_wasTrackingLost && eyeOk)
            {
                _wasTrackingLost = false;
                IsTrackingLost = false;
                _baselineReady = false;
                _baselineStart = -1f;
                _validEyeSince = -1f;
                _detector.ClearBaseline();
                CancelPendingShortPar();
                SetPhase(PupilBciPhase.WaitingForValidEye,
                    "Segnale tornato — riparti setup",
                    "Guarda LONTANO per la nuova baseline.");
                EmitTrackingOk();
            }

            if (IsTrackingLost)
            {
                Threshold = _detector.CurrentSmaThresh;
                IsUnderThreshold = false;
                EmitSample(0);
                return;
            }

            // --- SETUP: need stable valid eye before baseline ---
            if (!_baselineReady)
            {
                CancelPendingShortPar();
                if (!eyeOk)
                {
                    _validEyeSince = -1f;
                    _baselineStart = -1f;
                    SetPhase(PupilBciPhase.WaitingForValidEye,
                        "Occhio non valido (area bassa / perso)",
                        "Avvicinati / centra lo sguardo.\nArea attuale: " + FilteredArea.ToString("0"));
                    Threshold = 0f;
                    IsUnderThreshold = false;
                    EmitSample(0);
                    return;
                }

                if (_validEyeSince < 0f)
                    _validEyeSince = Time.realtimeSinceStartup;

                var settle = Time.realtimeSinceStartup - _validEyeSince;
                var needSettle = Mathf.Max(0.2f, config.validEyeSettleSeconds);
                if (settle < needSettle)
                {
                    SetPhase(PupilBciPhase.WaitingForValidEye,
                        $"Segnale ok — stabilizzazione {settle:0.0}/{needSettle:0.0}s",
                        "Resta fermo, sguardo LONTANO.");
                    EmitSample(0);
                    return;
                }

                // Baseline collection
                if (_baselineStart < 0f)
                {
                    _baselineStart = Time.realtimeSinceStartup;
                    _detector.ClearBaseline();
                }

                _detector.CollectBaseline(FilteredArea);
                Threshold = _detector.CurrentSmaThresh;
                IsUnderThreshold = false;

                var blNeed = Mathf.Max(0.5f, config.baselineSeconds);
                var blElapsed = Time.realtimeSinceStartup - _baselineStart;
                SetPhase(PupilBciPhase.CollectingBaseline,
                    $"Baseline {blElapsed:0.0}/{blNeed:0.0}s — guarda LONTANO",
                    "Non avvicinare lo sguardo finché non è pronto.");

                if (blElapsed >= blNeed)
                {
                    _baselineReady = true;
                    SetPhase(PupilBciPhase.Ready,
                        "Pronto — PAR attiva",
                        "Lontano → vicino breve = azione.");
                    if (logEvents)
                        Debug.Log("[PupilBci] Ready (baseline done)");
                    OnReady?.Invoke();
                }

                EmitSample(0);
                return;
            }

            // --- READY: detect PAR ---
            if (_phase != PupilBciPhase.Ready)
                SetPhase(PupilBciPhase.Ready, "Pronto — PAR attiva", "Lontano → vicino breve = azione.");

            Threshold = _detector.CurrentSmaThresh;
            float baselineSma = (config.threshold > 1e-6f && Threshold > 1e-6f)
                ? Threshold / config.threshold
                : 0f;
            float closedFrac = Mathf.Clamp(config.eyeClosedFraction, 0.15f, 0.7f);
            bool eyeClosedDeep = baselineSma > 1e-3f
                && (FilteredArea < baselineSma * closedFrac || rawArea < baselineSma * closedFrac);

            // Deep collapse (eyelid) while samples still look "valid" — Unity-only gate.
            if (config.blockParWhenEyeInvalid && eyeClosedDeep)
            {
                AbortOnSignalLost("eye_closed_deep", "calo area troppo profondo (palpebra?)");
                IsUnderThreshold = false;
                EmitSample(0);
                return;
            }

            // If a deferred short PAR is waiting and the eye lock dies → cancel emit.
            if (config.blockParWhenEyeInvalid && signalLost && _pendingShortPar)
                AbortOnSignalLost("short_par_cancelled", "segnale perso durante conferma short PAR");

            // After a hard abort, ignore PAR briefly while the eye returns.
            if (Time.realtimeSinceStartup < _parRefractoryUntil)
            {
                _detector.ResetMonitor();
                IsUnderThreshold = false;
                EmitSample(0);
                return;
            }

            // constriction.py path: feed detector with rawValid so #3 can cancel blink drops.
            // Do NOT ResetMonitor on every invalid frame — that would skip the invalid ratio logic.
            bool sampleRawValid = config.blockParWhenEyeInvalid ? rawValid && !signalLost : true;
            var status = _detector.Detect(FilteredArea, sampleRawValid);
            Threshold = _detector.CurrentSmaThresh;
            IsUnderThreshold = FilteredArea < Threshold && Threshold > 1e-6f;

            if (status == 0 && !string.IsNullOrEmpty(_detector.LastDiscardReason))
            {
                string kind = _detector.LastDiscardReason.IndexOf("EBF", StringComparison.OrdinalIgnoreCase) >= 0
                    ? "discard_ebf"
                    : "discard_tracking";
                EmitDiagnostic(kind, _detector.LastDiscardReason);
                if (logEvents)
                    Debug.Log("[PupilBci] " + _detector.LastDiscardReason);
            }

            // Never emit PAR on a frame where Gazepoint lost the eye.
            if (config.blockParWhenEyeInvalid && signalLost)
                status = 0;

            if (status == 1)
            {
                // Extra Hub safety: if signal is lost within confirm window, cancel.
                _pendingShortPar = true;
                _pendingShortParAt = Time.realtimeSinceStartup + Mathf.Max(0.03f, config.shortParConfirmSec);
                EmitDiagnostic("short_par_candidate", "sotto soglia per shortDur — in conferma");
                if (logEvents)
                    Debug.Log("[PupilBci] Short PAR candidate — confirming…");
            }
            else if (status == 2)
            {
                if (logEvents) Debug.Log("[PupilBci] Long PAR");
                EmitDiagnostic("long_par", "long constriction");
                OnLongPar?.Invoke();
                unityEvents.OnLongPar?.Invoke();
            }
            else if (status == 3)
            {
                if (logEvents) Debug.Log("[PupilBci] Extra PAR");
                EmitDiagnostic("extra_par", "extra-long constriction");
                OnExtraPar?.Invoke();
                unityEvents.OnExtraPar?.Invoke();
            }

            TryConfirmPendingShortPar(signalLost: false);
            EmitSample(_pendingShortPar ? 0 : status);
        }

        void AbortOnSignalLost(string kind = "signal_loss_abort", string detail = null)
        {
            bool hadPending = _pendingShortPar;
            _detector?.ResetMonitor();
            if (hadPending && logEvents)
                Debug.Log("[PupilBci] Short PAR cancelled — Gazepoint lost eye (blink/close).");
            CancelPendingShortPar();
            // Block new PAR until the eye is stably back
            _parRefractoryUntil = Time.realtimeSinceStartup + Mathf.Max(0.05f, config.afterSignalLostRefractorySec);
            EmitDiagnostic(
                hadPending ? "short_par_cancelled" : kind,
                detail ?? (hadPending
                    ? "short PAR annullato: perdita segnale"
                    : "abort per perdita segnale / occhio chiuso"));
        }

        void TryConfirmPendingShortPar(bool signalLost)
        {
            if (!_pendingShortPar)
                return;
            if (signalLost)
            {
                AbortOnSignalLost("short_par_cancelled", "segnale perso durante conferma short PAR");
                return;
            }
            if (Time.realtimeSinceStartup < _pendingShortParAt)
                return;

            _pendingShortPar = false;
            _pendingShortParAt = -1f;
            if (logEvents) Debug.Log("[PupilBci] Short PAR confirmed");
            EmitDiagnostic("short_par", "short constriction confermata");
            OnShortPar?.Invoke();
            unityEvents.OnShortPar?.Invoke();
        }

        void EmitDiagnostic(string kind, string detail)
        {
            if (string.IsNullOrEmpty(kind)) return;
            OnDiagnostic?.Invoke(kind, detail ?? "");
        }

        void SetPhase(PupilBciPhase phase, string status, string hint)
        {
            StatusMessage = status;
            SetupHint = hint;
            if (_phase == phase)
                return;
            _phase = phase;
            if (logEvents)
                Debug.Log($"[PupilBci] Phase → {phase}: {status}");
            OnPhaseChanged?.Invoke(phase);
        }

        void EmitTrackingLost()
        {
            OnTrackingLost?.Invoke();
            unityEvents.OnTrackingLost?.Invoke();
        }

        void EmitTrackingOk()
        {
            OnTrackingOk?.Invoke();
            unityEvents.OnTrackingOk?.Invoke();
        }

        void EmitSample(int status)
        {
            var sample = new PupilSample
            {
                RawArea = RawArea,
                FilteredArea = FilteredArea,
                Threshold = Threshold,
                BpogX = BpogX,
                BpogY = BpogY,
                UnderThreshold = IsUnderThreshold,
                Status = status,
                TrackingLost = IsTrackingLost
            };
            OnSample?.Invoke(sample);
            unityEvents.OnSample?.Invoke(sample);
        }
    }
}
