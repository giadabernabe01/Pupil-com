using System.Collections.Generic;

namespace Pupil.Bci
{
    /// <summary>
    /// Faithful port of Pupil-com DataProcessing.AreaFilter (Gazepoint ranges).
    /// </summary>
    public sealed class AreaFilter
    {
        readonly float _amin;
        readonly float _amax;
        readonly float _ebfThresh;
        readonly int _maxArrayLen;
        readonly int _fps;
        readonly float _timeoutSec;

        readonly Queue<float> _raw = new Queue<float>();
        readonly Queue<float> _areas = new Queue<float>();
        readonly Queue<float> _diffs = new Queue<float>();
        readonly Queue<float> _ebf = new Queue<float>();
        readonly Queue<float> _fin = new Queue<float>();

        int _rejectCount;
        bool _areaNotValid;
        double _areaNotValidTime;

        public bool TimeoutTriggered { get; private set; }
        public bool AreaNotValid => _areaNotValid;
        /// <summary>True this frame when EBF held the previous value (blink spike suppress).</summary>
        public bool EbfBlinkSuppressed { get; private set; }

        public AreaFilter(int fps = 60, float timeoutSec = 5f)
        {
            // Gazepoint-only package
            _amin = 50f;
            _amax = 1000f;
            _ebfThresh = 100f;
            _maxArrayLen = 1000;
            _fps = fps > 0 ? fps : 60;
            _timeoutSec = timeoutSec;
        }

        public float? Filter(float newArea)
        {
            EbfBlinkSuppressed = false;
            EnqueueCapped(_raw, newArea, _maxArrayLen);

            if (_amin <= newArea && newArea <= _amax)
            {
                EnqueueCapped(_areas, newArea, _maxArrayLen);
                if (_areaNotValid)
                {
                    _areaNotValid = false;
                    _areaNotValidTime = 0.0;
                    TimeoutTriggered = false;
                }
            }
            else if (_areas.Count > 0)
            {
                EnqueueCapped(_areas, PeekLast(_areas), _maxArrayLen);
                if (!_areaNotValid)
                {
                    _areaNotValid = true;
                    _areaNotValidTime = Now();
                }
                else
                {
                    var elapsed = Now() - _areaNotValidTime;
                    if (elapsed > _timeoutSec && !TimeoutTriggered)
                        TimeoutTriggered = true;
                }
            }
            else
            {
                return newArea;
            }

            if (_areas.Count == 0)
                return null;

            EnqueueCapped(_ebf, PeekLast(_areas), _maxArrayLen);
            if (_ebf.Count > 1)
            {
                var ebfArr = ToArray(_ebf);
                var diff = System.Math.Abs(ebfArr[ebfArr.Length - 1] - ebfArr[ebfArr.Length - 2]);
                EnqueueCapped(_diffs, (float)diff, _maxArrayLen);

                var winLen = _fps / 4;
                if (_diffs.Count > winLen + 1)
                {
                    var diffsArr = ToArray(_diffs);
                    // recent_diffs = list[:-1][-win_len:]
                    var endExclusive = diffsArr.Length - 1;
                    var start = System.Math.Max(0, endExclusive - winLen);
                    float baseline = 0f;
                    var n = 0;
                    for (var i = start; i < endExclusive; i++)
                    {
                        baseline += diffsArr[i];
                        n++;
                    }
                    if (n > 0)
                        baseline /= n;

                    if (diff > _ebfThresh + baseline)
                    {
                        _rejectCount++;
                        var maxRejects = (int)(_fps * 0.8f);
                        if (_rejectCount < maxRejects)
                        {
                            // Short spike/blink: reject and hold old value
                            ReplaceLast(_ebf, ebfArr[ebfArr.Length - 2]);
                            ReplaceLast(_diffs, baseline);
                            EbfBlinkSuppressed = true;
                        }
                        else
                        {
                            _rejectCount = 0;
                        }
                    }
                    else
                    {
                        _rejectCount = 0;
                    }
                }
            }

            var maWin = _fps / 2;
            float res;
            var ebfList = ToArray(_ebf);
            if (ebfList.Length >= maWin)
            {
                float sum = 0f;
                for (var i = ebfList.Length - maWin; i < ebfList.Length; i++)
                    sum += ebfList[i];
                res = sum / maWin;
            }
            else
            {
                res = ebfList[ebfList.Length - 1];
            }

            EnqueueCapped(_fin, res, _maxArrayLen);
            return res;
        }

        public void Reset()
        {
            _raw.Clear();
            _areas.Clear();
            _diffs.Clear();
            _ebf.Clear();
            _fin.Clear();
            _areaNotValid = false;
            _areaNotValidTime = 0.0;
            TimeoutTriggered = false;
            _rejectCount = 0;
            EbfBlinkSuppressed = false;
        }

        static double Now() =>
            System.DateTime.UtcNow.Subtract(new System.DateTime(1970, 1, 1)).TotalSeconds;

        static void EnqueueCapped(Queue<float> q, float v, int max)
        {
            q.Enqueue(v);
            while (q.Count > max)
                q.Dequeue();
        }

        static float PeekLast(Queue<float> q)
        {
            var arr = q.ToArray();
            return arr[arr.Length - 1];
        }

        static void ReplaceLast(Queue<float> q, float v)
        {
            var arr = q.ToArray();
            q.Clear();
            for (var i = 0; i < arr.Length - 1; i++)
                q.Enqueue(arr[i]);
            q.Enqueue(v);
        }

        static float[] ToArray(Queue<float> q) => q.ToArray();
    }
}
