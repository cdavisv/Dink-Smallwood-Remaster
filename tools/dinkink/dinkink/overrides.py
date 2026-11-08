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
