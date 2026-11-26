#!/usr/bin/env bash
# usage: tools/coord/merge_master_docs.sh <branch>
# Merges origin/master into the PR branch when the ONLY conflict is DinkRemasterUE/AGENTS.md (both sides' sections are
# kept), then pushes (no force). Any other conflict aborts with exit 3 and leaves the branch untouched.
# Works in a throwaway worktree under ${TMPDIR:-/tmp} with GIT_LFS_SKIP_SMUDGE=1 (nothing is downloaded); commits with the
# repository's own git identity (DINK_GIT_NAME / DINK_GIT_EMAIL override it). No hooks run, no attribution lines are added.
set -euo pipefail
B=${1:?usage: merge_master_docs.sh <branch>}
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$(git -C "$HERE" rev-parse --show-toplevel)"
W="$(mktemp -d "${TMPDIR:-/tmp}/mm_XXXXXX")"
TMPB="mm_tmp_$$"
cleanup(){ cd "$R"; git worktree remove --force "$W" 2>/dev/null || true; rm -rf "$W"; git branch -D "$TMPB" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cd "$R"; git fetch -q origin
rmdir "$W"
GIT_LFS_SKIP_SMUDGE=1 git worktree add -q -b "$TMPB" "$W" "origin/$B"
cd "$W"
export GIT_LFS_SKIP_SMUDGE=1
[ -n "${DINK_GIT_NAME:-}" ] && export GIT_AUTHOR_NAME="$DINK_GIT_NAME" GIT_COMMITTER_NAME="$DINK_GIT_NAME"
[ -n "${DINK_GIT_EMAIL:-}" ] && export GIT_AUTHOR_EMAIL="$DINK_GIT_EMAIL" GIT_COMMITTER_EMAIL="$DINK_GIT_EMAIL"
if git -c core.hooksPath=/dev/null merge --no-ff --no-commit origin/master >/dev/null 2>&1; then
  echo "clean merge"
else
  C=$(git diff --name-only --diff-filter=U); echo "conflicts: $C"
  for f in $C; do
    case "$f" in
      DinkRemasterUE/AGENTS.md)
        python3 -I - "$f" <<'PY'
import sys
p = sys.argv[1]
lines = open(p, encoding='utf-8').read().split('\n')
keep = [l for l in lines if not (l.startswith('<<<<<<< ') or l.startswith('>>>>>>> ') or l == '=======' or l.startswith('||||||| '))]
open(p, 'w', encoding='utf-8').write('\n'.join(keep))
PY
        git add "$f";;
      *) echo "NON-DOC CONFLICT in $f: abort"; git merge --abort; exit 3;;
    esac
  done
fi
left=$(grep -c -E '^(<<<<<<<|>>>>>>>)' DinkRemasterUE/AGENTS.md || true)
[ "$left" = 0 ] || { echo "conflict markers left in AGENTS.md: abort"; git merge --abort; exit 3; }
git -c core.hooksPath=/dev/null commit -q -m "Merge master into $B (AGENTS.md sections of both kept)"
git push -q origin "HEAD:$B" && echo "pushed $(git log --format=%h -1) to $B"
