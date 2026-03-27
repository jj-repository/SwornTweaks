# Update System

**UpdateChecker:** reads VERSION from `GITHUB_CONFIGURATOR` (main branch), compares semver.

**DownloadWorker:** generic QThread downloader. Optional `verify_ref`/`verify_filename` params trigger git blob SHA verification via `_verify_file_against_github()`.

**DLL download:** `GITHUB_DLL` (main branch) → `{mods_path}/SwornTweaks.dll`, verified against `main`.

**Configurator update:**
- As .py: downloads `GITHUB_CONFIGURATOR` → replaces `sys.argv[0]`, verified against `main`
- As .exe: downloads `GITHUB_EXE` (release asset) → replaces `sys.executable`, no git verification (binary release asset)

**Integrity helpers** (module-level):
- `_compute_git_blob_sha(content)` — `SHA1("blob {len}\0{content}")`
- `_verify_file_against_github(ref, filename, content)` — GitHub Contents API, raises `RuntimeError` on mismatch

Repo: `jj-repository/SwornTweaks`
