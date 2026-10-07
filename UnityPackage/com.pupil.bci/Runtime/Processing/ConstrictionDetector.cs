using System.Collections.Generic;

namespace Pupil.Bci
{
    /// <summary>
    /// Port of pacchetto-gioco/constriction.py ConstrictionMonitor:
    /// baseline SMA × thresh, short/long/extra, plus FP mitigations
    /// #3 tracking-loss during drop and #4 refractory after EBF blink suppress.
    /// Returns: 0 none, 1 short, 2 long, 3 extra-long.
    /// </summary>
    public sealed class ConstrictionDetector
    {
        const int DropMinFramesForRatio = 8;

        readonly int _fps;
        readonly float _thresh;
        readonly float _shortDur;
        readonly float _longDur;
        readonly float _extraDur;
        readonly bool _enableLongPar;
        readonly bool _enableExtraPar;
        readonly float _invalidRatioMax;
        readonly int _invalidConsecMax;
        readonly float _refractoryAfterEbfSec;

        readonly Queue<float> _baseline;
        readonly int _baselineMax;

        double? _dropStartTime;
        bool _shortHandled;
        bool _longHandled;
        bool _extraHandled;
        float? _exitThresh;
        bool _aboveMa;
        int _crossCount;

        int _dropFrameCount;
        int _dropInvalidCount;
        int _dropInvalidConsec;
        double _refractoryUntil;

        public float CurrentSmaThresh { get; private set; }
        public float? ExitThresh => _exitThresh;
        public string LastDiscardReason { get; private set; }

        public ConstrictionDetector(
            int fps = 60,
            float thresh = 0.85f,
            float shortDur = 0.3f,
            float longDur = 3f,
            float extraDur = 5f,
            bool enableLongPar = false,
            bool enableExtraPar = false,
            float invalidRatioMax = 0.35f,
            int invalidConsecMax = 12,
            float refractoryAfterEbfSec = 0.35f)
        {
            _fps = fps > 0 ? fps : 60;
            _thresh = thresh;
            _shortDur = shortDur;
            _longDur = longDur;
            _extraDur = extraDur;
            _enableLongPar = enableLongPar;
            _enableExtraPar = enableExtraPar;
            _invalidRatioMax = invalidRatioMax;
            _invalidConsecMax = invalidConsecMax > 0 ? invalidConsecMax : 12;
            _refractoryAfterEbfSec = refractoryAfterEbfSec;
            _baselineMax = System.Math.Max(1, (int)System.Math.Round(_fps * 2.0));
            _baseline = new Queue<float>(_baselineMax + 1);
        }

        public void ResetMonitor()
        {
            ClearDrop();
            _refractoryUntil = 0.0;
            LastDiscardReason = null;
        }

        public void ClearBaseline()
        {
            _baseline.Clear();
            CurrentSmaThresh = 0f;
            ResetMonitor();
        }

        /// <summary>Call when AreaFilter suppresses a blink spike (EBF hold).</summary>
        public void NotifyEbfBlink()
        {
            _refractoryUntil = Now() + System.Math.Max(0.05, _refractoryAfterEbfSec);
            if (_dropStartTime.HasValue && !_shortHandled)
            {
                LastDiscardReason = "candidato scartato: blink EBF — refrattario "
                    + _refractoryAfterEbfSec.ToString("0.00") + "s";
                ClearDrop();
            }
        }

        /// <summary>Fill baseline buffer (e.g. during init). Returns true when full.</summary>
        public bool CollectBaseline(float filtArea)
        {
            if (filtArea <= 0f)
                return false;
            if (_baseline.Count < _baselineMax)
                EnqueueCapped(_baseline, filtArea, _baselineMax);
            return _baseline.Count >= _baselineMax;
        }

