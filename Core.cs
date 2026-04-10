using MelonLoader;
using SwornTweaks.Patches;

[assembly: MelonInfo(typeof(SwornTweaks.Core), "SwornTweaks", "1.0.0", "Vercility")]
[assembly: MelonGame("Windwalk Games", "SWORN")]

namespace SwornTweaks
{
    public class Core : MelonMod
    {
        public override void OnInitializeMelon()
        {
            Config.Init();
            LoggerInstance.Msg("SwornTweaks loaded.");
        }

        public override void OnApplicationQuit()
        {
            SaveStateSave.DoSave();
        }

        public override void OnSceneWasLoaded(int buildIndex, string sceneName)
        {
            if (!Config.InfiniteRerolls.Value) return;
            try
            {
                Il2Cpp.RerollManager.SetRerolls(500);
                var rm = RerollPatch.Instance;
                if (rm != null) rm.baseRerolls = 500;
            }
            catch { /* RerollManager not ready yet — RerollPatch Postfix handles it */ }
        }
    }
}
