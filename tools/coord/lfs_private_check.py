#!/usr/bin/env python3
"""Private-path check of every file a branch adds or changes, in EVERY commit, LFS files read for real.

    tools/coord/lfs_private_check.sh <branch-ref> [<base-ref>]      (base default origin/master)

Each LFS file is fetched and smudged (GIT_LFS_SKIP_SMUDGE is removed from the environment: with it set, `git lfs
smudge` hands back the pointer and an older version of this check said "0 hits" on three branches that held a home
path, 23 Nov 2026). zstd-compressed files (.blend) are decompressed too, UTF-16 strings are read with their zero bytes
dropped, and a file that is still a pointer after the smudge is UNREAD and fails the check.

A hit is a personal home path (/home/<name>, /Users/<name>, C:\\Users\\<name>, with the neutral names of
Scripts/check_public_paths.py allowed), or any extra word given in DINK_PRIVATE_PATTERNS (comma-separated, e.g. the
machine's login name: the local wrapper adds `id -un` unless DINK_PRIVATE_NO_LOGIN=1). Exit code = hits + unread.
Last line: "lfs files checked: N, private hits: H".
"""
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Scripts'))
from check_public_paths import PATTERN, NEUTRAL_USERS  # noqa: E402

POINTER = b'git-lfs.github.com/spec'
ENV = {k: v for k, v in os.environ.items() if k != 'GIT_LFS_SKIP_SMUDGE'}


def git(*args, data=None, check=True):
    return subprocess.run(['git', *args], cwd=ROOT, env=ENV, input=data, capture_output=True, check=check).stdout


def extra_patterns():
    words = [w.strip() for w in os.environ.get('DINK_PRIVATE_PATTERNS', '').split(',') if w.strip()]
    return [re.compile(re.escape(w).encode(), re.IGNORECASE) for w in words]


def hits(data, extras):
    views = [data, data.replace(b'\0', b'')]
    if data[:4] == b'\x28\xb5\x2f\xfd':  # zstd frame (Blender's compressed .blend)
        out = subprocess.run(['zstd', '-dc'], input=data, capture_output=True).stdout
        if out:
            views += [out, out.replace(b'\0', b'')]
    found = set()
    for view in views:
        text = view.decode('latin-1')
        for m in PATTERN.finditer(text):
            if re.split(r'[\\/]+', m[0])[-1].lower() not in NEUTRAL_USERS:
                found.add(m[0])
        for x in extras:
            if x.search(view):
                found.add(x.pattern.decode())
    return sorted(found)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ref = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else 'origin/master'
    extras = extra_patterns()
    # No bulk `git lfs fetch` of the ref (it would download every LFS object of the whole tree): `git lfs smudge` below
    # downloads each changed file's object on demand, so only the branch's own LFS files are read.
    commits = git('rev-list', f'{base}..{ref}').decode().split()
    n = bad = unread = 0
    for c in commits:
        names = git('diff-tree', '--no-commit-id', '--name-only', '--diff-filter=AM', '-r', '-z', c).decode().split('\0')
        for f in filter(None, names):
            blob = git('cat-file', '-p', f'{c}:{f}', check=False)
            if POINTER in blob[:200]:
                n += 1
                real = git('lfs', 'smudge', '--', f, data=blob, check=False)
                if POINTER in real[:200]:
                    print(f'UNREAD (still a pointer) {c[:10]} {f}')
                    unread += 1
                    continue
                kind = 'PRIVATE'
            else:
                real, kind = blob, 'PRIVATE(text)'
            h = hits(real, extras)
            if h:
                print(f'{kind} in {c[:10]} {f}: {", ".join(h)[:200]}')
                bad += 1
    if unread:
        print(f'unread LFS files: {unread} (check NOT valid)')
    print(f'lfs files checked: {n}, private hits: {bad + unread}')
    return min(bad + unread, 125)


if __name__ == '__main__':
    raise SystemExit(main())
