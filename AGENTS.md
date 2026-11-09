# AGENTS.md

Project operating instructions for AI assistants working in this repository.

## Unreal project delivery

The owner chose this GitHub repository for the Unreal remaster on7Nov2026. `DinkRemasterUE/` contains the UE5.8.4 project, source art/audio and imported assets in Git LFS; read its AGENTS.md before changes. The original engine remains at the repository root and is not replaced. Unreal extraction defaults discover this parent repo; standalone sibling layouts also work. Never commit Engine, generated worlds, builds, caches or local credentials.

## Shared Project Memory

- Read this file before doing any work in this repository.
- Treat this file as the shared project memory for AI assistants.
- Do not rely on vendor-specific, proprietary, or hidden memory systems for project facts, preferences, or operating instructions. (except to remember to ALWAYS read this file first before doing anything.  Remember that.)
- Update this file with important repo-specific information learned during work, including build commands, test commands, conventions, decisions, pitfalls, and current project preferences.
- Keep this file accurate and current. Remove or correct stale, misleading, or incorrect information when discovered.
- If information is temporary or uncertain, label it clearly rather than presenting it as permanent fact.

## Testing

- When possible, design automated tests for new features and bug fixes.
- Run relevant automated tests after finishing changes to guard against regressions.
- If tests cannot be run or do not exist, state that clearly in the handoff and describe any manual verification performed.

### Automated smoke test (`-autotest`, added July 2026)

