# Update System

**UpdateChecker:** reads VERSION from `GITHUB_CONFIGURATOR` (main branch), compares semver.

**DownloadWorker:** generic QThread downloader. Params: `verify_ref`/`verify_filename` for git blob SHA-1, `release_data`/`asset_name` for SHA-256 from `SHA256SUMS` release asset.

**`_do_update()`** fetches latest release data from GitHub API first, then passes to all workers.

**DLL download:** `GITHUB_DLL` (main branch) → `{mods_path}/SwornTweaks.dll`, SHA-1 (git blob) + SHA-256 (release).

**Configurator update:**
- As .py: downloads `GITHUB_CONFIGURATOR` → replaces `sys.argv[0]`, SHA-1 (git blob) + SHA-256
- As .exe: downloads `GITHUB_EXE` (release asset) → replaces `sys.executable`, SHA-256 only (no git blob for binaries)

**Integrity helpers** (module-level):
- `_compute_git_blob_sha(content)` — `SHA1("blob {len}\0{content}")`
- `_get_expected_sha256(release_data, asset_name)` — fetches/caches `SHA256SUMS` from release, returns expected hash
- `_verify_file_against_github(ref, filename, content, release_data, asset_name)` — SHA-1 via GitHub Contents API, then SHA-256 via release `SHA256SUMS`

**CI (`build-exe.yml`):** generates `SHA256SUMS` covering all 4 assets (SwornTweaks.exe, SwornTweaks-Linux, SwornTweaks.dll, configurator.py), uploaded as release asset.

Repo: `jj-repository/SwornTweaks`
