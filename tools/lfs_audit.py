#!/usr/bin/env python3
"""Check that every Git LFS object a ref points at is actually stored on GitHub.

Why: a `git push` can succeed while the LFS upload silently does not (it happened
twice in Nov 2026, PR #31 among others); the commit then lands on master but any
fresh checkout aborts with "object not found" on those files. This asks the LFS
batch API directly, which is the only reliable check (a `git lfs fetch` will
happily report success for objects it already has locally).

Usage:
  tools/lfs_audit.py                 # audit origin/master
  tools/lfs_audit.py <ref> [<ref>..] # audit other refs (branches, HEAD, tags)
  tools/lfs_audit.py --fix <ref>     # also upload any missing object present in
                                     # the local LFS store (git lfs push --object-id)

Needs: git-lfs, and `gh auth token` for the repository's remote (origin).
Exit code 0 when nothing is missing, 1 otherwise.
"""
import json, os, re, subprocess, sys, urllib.request

def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, check=True, **k).stdout

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fix = "--fix" in sys.argv
    refs = args or ["origin/master"]
    root = sh("git", "rev-parse", "--show-toplevel").strip()
    url = sh("git", "remote", "get-url", "origin").strip()
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.split(":", 1)[1]
    if not url.endswith(".git"):
        url += ".git"
    token = sh("gh", "auth", "token").strip()
    store = sh("git", "rev-parse", "--git-common-dir").strip() + "/lfs/objects"
    missing_total = 0
    for ref in refs:
        ls = sh("git", "lfs", "ls-files", "-l", ref).splitlines()
        objs = {}
        for line in ls:
            oid, _, path = line.split(" ", 2)
            objs.setdefault(oid, path)
        if not objs:
            print(f"{ref}: no LFS files"); continue
        blobs = subprocess.run(["git", "cat-file", "--batch"], input="\n".join(f"{ref}:{p}" for p in objs.values()).encode(),
                               capture_output=True, check=True).stdout
        sizes = {m.group(1).decode(): int(m.group(2)) for m in re.finditer(rb"oid sha256:([0-9a-f]{64})\nsize (\d+)", blobs)}
        req_objs = [{"oid": o, "size": sizes.get(o, 0)} for o in objs]
        missing = []
        for i in range(0, len(req_objs), 100):
            body = json.dumps({"operation": "download", "transfers": ["basic"], "objects": req_objs[i:i + 100]}).encode()
            req = urllib.request.Request(url + "/info/lfs/objects/batch", data=body, method="POST", headers={
                "Accept": "application/vnd.git-lfs+json", "Content-Type": "application/vnd.git-lfs+json",
                "Authorization": "Bearer " + token})
            resp = json.load(urllib.request.urlopen(req))
            for o in resp["objects"]:
                if "actions" not in o:
                    missing.append((o["oid"], objs[o["oid"]], o.get("error", {}).get("message", "")))
        print(f"{ref}: {len(objs)} LFS objects, {len(missing)} missing on the server")
        for oid, path, err in missing:
            local = os.path.exists(f"{store}/{oid[:2]}/{oid[2:4]}/{oid}")
            print(f"  MISSING {oid[:12]} {path}  ({'in local store' if local else 'NOT local either'}; {err})")
        fixable = [oid for oid, _, _ in missing if os.path.exists(f"{store}/{oid[:2]}/{oid[2:4]}/{oid}")]
        if missing and fixable:
            cmd = ["git", "lfs", "push", "--object-id", "origin", *fixable]
            if fix:
                print(f"  uploading {len(fixable)} objects from the local store ...")
                subprocess.run(cmd, check=True)
            else:
                print(f"  fix (objects present locally): {' '.join(cmd[:5])} ... ({len(fixable)} ids); or rerun with --fix")
        if missing and len(fixable) < len(missing):
            print("  objects not in the local store must be found where the commit was made (a `~/Work` copy, "
                  "a clone's .git/lfs/objects) and copied into the store before pushing")
        missing_total += len(missing)
    sys.exit(1 if missing_total else 0)

if __name__ == "__main__":
    main()
