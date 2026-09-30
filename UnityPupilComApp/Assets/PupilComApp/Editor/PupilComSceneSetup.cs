#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Pupil.ComApp.Editor
{
    public static class PupilComSceneSetup
    {
        const string Folder = "Assets/PupilComApp/Scenes";

        [MenuItem("Pupil Com/Create App Scenes + Build Settings")]
        public static void CreateScenes()
        {
            if (!AssetDatabase.IsValidFolder("Assets/PupilComApp"))
                AssetDatabase.CreateFolder("Assets", "PupilComApp");
            if (!AssetDatabase.IsValidFolder(Folder))
                AssetDatabase.CreateFolder("Assets/PupilComApp", "Scenes");

            CreateScene(PupilSceneNames.MainMenu, typeof(MainMenuController));
            CreateScene(PupilSceneNames.Training, typeof(TrainingController));
            CreateScene(PupilSceneNames.YesNo, typeof(YesNoController));
            CreateScene(PupilSceneNames.Keyboard, typeof(KeyboardController));

            var scenes = new System.Collections.Generic.List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            AddBuild(scenes, $"{Folder}/{PupilSceneNames.MainMenu}.unity", true);
            AddBuild(scenes, $"{Folder}/{PupilSceneNames.Training}.unity", true);
            AddBuild(scenes, $"{Folder}/{PupilSceneNames.YesNo}.unity", true);
            AddBuild(scenes, $"{Folder}/{PupilSceneNames.Keyboard}.unity", true);
            // Space Evaders scene should already be in Build Settings — do not remove it.
            EditorBuildSettings.scenes = scenes.ToArray();

            AssetDatabase.SaveAssets();
            Debug.Log("[PupilCom] Scene create: " + Folder +
                      "\nImposta sul MainMenuController il nome esatto della scena Space Evaders già presente nel progetto.");
        }

        static void CreateScene(string name, System.Type controllerType)
        {
            var path = $"{Folder}/{name}.unity";
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var go = new GameObject(name + "_Root");
            go.AddComponent(controllerType);
            EditorSceneManager.SaveScene(scene, path);
        }

        static void AddBuild(System.Collections.Generic.List<EditorBuildSettingsScene> list, string path, bool enabled)
        {
            for (var i = 0; i < list.Count; i++)
                if (list[i].path == path) return;
            list.Add(new EditorBuildSettingsScene(path, enabled));
        }
    }
}
#endif
