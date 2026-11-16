#!/usr/bin/env python3
"""Compare the probe's trace md5s of two Unreal test runs: DinkExpanded OFF and ON (the beta gate's parity condition).

Run the two test turns first (one Unreal step each, through the machine's lock), in a built copy:

    DINK_TEST_RUN=expanded_off DINK_EXPANDED=0 Scripts/test.sh Dink
    DINK_TEST_RUN=expanded_on  DINK_EXPANDED=1 Scripts/test.sh Dink

then

    python3 -I tools/expanded/probe_parity.py <copy>/Saved/Logs/test_expanded_off.log <copy>/Saved/Logs/test_expanded_on.log

Prints every chapter's md5 in both runs and exits 1 unless both runs completed the same chapters with equal md5s and
the ON run really had the switch on (its log names the packs DinkExpanded loaded) and the OFF run had it off.
"""

import re
import sys

CHAPTER = re.compile(r"chapter (\d+): (\d+) of (\d+) steps, trace md5 ([0-9a-f]{10})")
ON = re.compile(r"DinkExpanded: ON, (\d+) pack")
OFF = re.compile(r"DinkExpanded is OFF")


def read(path):
    md5 = {}
    on = off = False
    with open(path, errors="replace") as fh:
        for line in fh:
            m = CHAPTER.search(line)
            if m:
                md5[int(m.group(1))] = (m.group(4), int(m.group(2)), int(m.group(3)))
            # The module states the switch once at start; later ON lines are tests that switch it themselves.
            if not (on or off):
                on = bool(ON.search(line))
                off = bool(OFF.search(line))
    return md5, on, off


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    off_md5, off_on, off_off = read(argv[1])
    on_md5, on_on, on_off = read(argv[2])
    ok = True
    if not off_off or off_on:
        print("OFF run: the log does not show the switch off")
        ok = False
    if not on_on:
        print("ON run: the log does not show DinkExpanded ON with its packs")
        ok = False
    chapters = sorted(set(off_md5) | set(on_md5))
    if not chapters:
        print("no probe chapters in either log")
        return 1
    for c in chapters:
        a, b = off_md5.get(c), on_md5.get(c)
        same = a is not None and b is not None and a[0] == b[0] and a[1] == a[2] and b[1] == b[2]
        ok &= same
        print("Ch%-2d off %-12s on %-12s %s" % (c, "%s %d/%d" % a if a else "-", "%s %d/%d" % b if b else "-", "EQUAL" if same else "DIFFERENT"))
    print("PROBE PARITY %s: %d chapter(s)" % ("OK" if ok else "FAILED", len(chapters)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
