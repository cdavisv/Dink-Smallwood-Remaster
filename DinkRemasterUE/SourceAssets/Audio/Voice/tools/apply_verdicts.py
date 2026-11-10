#!/usr/bin/env python3
"""Record listening verdicts from voice_takes_review.html.

    python3 tools/apply_verdicts.py ~/Downloads/voice_verdicts.csv [--date 2026-11-09]

Reads the CSV the page exports (id, voice, verdict, note), merges it into
voice_verdicts.csv (one row per line id, latest verdict wins) and sets the
asset ledger's `status` for each take: keep -> approved, redo -> rejected (the ledger's word for a take that is out). Lines with
only a note keep their status. Prints the redo list per voice so the next
generation batch can be built from it.
"""
import csv, datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../Audio/Voice
LEDGER = os.path.join(ROOT, "..", "..", "asset_ledger.csv")
OUT = os.path.join(ROOT, "voice_verdicts.csv")
STATUS = {"keep": "approved", "redo": "rejected"}

def main():
    args = sys.argv[1:]
    date = datetime.date.today().isoformat()
    if "--date" in args:
        i = args.index("--date"); date = args[i + 1]; del args[i:i + 2]
    if len(args) != 1:
        sys.exit(__doc__)
    new = {r["id"]: r for r in csv.DictReader(open(args[0], encoding="utf-8")) if r.get("id")}

    old = {}
    if os.path.exists(OUT):
        old = {r["id"]: r for r in csv.DictReader(open(OUT, encoding="utf-8"))}
    for lid, r in new.items():
        old[lid] = {"id": lid, "voice": r["voice"], "verdict": r["verdict"], "note": r.get("note", ""), "date": date}
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, ["id", "voice", "verdict", "note", "date"], lineterminator="\n")
        w.writeheader()
        for lid in sorted(old):
            w.writerow(old[lid])

    rows = list(csv.DictReader(open(LEDGER, encoding="utf-8")))
    fields = rows[0].keys()
    by_path = {r["asset_path"]: r for r in rows}
    changed = 0
    for lid, r in new.items():
        st = STATUS.get(r["verdict"])
        if not st:
            continue
        row = by_path.get(f"SourceAssets/Audio/Voice/{r['voice']}/{lid}.mp3")
        if row is None:
            print("not in ledger:", lid, file=sys.stderr); continue
        if row["status"] != st:
            row["status"] = st; changed += 1
        if r.get("note") and r["note"] not in row["notes"]:
            row["notes"] = (row["notes"] + "; " if row["notes"] else "") + f"listening {date}: {r['note']}"
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)

    redo = {}
    for r in old.values():
        if r["verdict"] == "redo":
            redo.setdefault(r["voice"], []).append(r)
    kept = sum(1 for r in old.values() if r["verdict"] == "keep")
    print(f"{len(old)} verdicts on file ({kept} keep, {sum(map(len, redo.values()))} redo); ledger rows changed: {changed}")
    for v in sorted(redo):
        print(f"  {v}: " + ", ".join(f"{r['id']}" + (f" ({r['note']})" if r["note"] else "") for r in redo[v]))

if __name__ == "__main__":
    main()