The game has a self-driving smoke test: `dink -autotest` (implies `-window` and
`-skip`, forces a 1024x768 window) runs one scripted session that screenshots
the main menu, installs a DMOD through the live dinknetwork.com browser
pipeline, installs a DMOD from a URL, starts a new game and screenshots it,
deletes everything it installed (saves/continue state are preserved via
backup+restore), writes `autotest/autotest_results.txt` plus
`autotest_mainmenu.png` / `autotest_newgame.png` in the save dir, and quits.
The results file is the authoritative pass/fail channel (`SUMMARY: PASS (5/5)`
on the last line; the process exit code is always 0). Implementation:
`source/AutoTester.cpp` state machine, hooked from `App::Update`/`App::Draw`;
the two test DMODs are constants at the top of that file (browser test looks
up "Cycles of Evil" in the live list; URL test downloads the 24K
`abcdefgh.dmod`, plain http because the Mac build's NetHTTP has no TLS).

Per-platform driver scripts (all honor `NO_PAUSE=1`, exit 0/1, copy artifacts
to `script\testruns\<platform>\`, which is gitignored):

- `script\TestWindows.bat` - runs `bin\winRTDink_Release GL.exe`; build first.
- `script\TestMac.bat` - runs the last dev build on studiomac over ssh
  (`OSX/build/Release/Dink Smallwood HD.app`, produced by BuildMac.bat).
  Requires seth logged into the mac's GUI session.
- `script\TestLinux.bat` - runs the installed flatpak on glados over ssh with
  `DISPLAY=:0` (glados has a real display). BuildFlatpak.bat installs the
  flatpak; rebuild before testing or you test a stale binary.

Gotcha: the Cocoa entry path on Mac never passed argv to the app; `App::Init`
now ingests it via `_NSGetArgc/_NSGetArgv` (this also made `-game`/`-window`
etc work on Mac for the first time).

### DMOD deletion compatibility (October 2026)

Proton's recursive deletion API now requires physical absolute paths. The
menu and autotest use `source/DMODCleanup.h` to turn the usual relative
`dmods/` root into an explicit app-base path, resolve POSIX OS cache aliases,
and delete only one immediate DMOD child. Do not pass `GetDMODRootPath() + name`
straight to the engine deletion API. Failures must be reported; disappearance
of `dmod.diz` alone does not prove the entire folder was removed. Startup's
`temp.dmod` cleanup uses `RemoveFile(path, false)` since a cache path can already
be absolute. The download/unpack cleanup uses file-only deletion as before.
Windows `-game name` can intentionally return an empty relative root; the
helper binds that case to the checked app base too, never to an unchecked cwd.

`tests/dmod_cleanup.cpp` exercises the production helper without starting the
game. From the parent Proton repo, compile with `cl /EHsc /W3 /WX /I shared
RTDink/tests/dmod_cleanup.cpp` (or `g++ -std=c++11 -Wall -Wextra -Werror -I shared`)
and pass the executable to Proton's `tests/deletion_safety.py --native <exe>`.
See `../docs/deletion-safety.md` for complete commands and the build matrix.
The helper tests pass on Windows, Linux, macOS and Emscripten. Windows Release
x64, Linux, macOS Release, HTML5 and Android native arm64 builds were checked.
Android CMake now includes `AutoTester.cpp`, which was previously missing and
broke its link.
These are companion changes in this separate repo; committing Proton alone
does not include them.


## Security

- Never commit sensitive data, including credentials, tokens, passwords, private keys, cookies, customer data, personal data, or machine-specific authentication material.
- If an AI assistant needs authentication data or other secrets for local work, use `agents_secret.md` for those notes.
- `agents_secret.md` must stay ignored by git and must not be committed.
- Do not put secrets in commit messages, logs, issue text, pull request descriptions, generated docs, or other tracked files.
- Before committing, review staged changes for accidental secrets.

## Git

- Never add OpenAI/Codex/Claude etc as a co-author on git commits.
- NEVER `git commit` unless explicitly told to commit.
- NEVER `git push` unless explicitly told to push. "Commit" means commit
  locally only; committing is not permission to push.

## Building (verified July 2026)

### Windows (Release GL x64)

Requires the Proton SDK sibling layout (this repo lives at `proton/RTDink`, SDK at
`proton/shared`) and VS 2026 (v18) Community. Command-line build that works:

```
"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe" windows_vs2017\iPhoneRTDink.sln /p:Configuration="Release GL" /p:Platform=x64 /m
```

Output: `bin\winRTDink_Release GL.exe`. Zero warnings expected: a cleanup pass
(Aug 2026) got Windows Release/Debug GL, Mac and HTML5 builds warning-free, so
treat any new warning as a regression. Two intentional oddities from that pass:
the DinkC parser's `strchr(temp, '=')` calls used to read `strchr(temp, '<=')`
etc but always truncated to '=' (kept, DMOD script compat depends on it), and
MainMenu's CheckForImportedSavedGames platform check preserves its historical
"return if Windows" behavior rather than the "return unless iOS" it appears to
have wanted.

### Windows packaging (`script\BuildAndPackageWindows.bat`)

- Does NOT compile; it packages an already-built `winRTDink_Release GL.exe` into
  `dink.exe`, builds the NSIS installer (`DinkSmallwoodHDInstaller.exe`), and stages
  a portable tree in `script\builds\win`.
- Needs env vars `RT_PROJECTS` (d:\projects) and `RT_PROTON_UTIL`
  (proton\shared\win\utils), plus NSIS at `d:\projects\util\NSIS`.
- It deletes local saves in `bin\dink` (save*.dat, quicksave, autosave,
  continue_state.dat) as a packaging cleanup step; expected.
- sign.bat (in `%RT_PROJECTS%\Signing`, outside this repo) requires THREE args:
  file, description, info URL (feeds signtool `/d` and `/du`). Calling it with 2
  args makes `/du` eat the filename and signing fails. Fixed July 2026: the script
  now passes the URL and aborts if signing fails.
- The staged readme comes from `script\win_installer\readme.txt` (same file the
  NSIS installer ships); the repo root has README.md only.

### Flatpak (`script\BuildFlatpak.bat [x86_64|aarch64] [local]`)

- Builds remotely on the `glados` Linux box over ssh. By default it pushes
  committed HEAD to a `flatpak-build` branch there; uncommitted local changes are
  NOT included.
- Pass `local` (any position) to build the current working tree instead: the
  script makes a throwaway snapshot commit via a temp index (your real index and
  any staged files are untouched) and pushes that. `.gitignore` is respected, and
  saves/`agents_secret.md` are force-stripped from the snapshot as a second layer.
  The CMake install rule also excludes `save*.dat`/`quicksave`/`autosave*`/
  `continue_state` from the flatpak itself, so saves have three layers keeping
  them out.
- The script checks for the freedesktop 24.08 Platform+Sdk on glados and installs
  them `--user` if missing.
- The remote flatpak-builder command runs with `set -o pipefail` so the
  `| tail -5` pipe cannot hide a failed build; the script exits 1 on failure and
  0 on success, and honors `NO_PAUSE=1` to skip the final `pause` for automation.

### macOS (`script/BuildMac.bat [local] [nonotarize] [adhoc]`) (verified July 2026)

- Builds remotely on `seth@studiomac.local` over ssh, same pattern as the
  Flatpak script: pushes committed HEAD (or a `local` working-tree snapshot)
  to a `mac-desktop-build` branch in `~/projects/proton/RTDink` on the Mac,
  runs `script/BuildAndPackageMac.sh` there, and copies the finished
  `DinkSmallwoodHD.dmg` back to `script/`. Honors `NO_PAUSE=1`.
- Layout on the Mac mirrors Windows: RTDink is cloned INSIDE the proton
  checkout (`~/projects/proton/RTDink`). The Xcode project
  (`OSX/RTDink.xcodeproj`) references `../../shared` and `../../RTSimpleApp`,
  so a sibling layout does NOT work.
- Universal binary (arm64 + x86_64), macOS 11+. Audio is SDL2_mixer
  (`RT_USE_SDL_AUDIO`, the define is read by proton's AudioManagerSDL.h), no
  FMOD. Gamepads via GamepadProviderGCController (Apple GameController
  framework, in proton since July 2026; replaced GamepadProviderSDL2, which
  Linux still uses).
- SDL2/SDL2_mixer come from `~/Library/Frameworks` (official universal DMG
  releases, see INSTALL.md). Install with `ditto`/`cp -R`, never `cp -r`,
  which flattens the framework symlinks and later breaks codesign with
  "bundle format is ambiguous".
- Dev builds (plain `xcodebuild -configuration Release`) are ad-hoc signed so
  they work over ssh with a locked keychain, and load SDL2 from
  `~/Library/Frameworks`. The package script embeds the frameworks into the
  .app and does the real Developer ID signing (sign framework `Versions/A`,
  not the top-level `.framework` dir).
- Signing identity: `Developer ID Application: Robinson Technologies
  Corporation (7DA5SJEYK8)` (the old team MK4EZB35P7 found in ancient configs
  is dead). Over ssh the login keychain shows up locked; the package script
  unlocks it with the password read from `~/.rtdink_keychain_pass` on the Mac
  (chmod 600, never committed anywhere).
- Notarization reuses the `patchy-notary` notarytool keychain profile that
  was set up for the Patchy project (the credentials are Apple ID + team, not
  app specific). Override with the NOTARY_PROFILE env var if needed.
- Gotcha fixed July 2026: on OSX `GetDMODRootPath()` returns the absolute
  save path, so it must not be passed to
  `CreateDirectoryRecursively(GetSavePath(), ...)` the way the relative
  Windows/Linux "dmods/" values are; doing so recreates the save dir inside
  itself.
- The game's save dir and log.txt on the Mac:
  `~/Library/Application Support/Dink Smallwood HD/`.
- History note: `.gitignore` used to ignore the whole `OSX` dir, which is why
  mac files kept going "missing" from the repo (e.g. MainMenu.xib in PR #23).
  Now only `OSX/build`, the generated xcworkspace, and stale local junk are
  ignored.
- The Cocoa window/view layer lives in the PROTON repo
  (`proton/shared/OSX/app`), not in RTDink. BuildMac.bat updates the mac's
  proton checkout with `git pull --ff-only` from GitHub, so proton changes
  must be committed AND pushed to SethRobinson/proton before a normal
  BuildMac.bat picks them up (RTDink changes are pushed directly by the
  script and don't need GitHub).
- Fullscreen gotcha (fixed July 2026, fix lives in proton
  `shared/OSX/app/MainController.mm`): `windowWillResize:` forces the window
  to 4:3, and AppKit also calls it during the native green-button fullscreen
  transition, which made the "fullscreen" window 4:3 (taller than the screen,
  game cropped top+bottom). It now skips the aspect forcing when the window
  is in or transitioning to/from fullscreen. Also `OSXToggleFullscreen()`
  (proton `shared/OSX/OSXUtils.mm`) used `[NSApp mainWindow]`, which is nil
  when the app isn't active (e.g. launched over ssh), so the toggle silently
  did nothing; it now falls back to keyWindow / first window.
- The Mac build accepts `-fullscreen` on the command line (forces fullscreen
  at startup regardless of the saved setting; `-window` still wins). Useful
  for testing fullscreen over ssh, e.g. launch the dev build with
  `-fullscreen -skip`, then verify the window rect equals the screen size
  with a small CGWindowListCopyWindowInfo helper (no TCC permissions needed;
  osascript/System Events and screencapture are both blocked over ssh).

## Releasing ("Build all three releases of the apps and upload them")

When Seth asks for this, build and upload the Windows, Mac, and Linux releases.
All three are hosted at `https://www.rtsoft.com/dink/<file>`; the upload
scripts use `%RT_PROJECTS%\UploadFileToRTsoftSSH.bat <file> dink` and honor
`NO_PAUSE=1`. README.md's download table links to these exact filenames, so
don't rename anything.

1. Run the smoke tests first (`script\TestWindows.bat` etc., see Testing
   above) so you don't ship a broken build.
2. **Windows**: build `Release GL x64` with MSBuild (command below), run
   `script\BuildAndPackageWindows.bat` (packages + signs + NSIS installer),
   then `script\UploadWindowsVersion.bat`
   (ships `DinkSmallwoodHDInstaller.exe`).
3. **Mac**: `script\BuildMac.bat` (no args: full signed + notarized build,
   takes a few extra minutes for Apple's notary service), then
   `script\UploadMacVersion.bat` (ships `DinkSmallwoodHD.dmg`).
4. **Linux**: `script\BuildFlatpak.bat` (no args builds both x86_64 and
   aarch64), then `script\UploadFlatpakVersion.bat` (ships both
   `DinkSmallwoodHD-<arch>.flatpak` bundles).

The README screenshots (`doc/images/screenshot_*.png`) are copies of
autotest output; refresh them from `script\testruns\windows\` after UI
changes.

### HTML5 / web version (`html5\`, verified October 2026)

- Builds with Emscripten 6.0.3 from `d:\pro\emsdk` (`EMSCRIPTEN_ROOT`, set by
  proton's `base_setup.bat`). Build: `html5\build_release.bat nopause`; then
  `html5\UploadToWebsite.bat` scp's to `rtsoft@rtsoft.com:www/web/dink/`
  (live at https://www.rtsoft.com/web/dink/). `BuildAndUpload.bat` chains both.
- For automation, use `UploadToWebsite.bat nobrowser` or
  `BuildAndUpload.bat nobrowser` (also skips the final pause). The scripts
  anchor paths to their own directory and stop on build/upload failures.
  Build cleanup uses Proton's `SafeRemove.ps1`; upload overwrites only the
  named build/loader files without deleting the live loader directory, then
  publishes the cache-busted HTML after the payloads and fixes permissions.
- October 8, 2026: fresh release built with Proton `f073700` and RTDink
  `ff45273`, deployed and hash-verified at the URL above. The Emscripten
  build succeeds with two existing `-Winvalid-pp-token` warnings from the
  JavaScript empty strings in Proton's `BaseApp.cpp` `EM_ASM` block; the
  older blanket warning-free HTML5 claim no longer applies. Local and live
  headless Edge verified the main menu and new game without JavaScript
  errors. Test artifacts belong in the
  ignored `script/testruns/` directory.
- `CustomMain4-3AspectRatioTemplate.html` (local, in `html5\`) is the
  hand-tweaked PWA/mobile page; sed generates `RTDink.html`/`index.html` from
  it, substituting the app name and an `RTBuildStamp` build stamp that
  cache-busts the js/wasm/data URLs. Edit the TEMPLATE, never the generated
  html, and don't switch back to proton's shared templates (the PWA/mobile
  tweaks would be lost). Same pattern as RTDscroll's July 2026 setup.
- `manifest.webmanifest`, the icon pngs, `.htaccess`, and `/web/arcade-mobile.js`
  live on the server only (mirrored in `d:\website\web\dink`); the upload
  script must never delete or overwrite them.
- Loader/file transfer (fixed October 8, 2026): keep the logo above the
  black canvas (no negative z-index) and dismiss the loader only in
  `onRuntimeInitialized`, never on plain download-status strings.
  `html5/DinkFileTransfer.js` restores the legacy loader's FileSaver and
  file-transfer helpers without redefining `Module` or booting the game
  twice. The template owns `#uploader`; imports write `/proton_temp.tmp`
  and send `MESSAGE_TYPE_HTML5_GOT_UPLOAD` (53) with the original filename.
  Preserve the local PWA/layout/cache-busting code. Do not include the
  complete legacy `RTLoader.js` (it also requests obsolete `.js.mem` data).
  `node tests/html5_loader.cjs` tests status transitions, cancelled/failed
  reads, import filenames/bytes, and download bytes/MIME without npm.
  Headless Edge checks cover desktop/mobile layout, an actual quicksave
  export/import round trip, and normal-slot byte transfer in an isolated
  browser profile. Menu clicks need a realistic down/up delay (about 150 ms)
  so the engine can register its file-picker click handler before mouseup.
  For HTML/JS-only releases, regenerate `RTDink.html` and `index.html` from
  the template using the existing binary build stamp, then run
  `UploadToWebsite.bat nobrowser htmlonly`; this uploads the helper and pages
  without recompiling or uploading the unchanged JS/WASM/data payloads.
- Stack size (fixed October 27, 2026): `build_release.bat` sets
  `-s STACK_SIZE=5MB`. Emscripten's default dropped to 64KB, and the DinkC
  interpreter's `run_script`/`process_line` recursion (~2.5KB of buffers per
  level) overflowed it on DMODs with nested procedure calls (Questlog
  Edition's quest log). Release builds don't check the stack, so the overflow
  silently corrupted static data and crashed later with an unrelated
  "RuntimeError: null function" (e.g. inside a `stringstream`). To diagnose
  crashes like that, build with `--profiling-funcs -sSTACK_OVERFLOW_CHECK=2`.
- Emscripten 6 port notes: needs `-s USE_SDL=1` (SDL 1.x shim no longer
  default), `-s INITIAL_MEMORY` (was TOTAL_MEMORY); `PRECISE_F32`,
  `--ignore-dynamic-linking`, `--memory-init-file` are gone. The ancient
  prebuilt `fmodstudioL_wasm.a` still links fine under 6.0.3.
- After a web deploy, copy the deployed files over `d:\website\web\dink\`
  (the local mirror of rtsoft.com) so the website repo can't clobber the game
  on its next site deploy; see the Feature Index in `d:\website\AGENTS.md`.

### AI-harness shell quirk (Claude Code sandbox on Windows)

The sandboxed shell sets `NoDefaultCurrentDirectoryInExePath=1`, so cmd does not
find `.bat`/`.exe` files in the current directory by bare name. This breaks the
`call setenv.bat` steps inside BuildAndPackageWindows.bat (installer then gets an
empty version string). When an AI session runs REAL builds (Seth wants real
builds, not sandbox-crippled ones), it must clear that variable first and run
without the sandbox, e.g. from PowerShell:

```
Remove-Item env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
cmd /c ".\BuildAndPackageWindows.bat < nul"
```

Normal interactive shells are unaffected.


## 3D remaster project (started November 2026)

This fork also hosts the planning and data pipeline for a free fan remaster of
the base game in Unreal Engine 5.8 (third-person, assets authored in Blender).

- Plan: `doc/remaster/REMASTER_PLAN.md`. Read it before any remaster work.
- Content bible (story, quests, bestiary, items, file formats):
  `doc/remaster/bible/README.md`, which also lists corrections to the reports.
- Reference images rendered from the original data: `doc/remaster/reference/`.
- Pipeline tools live under `tools/`. They read `bin/dink/` and must never
  modify `bin/` or `source/`. Generated output goes in each tool's `out/`
  directory, which is not tracked.
- The Unreal project lives IN this repo at `DinkRemasterUE/` (moved in from a
  sibling checkout on 8 Nov 2026; a symlink at `~/Repos/Dink-Smallwood/DinkRemasterUE`
  keeps the old path working). It has its own `AGENTS.md`; its binaries go
  through Git LFS (`DinkRemasterUE/.gitattributes`).
- Dev machine facts (5 Nov 2026): Arch-based Linux, Python 3.14 with numpy and
  Pillow, Blender 5.2 LTS, dotnet 10, cmake/clang, uv, node. No pytest
  (use stdlib `unittest`). git-lfs 3.8.1 is installed per-user through mise
  (`mise use -g git-lfs`; sudo needs a password, so pacman was not used) and
  `git lfs install --skip-repo` has set the global filters.
- The Git rules above apply to remaster work too: never commit or push unless
  told, and no AI co-author lines.
- `tools/dinkex` (built 5 Nov 2026) extracts all original data to JSON/PNG:
  `cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out`
  (about 7 s, 71 MB); tests: `python3 -m unittest discover -s tests` (38 pass).
  IDs: screens `SCR_nnn`, placements `Snnn_Pnn`, tiles `Snnn_Tnn`, where nnn is
  the screen number, not the map.dat record. Hardness PNG codes: 0 walkable,
  1 solid, 2 low, 3 other, 100 sprite hardbox, 200 warp trigger. Placement
  `hard` is inverted (0 = has hardness). `dink.ini` is read in two passes
  (all load_sequence lines first). Its schema is in `tools/dinkex/README.md`.
- `tools/data` (built 5 Nov 2026) holds the hand classification of every used
  tile (1,450 tile nums) and every placed sprite frame (559): `tile_classes.csv`
  and `sprite_classes.csv`. Both are generated: edit the label files in
  `tools/data/scripts/` and run `cd tools/data && python3 scripts/build_tables.py`;
  tests: `python3 -m unittest discover -s tests` (12 pass).
- Map facts found while classifying: tile source rects always use a 12-column
  grid even when the tileset bitmap is narrower than 600 px; tile hardness is
  drawn as outlines only (open water and forest canopy interiors have
  hardness 0, so reachability needs a flood fill plus the terrain class);
  active placements only use slots 1-96; 14 background placements carry
  scripts that never run; the upper storeys of the big town buildings are
  painted into tilesets ts34/35, not placed as sprites.
- `tools/dinkc` (built 5 Nov 2026, stdlib only) parses all 380 DinkC scripts to
  JSON ASTs plus tables (dialog_lines.csv, choices.json, facts.csv,
  script_kinds.csv, enemies/items/shops.json, calls.csv, diagnostics.json):
  `cd tools/dinkc && python3 -m dinkc build --scripts ../../bin/dink/story --map ../../bin/dink/map.dat --dat ../../bin/dink/dink.dat --out out`
  (under 1 s); tests: `python3 -m unittest discover -s tests` (40 pass).
- DinkC engine semantics worth knowing: one statement per line (the rest of
  the line is ignored); a procedure runs until the next `void` line; labels
  are file-wide; in `if (func() <op> x)` the operators `!=`, `<=`, `>=` act as
  `==` and `>`/`<` compare against 0; assignments need spaces around the
  operator; `sp_prop` is not a built-in; the engine prefers `.d` over `.c`
  (all 380 `.c` match their `.d`).
- inklecate 1.2.1 (official inkle release, the Ink compiler) is installed at
  `~/.local/share/inklecate/v1.2.1/` with a symlink in `~/.local/bin`:
  `inklecate -o out.json in.ink`.
- `tools/blender` (built 5 Nov 2026) is the Blender-to-Unreal asset pipeline:
  conventions in `tools/blender/CONVENTIONS.md`, scripts in `dinkasset/`
  (validate, fix, make_lods, export_ue, import_generated), run through
  `python3 dink.py <script> ...`. Self-test: `cd tools/blender && python3 run_tests.py`
  (16 tests, about 25 s, needs `blender` on PATH). Verified in Blender only;
  the items to confirm in the Unreal editor are listed in CONVENTIONS.md
  section 14. FBX export must use `FBX_SCALE_ALL` with `apply_unit_scale=True`
  (the default puts scale 100 on every node); a Blender round trip does not
  catch unit or axis mistakes, the byte-level FBX check in the tests does.
- Git remotes (set 5 Nov 2026): `origin` is the fork
  `cdavisv/Dink-Smallwood-Remaster` (master tracks origin/master); `upstream`
  is `SethRobinson/RTDink`, fetch-only (its push URL is set to DISABLED on
  purpose). `gh` is installed and authenticated as cdavisv; because of the
  `upstream` remote, `gh` must have `gh repo set-default
  cdavisv/Dink-Smallwood-Remaster` (set 9 Nov 2026) or it aims PRs at RTDink.
- Git LFS (checked 9 Nov 2026): a `git push` can succeed while its LFS upload
  silently does not; the commit lands on master and any fresh checkout then
  aborts on "object not found" (PR #31's 31 PhotorealTrousersV33 objects, and a
  vista asset before it). After pushing LFS content, and before switching a
  checkout to master, run `tools/lfs_audit.py [ref]` (asks GitHub's LFS batch
  API which objects it holds; `--fix` uploads any that are in the local store).
  Do NOT trust `git lfs fetch` as a check: it reports success for objects it
  already has locally. Recovering an object that is not local: find the file
  content (sha256 = the pointer's oid) in the committer's working copy, copy it
  to `.git/lfs/objects/<2>/<2>/<oid>`, then `git lfs push --object-id origin <oid>`.
- `tools/analyse` (built 5 Nov 2026) is pipeline stages 3 and 4: true
  connectivity, warp graph, interiors, regions and the 2D-to-3D world layout.
  `cd tools/analyse && python3 -m analyse build --ir ../dinkex/out --out out`
  (about 24 s); tests: `python3 -m unittest discover -s tests` (49 pass).
  It reads `tools/data/tile_classes.csv` and `tools/dinkc/out/calls.csv`.
  `tools/analyse/regions.toml` is the hand-tuned region and scale table: edit
  it and rebuild. World position of any original point is the bilinear blend
  of its screen's four corners in `out/world_layout.json` (u = map_x/600,
  v = y/400, map_x = placement x minus 20; metres, x east, y south).
  Base scale 0.025 m per original pixel; settlements x4, wilderness x2.75,
  dungeons x2.25, interiors x1.75. Component IDs `SCR_nnn#k`, interiors `INT_nnn`.
- Map connectivity facts from that analysis: Koka Isle joins the mainland by a
  walkable bridge (SCR_727 to SCR_759); Joppa is reached through a tunnel
  from a Windemere door (SCR_537) to SCR_483; the Darklands only by the
  `s6-warp` machine (SCR_253 to SCR_154); the Edge of the World plateau only
  by pits and caves; the snow isle only by the hole on SCR_144. The toll
  bridge is SCR_404 (base script `s1-brg`); the `s1-nopas` barrier is on
  SCR_346. East Wilds (cols 27-31, rows 8-20, 56 screens), checked 7 Nov 2026
  against the data and `dink.cpp`: no designed way in (no warp or script
  targets it except the booth door S289_P19; the river along cols 25/26, a
  channel at rows 11/12 and the cliff foot are closed outlines). The engine
  has two sequence-break routes, listed in `out/engine_reach.json`: push the
  rock S277_P03 (`s1-roc`, strength 4), walk the hardness-0 cliff face east to
  SCR_288, leave its right edge (the row wrap loads SCR_289, the booth's black
  void), take the booth door to SCR_350 (23 of the 56 screens); and wade
  through sea reached by screen-edge leaks (24 more; 9 stay closed). A cut
  must close the rock, the wrap and the leaks; a reconnection can use the
  booth door and the river at SCR_443/444.
- Unreal Engine 5.8.4 (Epic's prebuilt Linux build, CL 58902052) is installed
  at `~/UnrealEngine/UE_5.8.4` (73 GB) with Epic's Fab plugin for Linux
  unpacked into `Engine/Plugins/Fab`. The editor MCP plugins ship with it under
  `Engine/Plugins/Experimental/` (`ModelContextProtocol`, `ToolsetRegistry`,
  `Toolsets/AllToolsets`); the bundled toolchain is
  `Engine/Extras/ThirdPartyNotUE/SDKs/HostLinux/Linux_x64/v26_clang-20.1.8-rockylinux8`.
  Verified 5 Nov 2026: no missing shared libraries, and a headless editor run
  in a blank project executes Python and exits 0:
  `~/UnrealEngine/UE_5.8.4/Engine/Binaries/Linux/UnrealEditor-Cmd <abs path>.uproject -run=pythonscript -script=<abs path>.py -nullrhi -unattended -nosplash -nopause -stdout`
  (about 20 s; a minimal `.uproject` needs `"EngineAssociation": "5.8"` and the
  PythonScriptPlugin enabled). C++ compiles against this install (see below).
  NOT yet verified: the interactive editor on Hyprland/Wayland, the MCP
  server, Fab login, cooking and packaging. `-run=SmokeTest` without a project asserts on `GEditor`;
  that is the commandlet, not a broken install. With `-nullrhi` the log
  reports the integrated GPU; check the editor picks the Radeon RX 6800 when
  run with a display.
- `tools/dinkink` (built 5 Nov 2026, stdlib only) is pipeline stage 5: it
  converts the DinkC ASTs to Ink drafts. `cd tools/dinkink && python3 -m dinkink build --ast ../dinkc/out --out out`
  (about 7 s); tests: `python3 -m unittest discover -s tests` (39 pass, 12-27 s).
  Output: 377 `.ink` files plus root `dink.ink` (all compile with inklecate,
  0 errors, 0 warnings), `names.csv`, `line_ids.csv`, `director_commands.csv`,
  `director_vocabulary.csv`, 103 shot lists, `review_queue.csv` (65 items,
  11 high) and `coverage.csv` (all 380 scripts). Design in `tools/dinkink/DESIGN.md`.
  Runs in Unreal since 6 Nov 2026 (see the `DinkNarrative` entry below).
- Ink conversion conventions: script -> knot `d_<script>`, procedure entry
  `on_<proc>` with body `p_<proc>` called as a tunnel; globals are Ink
  variables (`&s2-nad` -> `s2_nad`, table in `names.csv`); script locals are
  `<script>__<name>`; director commands are output lines `>> name args #cmd #src:N`;
  spoken lines carry `#id`, `#say`, `#spk`, `#col`, `#src` tags. Engine bugs keep
  the engine's behaviour live and put the author's intent behind
  `CONST fix_<script>_l<line> = false`. Spoken text is verbatim: spaces Ink
  would collapse are written as U+00A0 and the display must turn them back
  into spaces. The fix-switch rule (all switches `false` by default): the
  engine's behaviour is live, the author's intent sits behind
  `fix_<script>_l<line>`, nothing is softened; a tag cannot be switched, so a
  wrong speaker or a stray character switches the whole line (`{ fix_..: intent
  - else: engine }`, same `#id` twice); a defect with no distinct intent (`goto
  mainloop` with no label) gets a review row but no constant. Argument lists
  follow `get_parms` (a short list gets zeros, a missing comma after a string
  cuts it short). Never-spoken lines have review category `never-spoken`.
- Ink gotchas found: knots, stitches and variables share one namespace; the
  comment stripper runs before escapes (`\//` is still a comment); empty
  conditional branches and tag-only lines are rejected; `inklecate -p` is
  quadratic on long output, so run it in chunks of about 200 lines.
- `DinkRemasterUE` (scaffolded 5 Nov 2026): C++ project `DinkRemaster` with
  plugins `DinkCore` (facts, world-state overrides, origin IDs, stats and the
  original combat maths, inventory, save), `DinkParity` (31 automation tests,
  `Dink.Core.*`), and empty shells `DinkNarrative`, `DinkImport`,
  `DinkExpanded`. `Scripts/build.sh` (about 28 s clean, seconds incremental)
  and `Scripts/test.sh` (about 15 s, 31/31 pass) both run headless and exit
  non-zero on failure.
- Unreal-on-this-machine facts: use `-ExecCmds="Automation RunTests <filter>; Quit"`
  (`-TestExit` always exits 1 on Linux); unset `WAYLAND_DISPLAY` and `DISPLAY`
  for headless runs or every frame logs a warning; the AndroidFileServer
  plugin must stay disabled or the editor writes a security token into
  `Config/DefaultEngine.ini`; do NOT run `GenerateProjectFiles.sh` (it writes
  about 6,000 files into the engine tree; the build does not need it); the
  build tool caches under `Engine/Saved/UnrealBuildTool` and listens on port
  1345 while building.
- Greybox import (stage 6, built 6 Nov 2026) lives in `DinkRemasterUE`:
  `Scripts/export_import_bundle.py` gathers the `tools/*/out/` data into
  `ImportData/`, and `Scripts/import_greybox.sh --region stonebrook|all` runs
  the `DinkImportGreybox` commandlet headless (whole world in about 45 s;
  re-runs are no-ops with zero drift). Result: maps `L_Greybox_Stonebrook`
  and `L_Greybox_World` under `Content/Dink/_Generated/` (git-ignored,
  regenerable, 175 MB): 643 screens, all 5,846 placements, 116 warps, and a
  third-person test character. 41 automation tests pass. NOT yet seen by
  anyone: headless image capture does not draw on this machine, so scale,
  readability and performance still need a person at the editor.
- Facts found by the importer: a new game starts on SCR_001 at map pixel
  (314, 161) facing west, and SCR_001 is Dink's house in its normal state
  (the burning and burnt versions are its vision 1 and 2). The 20 `screenlock`
  scripts run on 35 screens. Pipeline-data defects found by the importer, fixed
  in `tools/analyse` on 7 Nov 2026 (the exporter's workarounds can go): no two
  screens overlap in `world_layout.json` (unreached SCR_298/299 are parked on the
  `fragments` sheet with a `displaced` flag; a reached overlap stops the build);
  script warps are `cutscene` when `main`, `die` or a combat procedure starts
  them (`SW_s2-cave2_L154`, `s1-ltr`, `s2-bar`, `en-gmog`), with `triggers`
  and `player_triggered`; every warp has `dst_in_bounds` and `dst_engine`
  (`SW_s2-culg_L42` is off-map by design: `dink_can_walk_off_screen(1)` and the
  script walks Dink in); `vision_variants.json` searches spawned scripts too and
  lists `never_set`: 16 screens (17 values) have vision-gated placements that no
  script sets, so the shipped game never draws them; SCR_001 is "Dink's house"
  with `vision_states` in `regions.csv`.
- Dialogue runtime (built 6 Nov 2026) is `DinkRemasterUE/Plugins/DinkNarrative`:
  the compiled story (`tools/dinkink/out/json/dink.json`) runs on Inkpot's C++
  Ink runtime (`Plugins/Inkpot`, trimmed to the `InkPlusPlus` module, commit
  34a2e9e, MIT), one Ink flow per script instance, with `DinkCore`'s fact store
  as the single source of truth for variables. A director executes the
  `>> command` lines: of 134 vocabulary rows 82 are implemented and 52 are
  recorded for later layers (table in `Plugins/DinkNarrative/Docs/director_status.csv`).
  `Scripts/sync_story.py [--rebuild]` copies the story into
  `Content/Dink/Data/Story/` (last synced 7 Nov 2026 after the seven verbatim-review
  converter rules: 377 knots, 930 entry points, 16 fix switches all false).
  Smoke run of all 597 entry points: 571 complete, 26 are the original's
  endless idle loops, 0 runtime errors (`Saved/Narrative/smoke_report.txt`).
  Entering a screen now runs its scripts' `main`, so a new game opens with
  the mother's scene. Console: `dink.Run <script> <proc>`, `dink.Say`,
  `dink.Fact <name> [value]`, `dink.Choose`, `dink.Skip`, `dink.Story`,
  `dink.SmokeRun`; talk key is E.
- Gameplay layer (built 6 Nov 2026): `DinkGameplay.*` in `DinkNarrative`
  fires `hit`, `touch`, `push`, `talk`, `die` and the item procedures by the
  original engine's rules (line references to `dink.cpp` are in the project
  `AGENTS.md`), with drops, pickups, respawn, level-up and death. The
  converter now converts every script that has an executable statement
  (377 `.ink` files, 930 entry points, 25 converter tests); `random()` is an
  external with a seedable stand-in for C `rand()`. Only `ranstuff` is
  absent (the original has no such script). Smoke run: 930 entry points, 903 complete, 27 idle
  loops, 0 errors. Keys: F attack, Q cast, E talk; `dink.Arm <slot>`,
  `dink.ArmMagic`, `dink.Inventory`.
- Brains and fights (built 6 Nov 2026): `DinkBrains.cpp` in `DinkNarrative`
  ports every brain the shipped data uses from `dink.cpp` (0, 2, 3 duck,
  4 pig, 5/7, 6, 9 monster, 10 dragon, 11/17 missile, 12, 15, 16 people;
  line references in the project `AGENTS.md`), thinking on the original's
  60 Hz frame in screen pixels against per-screen hardness
  (`Content/Dink/Data/Gameplay/Hardness/SCR_nnn.txt`). Monster attacks hurt
  Dink by the original formula; missiles stop at walls. `screenlock` holds
  Dink on the screen (grey placeholder barriers in the greybox) until the
  script unlocks it; warps still work while locked, as in the original, and
  the Bonca cave of Martridge's trial (`s1-cavem`) is NOT a locked fight.
  A switchable 3D layer (`Content/Dink/Data/AI/adaptation.ini`: 450 ms
  wind-up, at most 2 attackers) is on for play and off in parity tests.
  Brains are plain C++ (`ThinkSprite`), not State Tree assets, so they run
  headless; a State Tree task can call them later. Director status: 146
  rows, 111 implemented, 35 recorded. 176 automation tests (verified 9 Nov
  2026: 176/176 in 723 s; the probe runs as twenty save-slot chapters,
  Ch1..Ch9 and ChA..ChK, deterministic across runs and identical packaged for all
  twenty (9 Nov 2026); PIE tests run on a fixed 60 Hz step).
- Stonebrook probe (`Dink.Gameplay.Probe.Stonebrook`, report in
  `DinkRemasterUE/Saved/Narrative/stonebrook_probe.txt`, every event in
  `stonebrook_probe_trace.txt`): a scripted play-through from a new game with
  real interactions plays Martridge's trial, pays the toll (`&story` 7),
  kills Jack with seven fireballs, picks up three magic potions (SCR_273,
  597, 352: `&magic` 5), learns Acid Rain, frees the prisoner and plays the
  cult ambush: 47 of 47 steps, 238 s of game time, about 50 s wall. Fixed
  (7 Nov 2026): the old flakiness was frame timing (real-time stepping drew
  the shared `rand()` stream in a different order each run); the editor now
  runs a fixed 60 Hz step in PIE tests and the probe is deterministic (trace
  md5 `23da76f5dc`, 5,127 events, identical in 8 verified runs). The
  "stuck wait" was a snapshot artifact of a timeout that was a whole number
  of casts. Real bug found and fixed: script instances kept the screen they
  were created on, so a spell armed on one screen did not fly on another.
  The run ends where the probe ends (next scene SCR_625), not where the game
  refuses; the route onward is `Plugins/DinkParity/Docs/probe_route.md`.
- Placeholder or missing: no animation (cards slide), no corpses, debug
  sphere for the attack telegraph, no inventory screen or escape menu; the
  dragon and Seth are untested; scripted `move`/`move_stop` ignore hardness.
  NOT yet seen on a display: text, menu, fade, keys, and how fights feel in
  3D; the packaged game has only run headless (`-nullrhi`, no window, no
  input). Move speed (60 px/s per
  `sp_speed` point), the 600 ms fade and the 3.5 m talk range are guesses.
- Audio generation: since 6 Nov 2026 the owner has ElevenLabs connectors
  available to agents and wants them used for the new sound effects, music
  and voice. The workspace can run sound effects (`eleven_text_to_sound_v2`,
  0.5-30 s, loopable), music (`eleven_music_v2_5`, up to 600 s), speech
  (`eleven_v4`) and voice design. Every generated file must go in the asset
  ledger (`DinkRemasterUE/SourceAssets/asset_ledger.csv`) with tool, model
  and licence; the owner explicitly confirmed public redistribution rights on7Nov2026; see
  `DinkRemasterUE/SourceAssets/Audio/REDISTRIBUTION.md`.
- Sound effects (generated 6 Nov 2026): the scripts load 48 distinct effects
  (`start.c`, slots 1-49; slot 25 repeats CAVEENT), not 58. Two candidates
  (`a`, `b`) per effect are in `DinkRemasterUE/SourceAssets/Audio/SFX/`:
  `delivered/<slot>_<cue>_<a|b>.mp3` as returned (128 kbps) and engine-ready
  WAVs (44.1 kHz, 16-bit, mono; loops 23 and 34 stereo; peak -3 dBFS) rebuilt
  by `SourceAssets/Audio/tools/prepare_sfx.py`. ElevenLabs flow id
  `5qYnooqvYY0wzSgUxf2K`. NOT yet chosen by ear, NOT imported into Unreal;
  the director's audio is still a stub that logs cue names. 29 of 96 files
  have clipped samples in the source (`quality_report.csv`); the worst are
  both takes of 29 hurt1 and 31 attack1. Seven files in `bin/dink/sound`
  (click, pop, intro, ocean1, high1, bird2, sword2_item) are not loaded by
  the scripts and were not regenerated.
- Music drafts (generated 7 Nov 2026, owner approved the spend): 28 original
  instrumental cues, one take each, in `DinkRemasterUE/SourceAssets/Audio/Music/`
  (`delivered/<nn>_<cue>.mp3` as returned, 48 kHz ~194 kbps; engine-ready
  stereo WAVs beside them; `README.md` there is the cue map: which `playmidi`
  names and `dink.dat` music values each cue replaces). ElevenLabs
  `eleven_music_v2_5`, flow `M1M41vE6pzKeEkQYmpi5`, 23,200 credits in total
  (about 900 credits per minute; the connector's pre-run estimate overstates
  the charge by about 1.8x). Prompts describe mood and instruments only,
  never existing music. Current status: the owner selected all28music cues, which are
  imported alongside44selectedSFX. Public redistribution rights are owner-confirmed;
  voice candidates remain separate. See the Unreal audio README and verification receipts.
  The 19 loop cues have technically seamless derived loops in
  `Audio/Music/loops/` (beat-aligned cut plus a 1 s equal-power crossfade,
  `prepare_music.py --loops-only`, `loop_report.csv`); musical continuity
  at the seam is still unchecked by ear (weakest: 02, 05, 09, 10, 18-21).
- Probe progress (7 Nov 2026): the bot plays route steps 1-12, the roads and the
  Mayor's errand, a gold loop (the Bong/Boncd pairs of SCR_583/480/632 kill each
  other and still drop loot; 724 -> 1072 gold), the bow (step 15), arms it, the
  goblin gate (step 20) and one goblin of SCR_680 (step 21). It stops at the other
  three goblins: a 600x100 px corridor where the two `s3-gs` cannot be kited and a
  fireball does 4-8; needs a longsword melee tactic or elixirs (the healer loops
  on "You don't have enough gold.", s2-healp.c:135-139). Engine fix found on the
  way: an expiring text no longer deletes the sprite that reused its handle
  (dink.cpp keeps a kill timer per slot). Six chapters, hashes in the UE AGENTS.md.
  Chapter 6 later gained the Terris healer (s2-healp, 1 gold per missing life),
  so it is three steps.
- Probe progress, later on 7 Nov 2026: a `DuelFight` tactic (reach-box dance
  with healer trips) beat the other three goblins and Mog (`spawn` verified);
  the Cast camp scene ran (scripted walk over SCR_489's edge, `fade_up`
  verified). Engine fix: `sp_script` now runs the attached script's `main` on
  the spot (`dink.cpp:8155-8175`; `no_running_main` mirrored for a screen's
  first base-script run; test `Dink.Narrative.Director.SpScriptRunsMainAtOnce`),
  which gives the knights their 40 hp; `SquadFight` beats them (their blows
  hit each other), then the Mayor, the parade (`&story 10`), Pete's bomb, the
  all-stat chests and the cracked rock. The probe now stops at route step 31,
  the 27 ducks of Windemere: `external` and `spawn` have the same deferred
  start as `sp_script` had (`dink.cpp:11326-11360`, `8181-8203`), so the last
  `duckdie` is removed before `external("make","foodduck")` runs and
  `spawn("s4-end")` never fires (UE AGENTS.md pitfall 56; next fix). Nine
  chapters, hashes in the UE AGENTS.md, packaged md5s identical to PIE.
- Probe progress, 8 Nov 2026: second engine fix, `external` and `spawn` run
  their child script on the spot (`dink.cpp:11326-11360`, `8181-8203`; test
  `Dink.Narrative.Director.ExternalAndSpawnRunAtOnce`), so the 27th duck's
  `duckdie` reaches `spawn("s4-end")`: `&s4-duck 2`, `&story 11`, the Kelly
  and guard scene. Chapter 10 (`ChAJoppa`): the Windemere healer, the three
  pickups of step 32, Joppa, the basement (`&s5-jop 2`), the return with the
  family and both dragons. Stops at route step 36, the dragons: a punch makes
  a dragon cast `harm` for 16 at once and Dink (strength 13: this run put its
  level-ups into defense) is dead in 1.4 s; the route's kit needs strength
  20+, i.e. level-ups into strength from chapter 7 on and the longsword
  (400 gold; Dink has 205), which re-tunes chapters 7-10. Ten chapters,
  packaged md5s identical to PIE; hashes in the UE AGENTS.md.
- Probe progress, 8 Nov 2026 (kit): the level-4 menu now answers "Increase
  Attack" (only Ch8 had chosen Defense); chapter 11 earns 508 gold with three
  feud rounds, buys Pete's longsword and three elixirs; Dink reaches the
  dragons with strength 20 (sword), defense 5, life 29 and wins in 9.4 s with
  the family alive (`DuelFight` with `bCaster`, an elixir drunk when one more
  `harm` would kill him; not robust: one more cast on Gwen loses it). Then the
  castle gate and the King (`&story 14`), the castle potions, the Edge pit and
  the ancients' machine, the Darklands rooms, Milder, and Seth appears:
  eighteen chapters, stop at route step 53, Seth (300 hp: a sword hit nets
  about 0.4; needs the bow with bow lore, 1500 gold, and a hold-the-key bow
  action that does not exist yet). Hashes in the UE AGENTS.md; packaged md5s
  identical to PIE for all eighteen.
- Probe progress, 9 Nov 2026 (PR #35): the bow built from `dink.cpp` in
  `UDinkGameplay` (`activate_bow`, the charge while the attack key is held: 7
  power per 60 Hz frame after the first status tick, 500 is a full draw;
  release fires an arrow of strength `(power/100) * max(1, strength/5)` with the
  engine's missile damage; bow lore is `item-b1.c`'s one-in-three power shot,
  x3), a `PlayerAttackPress/Release` API the input layer can bind to later.
  Two parity fixes with citations and tests: `load_screen` into a warp trigger
  no longer warps Dink back (`dink.cpp:15337`), and `init("load_sequence_now")`
  gives a sequence `dink.ini` lacks its hardbox (`dink.cpp:2335-2344`,
  `1899-1922`: Seth's bomb pose, which arrows passed through). Chapter 19
  (`ChJBowLore`, 37 steps): six strength potions of the Edge, the Darklands
  rooms again for gold, bow lore (1500), eleven elixirs, the bow armed
  (strength 26, defense 9, magic 12, lifemax 65). Chapter 20 (`ChKSeth`, 5
  steps): Seth (300 hp, defense 25) dies to 51 arrows in 139 s, Dink drinks all
  eleven elixirs (not robust: the last one is gone when he dies), the machine,
  the King: **`&story 16`, the end of the game**. Chapters 1-18 keep their
  hashes; ch19 579f75b840, ch20 eae2c35f54. 176/176 tests. Packaged run from
  master 8175f75 the same day: all twenty chapters PARITY OK, so the alpha
  gate's first condition (bot completes &story 0-16 on a packaged build) holds;
  condition three (no original audio) is met; condition two (every origin ID
  final/placeholder/cut) is audited by `DinkRemasterUE/Scripts/art_coverage.py`
  (9 Nov 2026: 143 final, all in Stonebrook on screens 1/407/438/439/471;
  6,459 placeholder; 5 cut; art binds by origin ID or screen only, never by
  sprite family, so delivered pillbug/duck sources dress one screen each;
  101 placeholders can never be final: hardness proxies, never-set vision
  variants, empty placements; report in `Plugins/DinkImport/Docs/art_coverage.md`). Remaster gap noted:
  `draw_hard_sprite`/`sp_hard` are only recorded (UE AGENTS.md pitfall 77).
- Packaged build (first cook 7 Nov 2026): the probe moved into a new
  `DeveloperTool` module `DinkProbe` (same plugin; `DinkParity` is now `Editor`
  type, the uproject allow-list is gone), so it exists in a game target.
  `Scripts/package.sh` cooks and packages Linux Development (22 s cook from
  empty, 1.5 GB staged, pak 575 MB, `Dink/Data` staged as UFS);
  `Scripts/run_packaged_tests.sh` runs each chapter in its own packaged game
  process (`-nullrhi`, fixed 60 Hz) and compares trace md5s with the editor's:
  every chapter matches PIE (7 Nov: six chapters; re-verified 8 Nov 2026
  evening with all eighteen chapters after the `sp_script`/`external`/`spawn`
  parity fixes moved the early hashes: Ch1 b3760d52d7 ... Ch18 e4355a5505, the
  table is in `packaged_probe.md`; 12 s cook of 5,198 packages, 55 s for
  package.sh, 1.5 GB staged), repeatably after a clean cook. Three plumbing fixes were needed for parity: FName display case does
  not survive cooking (event texts lower-cased), the automation controller
  delays tests by 300 frames in a game (`; Now;` in the exec), and the game
  ticks the story and greybox subsystems in the reverse order from PIE
  (`-DinkProbeHold` pauses the world until the probe starts). Details and
  pitfalls 47-52 in the UE AGENTS.md and `packaged_probe.md`. Only
  `L_Greybox_World` is cooked; Windows and Shipping were not attempted.
- Voice lines (started 7 Nov 2026): `DinkRemasterUE/SourceAssets/Audio/Voice/`
  (README there has the full state). The 1997 lines, verbatim, tagged in the Ink
  data with speaker expressions (`spk:1` Dink, `current_sprite`, script sprite
  variables): 2,125 unique lines, 68,486 characters, mapped to 29 voice
  archetypes (`voice_cast.csv`, `voices.csv`, `voice_lines.csv` with a
  `tts_text` column that turns `<shiver>`-style stage directions into ElevenLabs
  v4 tags; system lines such as gold pickups are never voiced). Voices are
  designed from text (`eleven_ttv_v3`), never cloned, chosen by the owner from
  three previews and saved in the owner's ElevenLabs library
  (`voices_saved.csv`, `voice_designs.json`): 26 designed voices plus three
  owner-approved stand-ins (girl = young woman, goblin = Mog, dragon = monster;
  the service refuses to design a child voice and refused the goblins'
  gibberish round, and the dragons have only 46 characters of lines).
  Generated with `eleven_v4` at 1 credit per character, one take per line, one
  flow per voice, files named `<voice>/<line id>.mp3`, every line ledgered
  `candidate` with generation id, flow, credits, sha256 and duration
  (manifests `pilot_dink`, `dink_batch_01..04`, `cast_batch_01..07`). Complete on
  9 Nov 2026: 2,088 voice lines, 65,562 credits (82 of them copies of an identical
  text already generated for the same voice), all `candidate`; every speaking
  part has a voice. The only unvoiced lines are the four that are nothing but a
  stage direction (`[chortles]`, `[sniffs]`, `[sobs]`, `[groans]`: the service
  needs words) and the 33 system lines. The account's DAILY generation limit
  (HTTP 429) stopped the batches twice on 8 Nov after about 36,000 credits a day.
  Audio quality has not been listened through; the takes are review candidates.
  `SourceAssets/Audio/REDISTRIBUTION.md` (7 Nov 2026) records the owner's
  confirmation of redistribution rights for the generated audio. Import into
  the game is the audio pipeline's job (Codex's `import_approved_audio.py`);
  nothing is wired to play the lines yet.
- Probe route (written 7 Nov 2026, script-verified):
  `DinkRemasterUE/Plugins/DinkParity/Docs/probe_route.md`, 56 steps from
  &story 7 to 16 with `file.c:line` for every fact (the &story setters:
  s1-brg2.c:47, s2-culg.c:79, s3-1st.c:93, s3-tc.c:285, s4-end.c:7,
  s5-end.c:36, king.c:134, king.c:189, s7-boss.c:304, king.c:102; spot-checked).
  Findings that shape the alpha bot: only ~3,700 exp lies on the path
  (level 5), so every locked fight must be won by kiting or ranged play, the
  Joppa dragons need the 400-gold longsword, and Seth (300 hp, defense 25,
  s7-boss.c:22-23) is unbeatable at natural stats: the bow kit needs about
  6,500 gold and 25,500 exp (about 30 sweeps of the four slayers on SCR_157).
  Plan: run the bot to step 51 unattended and treat the Seth fight as its own
  long test. Jack is optional (nothing later reads &s2-aunt == 4). The route
  skips probe steps 38-41, Koka Isle, the snow castle and Hellfire.
  Kiting geometry, bomb self-damage and the cadence model are unverified.
- Verbatim review pre-check (7 Nov 2026): `doc/remaster/verbatim_review.md`
  classes all 66 `review_queue.csv` items: 49 already correct, 3 converter
  bugs (R0015/R0016: the intent branch of `freeeze`/`unfreeeze` must emit the
  corrected command; R0044: `s3-chick.c:42` has no comma before
  `&current_sprite`, so `get_parms` returns early (dink.cpp 4206-4225) and the
  1997 game never spoke the line; DESIGN.md says the opposite and must be
  corrected), 12 author-intent switches (4 lacked their `fix_` CONST: R0001,
  R0002 for the mistyped `{` at `s1-h3-8.c:13`, R0004, R0035; the five
  `goto mainloop` constants R0007-R0011 were empty), and 2 owner
  decisions (whether to give the non-existent `sp_prop` a meaning; whether to
  ship with every `fix_` switch false, which leaves three written lines silent
  as in 1997). The converter now does rules C1-C7 of that review (new
  constants `fix_s2_man2_l25`, `fix_s1_h3_8_l13`, `fix_s1_wand2_l187`,
  `fix_s3_chick_l42`; the five empty ones are gone; `freeeze`/`unfreeeze` emit
  `freeze`/`unfreeze`; `sp_prop` is still a no-op and every switch false, so
  OD1 and OD2 stay open). Review-queue IDs were renumbered by that change, so
  the R-numbers in `verbatim_review.md` are the pre-fix ones (match by
  script and line). `DinkRemasterUE` has not been synced with the new story.
