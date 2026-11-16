#!/usr/bin/env python3
"""Offline C++ syntax check with the build's own compiler flags: catch compile errors BEFORE spending an Unreal queue turn.

  python3 -I Scripts/syntax_check.py --project <private copy>/DinkRemasterUE <file.cpp> [<file.cpp> ...]

Needs one earlier build (successful or failed) of that project copy: it reuses UnrealBuildTool's response files
(Plugins/<P>/Intermediate/Build/Linux/x64/UnrealEditor/Development/<Module>/<File>.cpp.o.rsp, or
Intermediate/Build/Linux/x64/DinkRemasterEditor/Development/<Module>/ for the game module), which hold the exact clang,
defines, include paths and shared PCH of that module. Each file is compiled with `-fsyntax-only` (no object, no Unreal
process, about 5-15 s and one core per file), in the engine's Source folder as UBT does.

- A .cpp that has no response file yet (a new file) borrows one from another file of the same module.
- A header changed after UnrealHeaderTool last ran gets a scratch copy of its .generated.h with the UCLASS / USTRUCT /
  GENERATED_BODY line numbers moved to where they are now (the macros are keyed by line), so an added line above a
  UCLASS does not look like an error. A NEW reflected type (no .generated.h at all) still needs UHT: the script says so.
- A .cpp may live in a worktree (its plugin's flags come from the built copy). With --source-root <worktree>/DinkRemasterUE its
  headers are found before the copy's; without it every #include resolves in the COPY. Never copy files into a copy while a
  build of it may be running (UHT and clang read them mid-build).
- What it cannot catch: link errors, UHT errors (bad UPROPERTY specifiers), errors in files you did not list.

Prints one `SYNTAX OK` / `SYNTAX FAILED` line per file and exits non-zero on any failure.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

UE_ROOT = Path(os.environ.get('UE_ROOT', Path.home() / 'UnrealEngine/UE_5.8.4'))
MACRO = re.compile(r'^\s*(UCLASS|USTRUCT|UENUM|UINTERFACE|GENERATED_BODY|GENERATED_USTRUCT_BODY|GENERATED_UCLASS_BODY|GENERATED_UINTERFACE_BODY)\s*\(')


def module_of(cpp: Path) -> tuple[Path, str]:
    parts = cpp.resolve().parts
    i = len(parts) - 1 - parts[::-1].index('Source')
    return Path(*parts[:i]), parts[i + 1]   # plugin or project root, module name


def find_rsp(project: Path, cpp: Path):
    root, module = module_of(cpp)
    if not (root / 'Intermediate').is_dir() and (project / 'Plugins' / root.name / 'Intermediate').is_dir():
        root = project / 'Plugins' / root.name  # a worktree file: use the built copy's flags for the same plugin
    cands = list((root / 'Intermediate/Build/Linux/x64').glob(f'*/Development/{module}/{cpp.name}.o.rsp'))
    if not cands:
        cands = list((project / 'Intermediate/Build/Linux/x64').glob(f'*/Development/{module}/{cpp.name}.o.rsp'))
    if cands:
        return max(cands, key=lambda p: p.stat().st_mtime), False
    sib = sorted((root / 'Intermediate/Build/Linux/x64').glob(f'*/Development/{module}/*.cpp.o.rsp')) or \
          sorted((project / 'Intermediate/Build/Linux/x64').glob(f'*/Development/{module}/*.cpp.o.rsp'))
    sib = [p for p in sib if not p.name.startswith(('Module.', 'PerModuleInline'))]
    return (sib[0], True) if sib else (None, False)


def macro_lines(text: str):
    return [n + 1 for n, line in enumerate(text.splitlines()) if MACRO.match(line)]


def fixed_generated(source: Path, project: Path, scratch: Path, notes: list):
    """Scratch copies of stale .generated.h files with line ids moved to the header's current macro lines."""
    roots = [project] + sorted((project / 'Plugins').glob('*'))
    src_roots = ([source] + sorted((source / 'Plugins').glob('*'))) if source else []
    gens = [g for r in roots for g in (r / 'Intermediate/Build/Linux').glob('UnrealEditor/Inc/*/UHT/*.generated.h')] + \
        list((project / 'Intermediate/Build/Linux').glob('*/Inc/*/UHT/*.generated.h'))
    for gen in gens:
        stem = gen.name[: -len('.generated.h')]
        copy_h = [h for r in roots for h in (r / 'Source').glob(f'**/{stem}.h')]
        src_h = [h for r in src_roots for h in (r / 'Source').glob(f'**/{stem}.h')]
        if src_h and copy_h and src_h[0].read_bytes() != copy_h[0].read_bytes():
            hdrs = src_h  # edited in the worktree: always remap
        elif copy_h and copy_h[0].stat().st_mtime > gen.stat().st_mtime:
            hdrs = copy_h  # edited in the copy after UHT ran
        else:
            continue
        text = gen.read_text(errors='replace')
        old = sorted({int(m) for m in re.findall(rf'{re.escape(stem)}_h_(\d+)_', text)})
        new = macro_lines(hdrs[0].read_text(errors='replace'))
        if old == new:
            continue
        if len(old) != len(new):
            notes.append(f'{stem}.h changed its reflected types since UHT ran ({len(old)} -> {len(new)} macro lines): needs a real UHT run')
            continue
        for o, n in sorted(zip(old, new), key=lambda p: -p[0]):
            text = text.replace(f'{stem}_h_{o}_', f'{stem}_h_@{n}_')
        (scratch / gen.name).write_text(text.replace('_h_@', '_h_'))
        notes.append(f'{stem}.generated.h: line ids {old} -> {new} (scratch copy)')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--project', required=True, help='the project copy that was built (holds Intermediate/ and Plugins/*/Intermediate/)')
    ap.add_argument('--source-root', default='', help='a worktree DinkRemasterUE: its Source/Public and Private folders are searched BEFORE the copy\'s, '
                    'so edited headers are checked without copying them into a project copy (which a running build may be reading)')
    ap.add_argument('files', nargs='+')
    a = ap.parse_args(argv)
    project = Path(a.project).resolve()
    source = Path(a.source_root).resolve() if a.source_root else None
    scratch = Path(tempfile.mkdtemp(prefix='dink_syntax_'))
    notes: list = []
    fixed_generated(source, project, scratch, notes)
    first = [f'-I"{scratch}"']
    if source:
        for d in sorted({p.parent for p in list(source.glob('Source/*/*/*.h')) + list(source.glob('Plugins/*/Source/*/*/*.h')) + list(source.glob('Plugins/*/Source/*/*/*/*.h'))}):
            first.append(f'-I"{d}"')
    for n in notes:
        print('note:', n)
    failed = 0
    for f in a.files:
        cpp = Path(f).resolve()
        rsp, borrowed = find_rsp(project, cpp)
        if rsp is None:
            print(f'SYNTAX FAILED {cpp.name}: no response file for its module (build this project copy once)'); failed += 1; continue
        lines = [l for l in rsp.read_text().splitlines() if not re.match(r'^-(o|MD|MF|MT|MMD)\b', l)]
        # always compile the file given (the response file names the copy's own path, or another file's when borrowed)
        lines = [f'"{cpp}"' if l.strip('"').endswith('.cpp') and l.startswith('"') else l for l in lines]
        clang = next((l.strip('"') for l in lines if l.strip('"').endswith('clang++')), None) or \
            str(next(UE_ROOT.glob('Engine/Extras/ThirdPartyNotUE/SDKs/HostLinux/Linux_x64/*/x86_64-unknown-linux-gnu/bin/clang++')))
        out = scratch / (cpp.name + '.rsp')
        out.write_text('\n'.join([*first, *lines, '-fsyntax-only', '-fno-color-diagnostics', '-Wno-unused-command-line-argument']) + '\n')
        r = subprocess.run(['nice', '-n', '15', clang, f'@{out}'], cwd=UE_ROOT / 'Engine/Source', capture_output=True, text=True)
        errs = [l for l in (r.stdout + r.stderr).splitlines() if ' error: ' in l or 'error:' in l[:12]]
        if r.returncode == 0:
            print(f'SYNTAX OK {cpp.name}' + (' (borrowed flags of ' + rsp.name.split('.cpp')[0] + ')' if borrowed else ''))
        else:
            failed += 1
            print(f'SYNTAX FAILED {cpp.name}: {len(errs)} errors')
            print('\n'.join((r.stdout + r.stderr).splitlines()[:60]))
    shutil.rmtree(scratch, ignore_errors=True)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
