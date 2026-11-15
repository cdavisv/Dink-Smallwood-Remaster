#!/usr/bin/env python3
"""Write Content/Dink/Data/Presentation/speakers.csv: the dialogue box's speaker name for each Ink line id.

Source: SourceAssets/Audio/Voice/voice_lines.csv (one row per spoken line of the base game: id, script, character, kind...),
the voice cast's ledger. Only dialogue lines (and Dink's system lines) get a name; object lines (signs, letters, posters),
narration and engine messages show no name plate, and Dink's own lines fall back to "Dink" at run time anyway.

Names are tidied for display: "cave prisoner" -> "Cave Prisoner", "old man 2" -> "Old Man",
"dragon (spell caster)" -> "Dragon", "Cast agent / bar thug" -> "Cast Agent".

    python3 -I Scripts/export_presentation_data.py            # write
    python3 -I Scripts/export_presentation_data.py --check    # exit 1 if the checked-in file is stale
"""
import argparse
import csv
import io
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / 'SourceAssets/Audio/Voice/voice_lines.csv'
DEST = PROJECT / 'Content/Dink/Data/Presentation/speakers.csv'
NAMED_KINDS = {'dialogue', 'system'}
SMALL_WORDS = {'a', 'an', 'and', 'of', 'the', 'from', 'to', 'in', 'on'}


def display_name(character):
    """A cast ledger character label as a name plate, or '' for none."""
    name = (character or '').strip()
    name = name.split(' / ')[0]
    name = re.sub(r'\s*\([^)]*\)', '', name)
    name = re.sub(r'\s+\d+$', '', name).strip()
    if not name:
        return ''
    words = name.split()
    out = []
    for i, word in enumerate(words):
        if word[0].isupper() or any(c.isupper() for c in word[1:]):
            out.append(word)  # already a proper name ("SmileStein", "Royal")
        elif i > 0 and word in SMALL_WORDS:
            out.append(word)
        else:
            out.append(word[0].upper() + word[1:])
    return ' '.join(out)


def build_rows(lines_csv_text):
    rows = []
    for row in csv.DictReader(io.StringIO(lines_csv_text)):
        if row.get('kind') not in NAMED_KINDS:
            continue
        if row.get('kind') == 'system' and row.get('character') != 'Dink':
            continue  # engine messages ("game message", "UI hint") are not spoken by anyone
        name = display_name(row.get('character', ''))
        if name and row.get('id'):
            rows.append((row['id'], name))
    rows.sort()
    return rows


def render(rows):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(['line_id', 'name'])
    writer.writerows(rows)
    return buf.getvalue()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='fail if the checked-in file differs')
    args = parser.parse_args(argv)
    text = render(build_rows(SOURCE.read_text(encoding='utf-8')))
    if args.check:
        current = DEST.read_text(encoding='utf-8') if DEST.exists() else ''
        if current != text:
            print(f'{DEST.relative_to(PROJECT)} is stale: run Scripts/export_presentation_data.py', file=sys.stderr)
            return 1
        print(f'{DEST.relative_to(PROJECT)} up to date')
        return 0
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(text, encoding='utf-8')
    print(f'wrote {DEST.relative_to(PROJECT)}: {text.count(chr(10)) - 1} lines')
    return 0


if __name__ == '__main__':
    sys.exit(main())
