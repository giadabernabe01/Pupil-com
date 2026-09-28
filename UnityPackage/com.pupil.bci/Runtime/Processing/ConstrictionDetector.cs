using System.Collections.Generic;

namespace Pupil.Bci
{
    /// <summary>
    /// Faithful port of Pupil-com ConstrictionMonitor.
    /// Returns: 0 none, 1 short, 2 long, 3 extra-long.
    /// </summary>
    public sealed class ConstrictionDetector
    {
        readonly int _fps;
        readonly float _thresh;
        readonly float _shortDur;
        readonly float _longDur;
        readonly float _extraDur;
        readonly bool _enableLongPar;
        readonly bool _enableExtraPar;

        readonly Queue<float> _baseline;
        readonly int _baselineMax;

        double? _dropStartTime;
        bool _shortHandled;
        bool _longHandled;
        bool _extraHandled;
        float? _exitThresh;
        bool _aboveMa;
        int _crossCount;

        public float CurrentSmaThresh { get; private set; }
        public float? ExitThresh => _exitThresh;

        public ConstrictionDetector(
            int fps = 60,
            float thresh = 0.85f,
            float shortDur = 0.2f,
            float longDur = 3f,
            float extraDur = 5f,
            bool enableLongPar = false,
            bool enableExtraPar = false)
        {
            _fps = fps > 0 ? fps : 60;
            _thresh = thresh;
            _shortDur = shortDur;
            _longDur = longDur;
            _extraDur = extraDur;
            _enableLongPar = enableLongPar;
            _enableExtraPar = enableExtraPar;
            _baselineMax = System.Math.Max(1, (int)System.Math.Round(_fps * 2.0));
            _baseline = new Queue<float>(_baselineMax + 1);
        }

        public void ResetMonitor()
        {
            _dropStartTime = null;
            _shortHandled = false;
            _longHandled = false;
            _extraHandled = false;
            _exitThresh = null;
            _crossCount = 0;
        }

        public void ClearBaseline()
        {
            _baseline.Clear();
            CurrentSmaThresh = 0f;
            ResetMonitor();
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

        public int Detect(float filtArea)
        {
            if (filtArea <= 0f)
                return 0;

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
                _aboveMa = filtArea > CurrentSmaThresh;

                if (!_dropStartTime.HasValue)
                {
                    _dropStartTime = Now();
                    _exitThresh = CurrentSmaThresh;
                    _aboveMa = false;
                    _crossCount = 0;
                }

                var elapsed = Now() - _dropStartTime.Value;

                if (_aboveMa && _crossCount == 0)
                    _crossCount++;
                else if (!_aboveMa && _crossCount == 1)
                    _crossCount++;

                if (_crossCount == 2)
                {
                    _exitThresh = null;
                    _dropStartTime = null;
                    _shortHandled = false;
                    _longHandled = false;
                    _extraHandled = false;
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
                        _shortHandled = true;
                        return 1;
                    }
                }

                // Do not poison baseline with constriction samples (keeps threshold stable)
            }
            else
            {
                _exitThresh = null;
                _dropStartTime = null;
                _shortHandled = false;
                _longHandled = false;
                _extraHandled = false;
                EnqueueCapped(_baseline, filtArea, _baselineMax);
            }

            return 0;
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
