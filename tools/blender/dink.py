#!/usr/bin/env python3
"""Convenience wrapper: run one dinkasset script in headless Blender and print only its JSON.

    python3 dink.py validate --blend sources/Props/SM_Barrel_01.blend
    python3 dink.py fix --blend in.blend --output out.blend --all-safe --rename
    python3 dink.py make_lods --blend in.blend --inplace --lods --collision
    python3 dink.py export_ue --blend in.blend --out out/export
    python3 dink.py import_generated --input barrel.glb --name SM_Barrel_02 --class prop --height 0.9 --out x.blend
    python3 dink.py --summary validate --blend in.blend      # human-readable instead of JSON

Blender's own log noise goes to stderr (shown with --verbose, hidden otherwise); stdout carries only
the JSON report; the exit code is the script's (0 ok, 1 findings/rejections, 2 usage or load error,
3 Blender crashed or produced no report). Set $BLENDER to use a specific binary.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BEGIN, END = "@@DINK_REPORT_BEGIN@@", "@@DINK_REPORT_END@@"
SCRIPTS = ("validate", "fix", "make_lods", "export_ue", "import_generated")


def summarize(rep):
    lines = []
    tool = rep.get("tool")
    if tool == "validate" or "validation" in rep:
        v = rep.get("validation", rep)
        for f in v.get("scene_findings", []):
            lines.append("%-7s %-22s %s" % (f["severity"].upper(), f["code"], f["message"]))
        for a in v.get("assets", []):
            lines.append("%s %s (%s) tris=%s" % ("PASS" if a["passed"] else "FAIL", a["name"], a["class"], a["tris_per_lod"]))
            for f in a["findings"]:
                if f["severity"] != "info":
                    lines.append("   %-7s %-22s %s" % (f["severity"].upper(), f["code"], f["message"]))
        if v.get("summary"):
            lines.append("summary: %s" % json.dumps(v.get("summary")))
    for k in ("fixes", "exported", "rejected", "steps"):
        for item in rep.get(k, []):
            lines.append("%s: %s" % (k, json.dumps(item)))
    if "assets" in rep and tool == "make_lods":
        for a in rep["assets"]:
            for e in a["log"]:
                lines.append("%s: %s" % (a["asset"], json.dumps(e)))
    if rep.get("fatal"):
        lines.append("FATAL: " + rep["fatal"])
    return "\n".join(lines)


def main(argv):
    summary = verbose = False
    while argv and argv[0].startswith("--") and argv[0] in ("--summary", "--verbose"):
        summary |= argv[0] == "--summary"
        verbose |= argv[0] == "--verbose"
        argv = argv[1:]
    if not argv or argv[0] not in SCRIPTS:
        print(__doc__)
        return 2
    blender = os.environ.get("BLENDER") or shutil.which("blender")
    if not blender:
        print("Blender not found (set $BLENDER)", file=sys.stderr)
        return 2
    script = os.path.join(HERE, "dinkasset", argv[0] + ".py")
    p = subprocess.run([blender, "-b", "--factory-startup", "-P", script, "--"] + argv[1:],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = p.stdout
    if verbose or BEGIN not in out:
        sys.stderr.write(out)
    if BEGIN not in out or END not in out:
        return 3 if p.returncode in (0, 1) else p.returncode
    text = out[out.index(BEGIN) + len(BEGIN):out.index(END)].strip()
    print(summarize(json.loads(text)) if summary else text)
    return p.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
