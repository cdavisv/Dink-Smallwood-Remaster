"""Hand-curated source overrides: defects a script parser cannot localise by itself.

BRACE_TYPOS: a `{` the author typed where a `}` was meant. The engine's brace handling
(dink.cpp 7289-7360) nests everything after it, so the parse (and the live default) keeps
that nesting; the balanced reading is the author's intent. For each entry the block whose
opener sits at (script, line) is the last statement of an enclosing `if` body; the
converter hoists that block's statements out behind the same-named switch
`fix_<script>_l<line>` (so they cannot run by default, as in the engine, and run when the
switch is true) and reports the typo at `line` instead of the openers it left unbalanced
(`suppress`: the `unclosed_block` diagnostics of tools/dinkc that are one defect).
"""

BRACE_TYPOS = {
    ("s1-h3-8", 13): {
        "suppress": (7, 11),
        "engine": "line 13 is `{` where `}` was meant (it has the indentation of the `}` "
                  "lines 17 and 21): the `== 2` and `== 3` tests nest inside the `== 1` "
                  "block, so lines 16 and 20 are never spoken and two interactions in "
                  "three say nothing",
        "intent": "close the `== 1` block at line 13: one of three bed lines, chosen at "
                  "random",
    },
}

# OWNER_DECISIONS: fix switches the owner turned on for the shipped build. Every other
# `fix_` switch is emitted `false` (the 1997 engine's behaviour is the default, DESIGN.md
# section 9). Each entry names the switch, the decision date, why, and the dink.cpp lines
# that make the 1997 engine skip what the author wrote (the parity rule: an enabled switch
# carries its citation and a test, tests/test_dinkink.py OwnerDecisionTests). The converter
# emits `CONST <name> = true // owner decision 9 Nov 2026: ...` for these and fails the build
# if one of them is not generated (a renamed constant must not silently fall back to false).
# Decision OD2 of doc/remaster/verbatim_review.md ("Owner decisions"), 9 Nov 2026: the four
# pure-typo switches, whose lines the 1997 player never saw.
OWNER_DECISIONS = {
    "fix_s2_jack_l171": {
        "value": True,
        "decided": "2026-11-09",
        "reason": "typo: stray leading ' before the text of s2-jack.c:171; "
                  "\"I guess I just killed your husband.\" is spoken",
        "dink_cpp": "get_parms reads a string only between two double quotes (dink.cpp:4164); "
                    "with one the comma test fails and it returns early with the speaker 0 "
                    "(4206-4225); say_stop rejects sprite 0 (7908-7913)",
    },
    "fix_s4_sign3_l17": {
        "value": True,
        "decided": "2026-11-09",
        "reason": "typo: missing ) at s4-sign3.c:17; \"Long live the ducks.\" is spoken",
        "dink_cpp": "get_parms finds neither , nor ) after the speaker, the speaker reads 0 "
                    "(dink.cpp:4141-4186); say_stop rejects sprite 0 (7908-7913)",
    },
    "fix_s3_chick_l42": {
        "value": True,
        "decided": "2026-11-09",
        "reason": "typo: missing comma before &current_sprite at s3-chick.c:42; "
                  "Christina's \"Hello Dink, I'm Christina.\" is spoken",
        "dink_cpp": "after a string parameter get_parms demands a comma and otherwise returns "
                    "early with the rest 0 (dink.cpp:4206-4225); say_stop rejects sprite 0 "
                    "(7908-7913)",
    },
    "fix_s1_h3_8_l13": {
        "value": True,
        "decided": "2026-11-09",
        "reason": "typo: { for } at s1-h3-8.c:13; Libby's bed says one of its three lines "
                  "at random (lines 12, 16, 20)",
        "dink_cpp": "a { after a statement opens a block; the == 2 and == 3 tests nest inside "
                    "the == 1 block and a false if skips to the matching } (dink.cpp:7289-7360)",
    },
}
