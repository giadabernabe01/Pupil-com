using UnityEngine;
using UnityEngine.SceneManagement;

namespace Pupil.ComApp
{
    public static class PupilSceneRouter
    {
        public static void Go(string sceneName)
        {
            if (string.IsNullOrWhiteSpace(sceneName))
            {
                Debug.LogError("[PupilCom] Scene name vuoto.");
                return;
            }
            CleanupTransientUi();
            SceneManager.LoadScene(sceneName);
        }

        public static void GoMainMenu() => Go(PupilSceneNames.MainMenu);
        public static void GoTraining() => Go(PupilSceneNames.Training);
        public static void GoYesNo() => Go(PupilSceneNames.YesNo);
        public static void GoKeyboard() => Go(PupilSceneNames.Keyboard);

        public static void GoSpaceEvaders()
        {
            var name = PupilSession.Instance != null
                ? PupilSession.Instance.SpaceEvadersScene
                : PupilSceneNames.SpaceEvadersDefault;
            Go(name);
        }

        /// <summary>Remove menu/keyboard overlays + helper camera before loading the game.</summary>
        public static void CleanupTransientUi()
        {
            DestroyByName("PupilMainMenuCanvas");
            DestroyByName("PupilTrainingCanvas");
            DestroyByName("PupilYesNoCanvas");
            DestroyByName("PupilKeyboardCanvas");
            DestroyByName("PupilUiCamera");
        }

        static void DestroyByName(string name)
        {
            var all = Object.FindObjectsOfType<Transform>();
            for (var i = 0; i < all.Length; i++)
            {
                if (all[i] != null && all[i].name == name && all[i].parent == null)
                    Object.Destroy(all[i].gameObject);
            }
        }
    }
}
