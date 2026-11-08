"""Import the reviewed, hash-pinned WAV selection and publish runtime JSON on success.
Run via import_approved_audio.sh; no rejected/candidate audio is imported implicitly.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import wave
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
SELECTION = ROOT / 'SourceAssets/Audio/selection_manifest.json'
REPORT = ROOT / 'Saved/Audio/import_report.json'
OUTPUT = ROOT / 'Content/Dink/Data/Audio/approved.json'
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
report = {'schema': 'dink-audio-import/1', 'selection': str(SELECTION.relative_to(ROOT)),
          'passed': False, 'assets': [], 'errors': []}


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    os.replace(temporary, path)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def references(value):
    if isinstance(value, str) and value.startswith('/Game/'):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from references(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from references(item)


try:
    specification = json.loads(SELECTION.read_text())
    require(specification.get('schema') == 'dink-audio-selection/1', 'Unsupported audio selection schema')
    rows = specification.get('assets')
    require(isinstance(rows, list) and rows, 'Audio selection contains no approved assets')
    runtime = specification.get('runtime')
    require(isinstance(runtime, dict) and runtime.get('schema') == 'dink-audio/1', 'Invalid runtime audio schema')
    for key in ['sounds', 'music', 'screen_music', 'volumes', 'rejected']:
        require(key in runtime, 'Missing runtime audio field: ' + key)
    # Validate ALL source inputs before writing any Unreal assets.
    approved = {}
    for row in rows:
        name, folder = row['name'], row['folder']
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name), 'Invalid SoundWave name')
        require(isinstance(folder, str) and folder.startswith('/Game/Dink/') and '..' not in folder,
                'Audio folder must be under /Game/Dink: ' + str(folder))
        require(isinstance(row['loop'], bool), 'Loop flag must be boolean for ' + name)
        source_relative = Path(row['source'])
        require(not source_relative.is_absolute(), 'WAV source must be project relative')
        source = (ROOT / source_relative).resolve()
        require(source.is_relative_to(ROOT / 'SourceAssets/Audio'), 'WAV source escaped SourceAssets/Audio')
        require(source.is_file() and source.suffix.lower() == '.wav', 'Missing WAV: ' + str(source_relative))
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        require(digest == row['sha256'], 'Source SHA256 mismatch: ' + str(source_relative))
        with wave.open(str(source), 'rb') as wav:
            channels, rate, frames, width = wav.getnchannels(), wav.getframerate(), wav.getnframes(), wav.getsampwidth()
            require(wav.getcomptype() == 'NONE', 'Compressed WAV unsupported: ' + name)
            require(channels in (1, 2) and width == 2 and rate > 0 and frames > 0,
                    'Expected nonempty mono/stereo PCM16 WAV: ' + name)
            duration = frames / rate
        expected = float(row['duration_s'])
        require(math.isfinite(expected) and expected > 0 and abs(duration - expected) <= max(1/rate, .001),
                'WAV duration differs from selection: ' + name)
        object_path = folder.rstrip('/') + '/' + name + '.' + name
        entry = {'name': name, 'source': str(source_relative), 'object_path': object_path,
                 'sha256': digest, 'duration_s': duration, 'sample_rate': rate,
                 'channels': channels, 'loop': row['loop'], 'passed': False}
        if object_path in approved:
            require(approved[object_path][0] == row, 'Conflicting duplicate SoundWave selection: ' + object_path)
            continue
        approved[object_path] = (row, source, entry)
    runtime_refs = set(references({key: runtime[key] for key in ['sounds', 'music', 'screen_music']}))
    require(runtime_refs <= set(approved), 'Runtime references unapproved audio: ' + str(sorted(runtime_refs - set(approved))))
    for object_path, (row, source, entry) in approved.items():
        report['assets'].append(entry)
        task = unreal.AssetImportTask()
        task.filename = str(source)
        task.destination_path = row['folder'].rstrip('/')
        task.destination_name = row['name']
        task.automated = True
        task.replace_existing = True
        task.save = False
        task.factory = unreal.SoundFactory()
        TOOLS.import_asset_tasks([task])
        asset = LIB.load_asset(object_path)
        require(asset is not None and isinstance(asset, unreal.SoundWave), 'SoundWave import failed: ' + object_path)
        asset.set_editor_property('looping', row['loop'])
        require(bool(asset.get_editor_property('looping')) == row['loop'], 'Loop flag did not apply: ' + object_path)
        imported_duration = float(asset.get_editor_property('duration'))
        require(abs(imported_duration - entry['duration_s']) < .02,
                'Imported SoundWave duration mismatch: ' + object_path)
        require(LIB.save_loaded_asset(asset, only_if_is_dirty=False), 'Failed saving SoundWave: ' + object_path)
        entry.update(passed=True, imported_duration_s=imported_duration,
                     imported_object_paths=list(task.imported_object_paths))
    report['passed'] = True
    report['asset_count'] = len(approved)
    report['runtime_reference_count'] = len(runtime_refs)
    atomic_json(OUTPUT, runtime)
    report['published'] = str(OUTPUT.relative_to(ROOT))
    atomic_json(REPORT, report)
    print('DINK AUDIO IMPORT OK: %d approved SoundWaves, runtime manifest published' % len(approved), flush=True)
except Exception as error:
    report['passed'] = False
    report['errors'].append(str(error))
    atomic_json(REPORT, report)
    unreal.log_error('DINK AUDIO IMPORT FAILED: ' + str(error))
    raise
