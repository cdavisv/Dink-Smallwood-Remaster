#!/usr/bin/env python3
"""Reject user-specific home paths in public text; --fix normalizes historical receipts.

Uses the Git inventory, so ignored local builds and credentials are never read.
Binary authoring files need their own format-aware metadata review.
"""
import argparse
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Split the prefixes so this checker does not flag its own source.
PATTERN = re.compile(r'(?<![A-Za-z0-9_])/(?:@?ho' + r'me|Us' + r'ers)/[A-Za-z0-9_.-]+|[A-Za-z]:[\\/]+Us' + r'ers[\\/]+[A-Za-z0-9_.-]+')

IDENTITY_PATTERN = re.compile(r'((?:LoginId|MachineId|EpicAccountId)\s*[=:]\s*)([A-Fa-f0-9-]{16,})', re.IGNORECASE)

NEUTRAL_USERS = {'artist', 'user', 'username', 'runner', 'name', 'you', 'me', 'ubuntu', 'vsts', 'builder', 'build', 'work', 'home', 'dev', 'developer', 'example', 'someone', 'linuxbrew', 'git', 'jenkins', 'circleci', 'glados'}

def private_home(match):
    return re.split(r'[\\/]+', match[0])[-1].lower() not in NEUTRAL_USERS

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fix', action='store_true')
    args = parser.parse_args()
    names = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    found = []
    for name in sorted(set(names) - {''}):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if b'\0' in data[:8192]:
            continue
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if any(private_home(match) for match in PATTERN.finditer(text)) or IDENTITY_PATTERN.search(text):
            found.append(name)
            if args.fix:
                # Historical receipts retain their useful suffix without disclosing a user.
                clean = PATTERN.sub(lambda match: '<HOME>' if private_home(match) else match[0], text)
                clean = IDENTITY_PATTERN.sub(lambda match: match.group(1) + '<REDACTED>', clean)
                path.write_bytes(clean.encode('utf-8'))
    print(f'Public path and identity check: {len(found)} text files ' + ('normalized' if args.fix else 'flagged'))
    if not args.fix:
        for name in found:
            print(name)
    return bool(found) and not args.fix

if __name__ == '__main__':
    raise SystemExit(main())
