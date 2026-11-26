#!/usr/bin/env bash
# usage: tools/coord/lfs_private_check.sh <branch-ref> [<base-ref>]
# Every LFS/binary/text file the branch adds or changes against <base-ref> (default origin/master), in EVERY commit, is
# fetched, smudged for real and searched for a personal home path; locally the login name is searched too. See
# lfs_private_check.py. Run it on origin/<branch> AFTER the push, with GIT_LFS_SKIP_SMUDGE unset (this script unsets it).
unset GIT_LFS_SKIP_SMUDGE
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "${DINK_PRIVATE_NO_LOGIN:-0}" != 1 ] && [ -z "${CI:-}" ]; then
  DINK_PRIVATE_PATTERNS="${DINK_PRIVATE_PATTERNS:+$DINK_PRIVATE_PATTERNS,}$(id -un)"; export DINK_PRIVATE_PATTERNS
fi
exec python3 -I "$HERE/lfs_private_check.py" "$@"