        /// <param name="rawValid">False when Gazepoint sample is unusable (LPV=0 / area 0).</param>
        public int Detect(float filtArea, bool rawValid = true)
        {
            LastDiscardReason = null;

            // Tracking hole while a drop is active (mitigation #3)
            if (filtArea <= 0f)
            {
                if (_dropStartTime.HasValue)
                {
                    _dropFrameCount++;
                    _dropInvalidCount++;
                    _dropInvalidConsec++;
                    if (TrackingBad())
                        CancelDropTracking();
                }
                return 0;
            }

            double now = Now();
            bool inRefractory = now < _refractoryUntil;

            if (_baseline.Count > 0)
            {
                float sum = 0f;
                foreach (var v in _baseline)
                    sum += v;
                CurrentSmaThresh = (sum / _baseline.Count) * _thresh;
            }
            else
            {
                CurrentSmaThresh = 0f;
            }

            float activeThresh = _shortHandled && _exitThresh.HasValue
                ? _exitThresh.Value
                : CurrentSmaThresh;

            if (filtArea < activeThresh)
            {
                // Mitigation #4: do not start a new drop during refractory
                if (!_dropStartTime.HasValue && inRefractory)
                    return 0;

                // Mitigation #4: clear young drops during refractory
                if (inRefractory && _dropStartTime.HasValue)
                {
                    if (!_shortHandled)
                    {
                        LastDiscardReason = "candidato scartato: in refrattario post-blink EBF";
                        ClearDrop();
                    }
                    return 0;
                }

                _aboveMa = filtArea > CurrentSmaThresh;

                if (!_dropStartTime.HasValue)
                {
                    _dropStartTime = now;
                    _exitThresh = CurrentSmaThresh;
                    _aboveMa = false;
                    _crossCount = 0;
                    _dropFrameCount = 0;
                    _dropInvalidCount = 0;
                    _dropInvalidConsec = 0;
                }

                // Mitigation #3 — track sample validity during drop
                _dropFrameCount++;
                if (rawValid)
                {
                    _dropInvalidConsec = 0;
                }
                else
                {
                    _dropInvalidCount++;
                    _dropInvalidConsec++;
                    if (TrackingBad())
                    {
                        CancelDropTracking();
                        return 0;
                    }
                }

                var elapsed = now - _dropStartTime.Value;

                if (_aboveMa && _crossCount == 0)
                    _crossCount++;
                else if (!_aboveMa && _crossCount == 1)
                    _crossCount++;

                if (_crossCount == 2)
                {
                    ClearDrop();
                    EnqueueCapped(_baseline, filtArea, _baselineMax);
                    return 0;
                }

                if (_enableExtraPar && elapsed >= _extraDur)
                {
                    if (!_extraHandled)
                    {
                        _extraHandled = true;
                        return 3;
                    }
                }
                else if (_enableLongPar && elapsed >= _longDur)
                {
                    if (!_longHandled)
                    {
                        _longHandled = true;
                        return 2;
                    }
                }
                else if (elapsed >= _shortDur)
                {
                    if (!_shortHandled)
                    {
                        if (TrackingBad())
                        {
                            CancelDropTracking();
                            return 0;
                        }
                        _shortHandled = true;
                        return 1;
                    }
                }

                EnqueueCapped(_baseline, filtArea, _baselineMax);
            }
            else
            {
                ClearDrop();
                EnqueueCapped(_baseline, filtArea, _baselineMax);
            }

            return 0;
        }

        void CancelDropTracking()
        {
            float ratio = _dropFrameCount > 0
                ? _dropInvalidCount / (float)_dropFrameCount
                : 0f;
            LastDiscardReason =
                "candidato scartato: tracking perso (blink?) — invalidi "
                + _dropInvalidCount + "/" + _dropFrameCount
                + " (" + (ratio * 100f).ToString("0") + "%), consec="
                + _dropInvalidConsec;
            ClearDrop();
        }

        bool TrackingBad()
        {
            if (_dropInvalidConsec >= _invalidConsecMax)
                return true;
            if (_dropFrameCount >= DropMinFramesForRatio)
            {
                float ratio = _dropInvalidCount / (float)_dropFrameCount;
                if (ratio > _invalidRatioMax)
                    return true;
            }
            return false;
        }

        void ClearDrop()
        {
            _dropStartTime = null;
            _shortHandled = false;
            _longHandled = false;
            _extraHandled = false;
            _exitThresh = null;
            _aboveMa = false;
            _crossCount = 0;
            _dropFrameCount = 0;
            _dropInvalidCount = 0;
            _dropInvalidConsec = 0;
        }

        static double Now() =>
            System.DateTime.UtcNow.Subtract(new System.DateTime(1970, 1, 1)).TotalSeconds;

        static void EnqueueCapped(Queue<float> q, float v, int max)
        {
            q.Enqueue(v);
            while (q.Count > max)
                q.Dequeue();
        }
    }
}
