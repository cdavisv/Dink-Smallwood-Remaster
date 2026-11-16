"""Editor import (UnrealEditor-Cmd -run=pythonscript) of the footstep and ambience-bed WAVs listed in
Content/Dink/Data/Audio/life.json `import` into /Game/Dink/Audio/Life. Run through Scripts/AudioQA/import_life_audio.sh."""
import json, wave
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.EditorAssetLibrary
spec = json.loads((ROOT / 'Content/Dink/Data/Audio/life.json').read_text())
ok = 0
for row in spec['import']:
    src = (ROOT / row['source']).resolve()
    if not src.is_file() or src.stat().st_size < 1000:
        raise RuntimeError('Missing or LFS-pointer WAV: ' + str(src))
    with wave.open(str(src), 'rb') as w:
        if w.getsampwidth() != 2:
            raise RuntimeError('Not PCM16: ' + str(src))
    task = unreal.AssetImportTask()
    task.filename = str(src)
    task.destination_path = '/Game/Dink/Audio/Life'
    task.destination_name = row['name']
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.factory = unreal.SoundFactory()
    TOOLS.import_asset_tasks([task])
    path = '/Game/Dink/Audio/Life/%s.%s' % (row['name'], row['name'])
    asset = LIB.load_asset(path)
    if asset is None or not isinstance(asset, unreal.SoundWave):
        raise RuntimeError('Import failed: ' + path)
    asset.set_editor_property('looping', bool(row['loop']))
    if abs(float(asset.get_editor_property('duration')) - float(row['duration_s'])) > 0.02:
        raise RuntimeError('Duration mismatch: ' + path)
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Save failed: ' + path)
    ok += 1
print('DINK LIFE AUDIO IMPORT OK: %d SoundWaves in /Game/Dink/Audio/Life' % ok, flush=True)
