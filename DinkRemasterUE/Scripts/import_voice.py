"""Import the approved voice lines (SourceAssets/Audio/Voice/<voice>/<line id>.mp3) as SoundWaves
and publish Content/Dink/Data/Audio/voice.json (line id -> SoundWave) for UDinkAudioSubsystem.

Run via import_voice.sh. Only ledger rows of kind "voice line" with status "approved" are imported;
every source is checked against the ledger's sha256 and duration before anything is written.
Re-runs skip SoundWaves whose source hash matches the previous report (DINK_VOICE_FORCE=1 re-imports).
DINK_VOICE_ONLY=<voice>[,<voice>...] limits the import to some voice folders (the manifest still lists
only lines whose SoundWave exists and loads).
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
LEDGER = ROOT / 'SourceAssets/asset_ledger.csv'
LINES = ROOT / 'SourceAssets/Audio/Voice/voice_lines.csv'
VOICE_DIR = ROOT / 'SourceAssets/Audio/Voice'
REPORT = ROOT / 'Saved/Audio/voice_import_report.json'
OUTPUT = ROOT / 'Content/Dink/Data/Audio/voice.json'
FOLDER = '/Game/Dink/Audio/Voice'
DURATION_TOLERANCE_S = 0.15
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    os.replace(temporary, path)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def asset_name(line_id):
    return 'VO_' + re.sub(r'[^A-Za-z0-9]', '_', line_id)


report = {'schema': 'dink-voice-import/1', 'passed': False, 'assets': {}, 'errors': []}
try:
    previous = {}
    if REPORT.is_file() and os.environ.get('DINK_VOICE_FORCE') != '1':
        try:
            previous = json.loads(REPORT.read_text()).get('assets', {})
        except ValueError:
            previous = {}
    only = {v for v in os.environ.get('DINK_VOICE_ONLY', '').split(',') if v}
    script_lines = {row['id']: row for row in csv.DictReader(LINES.open(newline=''))}

    # Validate every approved source before writing any asset.
    plan, names = [], {}
    for row in csv.DictReader(LEDGER.open(newline='')):
        if row['kind'] != 'voice line' or row['status'] != 'approved':
            continue
        relative = Path(row['asset_path'])
        require(relative.parts[:3] == ('SourceAssets', 'Audio', 'Voice') and len(relative.parts) == 5
                and relative.suffix == '.mp3', 'Unexpected voice path: ' + row['asset_path'])
        voice, line_id = relative.parts[3], relative.stem
        require(re.fullmatch(r'[a-z_]+', voice), 'Invalid voice folder: ' + voice)
        require(line_id in script_lines, 'Voice file for a line the script does not have: ' + line_id)
        require(script_lines[line_id]['voice'] == voice,
                'Line %s is cast as %s but its file is under %s' % (line_id, script_lines[line_id]['voice'], voice))
        name = asset_name(line_id)
        require(name not in names, 'SoundWave name collision: %s and %s' % (line_id, names.get(name)))
        names[name] = line_id
        source = (ROOT / relative).resolve()
        require(source.is_relative_to(VOICE_DIR), 'Voice source escaped SourceAssets/Audio/Voice: ' + str(relative))
        require(source.is_file(), 'Missing voice file: ' + str(relative))
        data = source.read_bytes()
        require(not data.startswith(b'version https://git-lfs'), 'LFS pointer, run git lfs pull: ' + str(relative))
        digest = hashlib.sha256(data).hexdigest()
        require(digest == row['sha256'], 'Source SHA256 differs from the ledger: ' + str(relative))
        duration = float(row['duration_s'])
        require(duration > 0, 'Ledger duration missing: ' + str(relative))
        folder = FOLDER + '/' + voice
        plan.append({'line_id': line_id, 'voice': voice, 'source': str(relative), 'sha256': digest,
                     'duration_s': duration, 'object_path': folder + '/' + name + '.' + name,
                     'folder': folder, 'name': name})
    require(plan, 'No approved voice lines in the ledger')

    imported = skipped = 0
    for item in plan:
        old = previous.get(item['line_id'])
        selected = not only or item['voice'] in only
        if not selected or (old and old.get('sha256') == item['sha256'] and LIB.does_asset_exist(item['object_path'])):
            if old and old.get('sha256') == item['sha256'] and LIB.does_asset_exist(item['object_path']):
                report['assets'][item['line_id']] = old
            skipped += 1
            continue
        task = unreal.AssetImportTask()
        task.filename = str(ROOT / item['source'])
        task.destination_path = item['folder']
        task.destination_name = item['name']
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.factory = unreal.SoundFactory()
        TOOLS.import_asset_tasks([task])
        asset = LIB.load_asset(item['object_path'])
        require(asset is not None and isinstance(asset, unreal.SoundWave), 'SoundWave import failed: ' + item['object_path'])
        asset.set_editor_property('looping', False)
        imported_duration = float(asset.get_editor_property('duration'))
        require(abs(imported_duration - item['duration_s']) <= DURATION_TOLERANCE_S,
                'Imported duration %.3f s differs from the ledger %.3f s: %s'
                % (imported_duration, item['duration_s'], item['object_path']))
        require(LIB.save_loaded_asset(asset, only_if_is_dirty=False), 'Failed saving SoundWave: ' + item['object_path'])
        entry = {k: item[k] for k in ('voice', 'source', 'sha256', 'duration_s', 'object_path')}
        entry['imported_duration_s'] = imported_duration
        report['assets'][item['line_id']] = entry
        imported += 1
        if imported % 100 == 0:
            print('DINK VOICE IMPORT progress: %d imported' % imported, flush=True)

    lines = {}
    for line_id, entry in sorted(report['assets'].items()):
        lines[line_id] = {'asset': entry['object_path'], 'voice': entry['voice'],
                          'duration_s': round(entry['imported_duration_s'], 3)}
    atomic_json(OUTPUT, {'schema': 'dink-voice/1', 'volume': 1.0, 'lines': lines})
    report.update(passed=True, approved=len(plan), imported=imported, skipped=skipped, published_lines=len(lines),
                  published=str(OUTPUT.relative_to(ROOT)))
    atomic_json(REPORT, report)
    print('DINK VOICE IMPORT OK: %d approved, %d imported, %d unchanged or not selected, %d lines published'
          % (len(plan), imported, skipped, len(lines)), flush=True)
except Exception as error:
    report['passed'] = False
    report['errors'].append(str(error))
    atomic_json(REPORT, report)
    unreal.log_error('DINK VOICE IMPORT FAILED: ' + str(error))
    raise
