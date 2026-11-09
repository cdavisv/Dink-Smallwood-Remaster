"""Read authoritative binary asset hashes from Git's staged LFS pointers."""
import io
from pathlib import Path
import re
import subprocess

BINARY_SUFFIXES = set('.uasset .umap .fbx .obj .glb .abc .usd .usdc .usdz .blend .png .jpg .jpeg .tga .tif .tiff .exr .hdr .psd .kra .bmp .dds .wav .ogg .mp3 .flac .mid .mp4 .mov .webm .bk2 .ttf .otf .zip .7z'.split())
POINTER = re.compile(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n')


def pointer_metadata(data):
    match = POINTER.fullmatch(data)
    return {'sha256': match[1].decode(), 'size': int(match[2])} if match else None


def inventory(project):
    """Use the index, so changing a local asset cannot change its expected hash."""
    project = Path(project)
    records = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=project)
    entries = [record.split(b'\t', 1) for record in records.split(b'\0') if record]
    # Explicitly LFS-managed diagnostics need not have an image/mesh suffix.
    # Read attributes from the index too: local attributes cannot promote an
    # ordinary source file into accepted pointer-only metadata.
    attributes = subprocess.check_output(
        ['git', 'check-attr', '--cached', '-z', '--stdin', 'filter'], cwd=project,
        input=b'\0'.join(name for _, name in entries) + b'\0') if entries else b''
    fields = attributes.split(b'\0')
    lfs_paths = {fields[i] for i in range(0, len(fields) - 1, 3)
                 if fields[i + 1:i + 3] == [b'filter', b'lfs']}
    objects = {}
    for metadata, name in entries:
        mode, oid, stage = metadata.split()
        path = name.decode('utf-8')
        if Path(path).suffix.lower() not in BINARY_SUFFIXES and name not in lfs_paths:
            continue
        if stage != b'0' or mode not in (b'100644', b'100755'):
            raise ValueError('Unmerged or nonregular binary asset: ' + path)
        objects[path] = oid
    if not objects:
        raise ValueError('No tracked LFS binary assets; restore/stage the LFS asset revision first')
    ids = list(dict.fromkeys(objects.values()))
    output = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=project,
                                     input=b'\n'.join(ids) + b'\n')
    stream = io.BytesIO(output)
    expected = {}
    for oid in ids:
        header = stream.readline().split()
        if len(header) != 3 or header[0] != oid or header[1] != b'blob':
            raise ValueError('Cannot read staged asset object')
        data = stream.read(int(header[2]))
        if stream.read(1) != b'\n':
            raise ValueError('Truncated staged asset object')
        parsed = pointer_metadata(data)
        if parsed is None:
            paths = [name for name, value in objects.items() if value == oid]
            raise ValueError('Binary assets must be stored with Git LFS: ' + ', '.join(paths))
        expected[oid] = parsed
    return {name: dict(expected[oid]) for name, oid in objects.items()}
