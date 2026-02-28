namespace SwornTweaks.Patches
{
    /// <summary>
    /// Chaos Mode: bypass all blessing prerequisite checks.
    ///
    /// Previous approach (hooking IsValid on blessing subtypes) caused native IL2CPP
    /// crashes because IsValid is a virtual method — Harmony trampolines corrupt the
    /// native vtable. The new approach hooks the non-virtual filter lambda in
    /// BlessingGenerator.GenerateBlessingsInternal instead.
    ///
    /// TODO: Hook BlessingGenerator.__c__DisplayClass33_0._GenerateBlessingsInternal_b__0
    /// </summary>
    static class ChaosModePatch
    {
    }
}
