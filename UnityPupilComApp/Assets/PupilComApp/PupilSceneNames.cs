using UnityEngine;

namespace Pupil.ComApp
{
    /// <summary>Build Settings scene names. Rename Space Evaders to match your existing game scene.</summary>
    public static class PupilSceneNames
    {
        public const string MainMenu = "Pupil_MainMenu";
        public const string Training = "Pupil_Training";
        public const string YesNo = "Pupil_YesNo";
        public const string Keyboard = "Pupil_Keyboard";

        /// <summary>Override at runtime via PupilSession.SpaceEvadersScene if needed.</summary>
        public const string SpaceEvadersDefault = "Prototype_GalaxyCampaign";
    }
}
