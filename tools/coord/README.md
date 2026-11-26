# Coordinator tools (`tools/coord/`)

Shell tools the remaster's coordinator sessions use on the shared machine. They hold no machine paths: the repository
is found from the script's own place, temporary worktrees go under `${TMPDIR:-/tmp}`, the GitHub repository comes from
`gh repo view` (or `DINK_REPO`).

| Script | What it does |
|---|---|
| `unreal_turn.sh <command...>` | Runs ONE Unreal step (build, import, test run, capture, package) when it is its turn: two lanes, a GPU lock, a kernel-Oops guard, exclusive packaged runs. `--status` prints the queue, the locks and the counted processes. The copy every agent calls is `DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh` (git-ignored); install a new version with `install_unreal_turn.sh`, which replaces it by rename (never edit the installed file in place: bash reads a running script as it goes). |
| `merge_pr2.sh <pr>` | Merges a PR only when it is mergeable (an AGENTS.md-only conflict is merged away by `merge_master_docs.sh`), the CI `source-audit` passed (or the PR is docs-only, see below), the CI `lfs-private-check` passed or did not run, no commit has an attribution line, and `lfs_private_check.sh origin/<branch>` finds 0 hits. Says "merged" only when GitHub reports state MERGED. |
| `merge_master_docs.sh <branch>` | Merges origin/master into the branch when the only conflict is `DinkRemasterUE/AGENTS.md` (both sides kept), pushes without force; any other conflict aborts (exit 3). |
| `lfs_private_check.sh <ref> [<base>]` | Reads every file the branch adds or changes in every commit since `<base>` (default origin/master), LFS content downloaded and smudged for real (`GIT_LFS_SKIP_SMUDGE` is unset), zstd `.blend` files decompressed, UTF-16 strings read, and fails on a personal home path (the patterns of `Scripts/check_public_paths.py`) or, locally, the login name. A file still a pointer after the smudge is UNREAD and fails. |

## Docs-only PRs and the source-audit check

`.github/workflows/unreal-source-audit.yml` runs only for PRs that touch its trigger paths (`DinkRemasterUE/**`, `tools/coord/**`,
`Scripts/check_public_paths.py`, the workflow and its fixture list). `merge_pr2.sh` reads the PR's file list from
GitHub: when no file is under those paths and every file is a `*.md`, the missing check counts as a pass; a PR without
the check that is not docs-only is not merged.

## CI

`.github/workflows/lfs-private-check.yml` runs `lfs_private_check.sh <head sha> <base sha>` on every non-draft PR
(drafts are skipped to save LFS bandwidth; only the PR's own LFS files are downloaded). An optional repository secret
`DINK_PRIVATE_PATTERNS` adds comma-separated words to search for.

## Rules these tools encode (learned on the shared machine)

- Run the private check on `origin/<branch>` AFTER the push, with real LFS content: a skip-smudge worktree holds
  pointers, and a scrub of pointers says "clean" without reading anything.
- A script that reports "merged" must ask GitHub for the PR's state.
- Never kill by pattern; stop only PIDs you started.
