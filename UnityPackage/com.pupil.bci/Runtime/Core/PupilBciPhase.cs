namespace Pupil.Bci
{
    /// <summary>Guided connection lifecycle — games should wait for <see cref="Ready"/> before PAR gameplay.</summary>
    public enum PupilBciPhase
    {
        /// <summary>Hub not started.</summary>
        Idle = 0,
        /// <summary>TCP not connected — open Gazepoint Control.</summary>
        WaitingForGazepoint = 1,
        /// <summary>TCP up but pupil area invalid / eye not tracked.</summary>
        WaitingForValidEye = 2,
        /// <summary>Collecting relaxed baseline (look FAR).</summary>
        CollectingBaseline = 3,
        /// <summary>PAR detection active.</summary>
        Ready = 4,
        /// <summary>Was ready, then lost signal for too long.</summary>
        TrackingLost = 5
    }
}
