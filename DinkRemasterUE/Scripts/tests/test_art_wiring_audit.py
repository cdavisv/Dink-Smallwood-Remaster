"""Scripts/art_wiring_audit.py: package reading, the checks and the reviewed-reason table."""
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'art_wiring_audit.py'
spec = importlib.util.spec_from_file_location('art_wiring_audit', SCRIPT)
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def fstrings(*values):
    """Bytes as a .uasset stores FStrings: int32 length (with the NUL), ASCII, NUL."""
    out = b'\x00' * 16
    for v in values:
        b = v.encode() + b'\x00'
        out += struct.pack('<i', len(b)) + b
    return out


class FakePackages(A.Packages):
    def __init__(self, blobs):
        self.lfs = None
        self.files = {g: g for g in blobs}
        self.by_name = {}
        for g in blobs:
            self.by_name.setdefault(os.path.basename(g), []).append(g)
        self._strings = {}
        self.unreadable = set()
        self.blobs = blobs

    def strings(self, game):
        data = self.blobs[game]
        return [m.group(2).decode() for m in A.FSTRING.finditer(data) if len(m.group(2)) + 1 == m.group(1)[0]]


class PackageReading(unittest.TestCase):
    def setUp(self):
        self.pk = FakePackages({
            '/Game/Dink/K/SM_Rock': fstrings('/Game/Dink/K/SM_Rock', '/Game/Dink/K/MI_Rock', 'SM_Rock',
                                             '/Script/Engine.StaticMesh', 'LODs', '1', 'NaniteEnabled', 'False',
                                             'Triangles', '9000'),
            '/Game/Dink/K/MI_Rock': fstrings('/Game/Dink/K/MI_Rock', '/Game/Dink/K/Textures/T_Rock_BC', 'MI_Rock',
                                             '/Script/Engine.MaterialInstanceConstant'),
            '/Game/Dink/K/SM_Grey': fstrings('SM_Grey', '/Script/Engine.StaticMesh',
                                             '/Engine/EngineMaterials/WorldGridMaterial'),
            '/Game/Dink/K/Textures/T_Rock_N': fstrings('T_Rock_N', '/Script/Engine.Texture2D', 'CompressionSettings',
                                                       'TC_Default', 'SRGB', 'True'),
            '/Game/Dink/K/Textures/T_Rock_ORM': fstrings('T_Rock_ORM', '/Script/Engine.Texture2D',
                                                         'CompressionSettings', 'TC_Masks', 'SRGB', 'False'),
            '/Game/Dink/V/SM_Veg_Grass': fstrings('SM_Veg_Grass', '/Script/Engine.StaticMesh', 'NaniteEnabled', 'True',
                                                  '/Game/Dink/K/MI_Rock'),
            '/Game/Dink/K/SM_Chair_Oak': fstrings('SM_Chair_Oak', '/Script/Engine.StaticMesh', 'NaniteEnabled', 'True',
                                                  '/Game/Dink/K/MI_Rock'),
        })

    def flags(self, game):
        return [f for f, _ in A.check_package(self.pk, game, self.pk.tags(game))]

    def test_tags_and_class(self):
        t = self.pk.tags('/Game/Dink/K/SM_Rock')
        self.assertEqual(t['_class'], 'StaticMesh')
        self.assertEqual(t['Triangles'], '9000')
        self.assertIn('/Game/Dink/K/MI_Rock', self.pk.refs('/Game/Dink/K/SM_Rock'))

    def test_mesh_checks(self):
        self.assertEqual(self.flags('/Game/Dink/K/SM_Rock'), ['lod'])          # one LOD, 9000 triangles, Nanite off
        self.assertEqual(self.flags('/Game/Dink/K/SM_Grey'), ['default_material'])
        self.assertIn('missing_texture', self.flags('/Game/Dink/K/MI_Rock'))   # T_Rock_BC is not a package
        self.assertEqual(self.flags('/Game/Dink/V/SM_Veg_Grass'), ['nanite'])
        self.assertEqual(self.flags('/Game/Dink/K/SM_Chair_Oak'), [])          # "chair" is not hair

    def test_texture_checks(self):
        self.assertEqual(self.flags('/Game/Dink/K/Textures/T_Rock_N'), ['texture'])
        self.assertEqual(self.flags('/Game/Dink/K/Textures/T_Rock_ORM'), [])

    def test_reachability(self):
        via = A.reach(self.pk, {'/Game/Dink/K/SM_Rock': {'Content/Dink/Data/Art/families.json'}})
        self.assertIn('/Game/Dink/K/MI_Rock', via)
        self.assertTrue(via['/Game/Dink/K/MI_Rock'].startswith('via SM_Rock'))
        self.assertNotIn('/Game/Dink/K/SM_Grey', via)


class Reasons(unittest.TestCase):
    def test_known_table_parses_and_matches(self):
        rows = A.known_rows()
        self.assertTrue(rows)
        self.assertIsNone(A.known_reason('SK_Duck', '', rows))           # #113 merged: the duck is wired, no reason
        self.assertEqual(A.known_reason('AN_Duck_Peck', '', rows)[0], 'bug')
        self.assertEqual(A.known_reason('SM_Castle_Wall_8m', 'SourceAssets/Art/PhotorealPass/Structures/Castle/x.fbx', rows)[0], 'queued')
        self.assertIsNone(A.known_reason('SM_Castle_Wall_8m', 'SourceAssets/Art/Other/x.fbx', rows))
        self.assertEqual(A.known_reason('SM_Anything', 'SourceAssets/Art/StonebrookRuins/Export/a.fbx', rows)[0], 'alternate')

    def test_gap_flag(self):
        self.assertEqual(A.gap_flag('queued: PR #113', ''), 'queued')
        self.assertEqual(A.gap_flag('', 'VS-02'), 'queued')
        self.assertEqual(A.gap_flag('deliberate: a reviewed reason', ''), 'deliberate')
        self.assertEqual(A.gap_flag('STATUS.md: not imported: hangs on a wall', ''), 'documented')  # not reviewed here
        self.assertEqual(A.gap_flag('replaced: mocap', ''), 'replaced')
        self.assertIsNone(A.gap_flag('', ''))

    def test_clip_played(self):
        natural = {'drop_prefixes': ['Walk_']}
        self.assertTrue(A.deliberate_clip_reason('AN_Walk_Timid', natural, {}))
        self.assertEqual(A.clip_played('AN_Fist_Jab_Timid', '', {'Fist_Jab'}, {}, []), "yes (C++ asks for 'Fist_Jab')")
        self.assertTrue(A.clip_played('AN_Wave', '', set(), {}, []).startswith('no (no runtime'))

    def test_card_table_counts_only_drawn_cards(self):
        with tempfile.TemporaryDirectory() as d:
            audit = Path(d) / 'audit.jsonl'
            prim = lambda o, z, frame: {'cn': 'Card', 'o': o, 'max': [0, 0, z],
                                        'mats': [{'m': '/Game/Dink/_Generated/Sprites/MI_Sprite_93_%02d.MI_Sprite_93_%02d' % (frame, frame)}]}
            audit.write_text(json.dumps({'screen': 409, 'prims': [prim('S409_P01', 100, 4), prim('S409_P02', -2000, 4),
                                                                   prim('S409_P03', 100, 1)]}) + '\n')
            cov = Path(d) / 'cov.csv'
            cov.write_text('origin_id,state\nS409_P01,placeholder\nS409_P03,final\n')
            rows = A.card_table(str(audit), str(cov), str(Path(d) / 'none.json'), {'fence_rail_ns': {'SM_Fence'}})
        by = {r['class']: r for r in rows}
        self.assertEqual(by['fence_rail_ns']['cards'], 1)               # the buried card is not drawn
        self.assertEqual(by['fence_rail_ns']['mesh_available'], 'SM_Fence')
        self.assertEqual(by['fence_rail_ew']['final_origin_cards'], 'S409_P03')


class Classifier(unittest.TestCase):
    """Review of PR #154 (15 Nov 2026): what may and may not count as a runtime binding."""

    def setUp(self):
        self.pk = FakePackages({'/Game/Dink/A/SM_Door': b'', '/Game/Dink/B/SM_Door': b'', '/Game/Dink/A/SM_Only': b'',
                                '/Game/Dink/Photoreal/TownExteriors/SM_Wall': b'', '/Game/Dink/Old/SM_Wall': b''})
        self.roots = A.collections.defaultdict(set)

    def test_a_free_text_fields_do_not_bind(self):
        A.walk_json({'family': 'x', 'mesh': '/Game/Dink/A/SM_Only.SM_Only',
                     'note': 'SM_Door is imported but unbound; see /Game/Dink/B/SM_Door', 'why': 'SM_Door'},
                    'families.json', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Only'])

    def test_a_keys_and_asset_lists_do_not_bind(self):
        A.walk_json({'mesh_swaps': {'/Game/Dink/A/SM_Door': ['/Game/Dink/A/SM_Only']},
                     'assets': [{'mesh': '/Game/Dink/B/SM_Door.SM_Door'}]}, 'environment.json', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Only'])     # (d): the swap source key is not bound

    def test_b_a_path_binds_only_the_package_it_names(self):
        A.walk_json({'mesh': '/Game/Dink/A/SM_Door.SM_Door'}, 'm.json', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Door'])      # not the same-named twin in B
        A.walk_json({'mesh': 'SM_Door'}, 'm.json', self.pk, self.roots)     # an ambiguous bare name binds nothing more
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Door'])
        A.walk_json({'mesh': 'SM_Wall'}, 'town_houses.json', self.pk, self.roots,
                    A.BARE_PREFIX['town_houses.json'])                      # resolved under the runtime's folder
        self.assertIn('/Game/Dink/Photoreal/TownExteriors/SM_Wall', self.roots)
        self.assertNotIn('/Game/Dink/Old/SM_Wall', self.roots)

    def test_c_only_runtime_modules_are_cpp_roots(self):
        # reads the project's real .uplugin / .uproject files: run in a full checkout (or copy them into a snapshot)
        dirs = [d.replace(os.sep, '/') for d in A.runtime_module_dirs()]
        self.assertTrue(any(d.endswith('Plugins/DinkCore/Source/DinkCore') for d in dirs))
        self.assertFalse(any('DinkImport' in d or 'DinkParity' in d or 'DinkProbe' in d for d in dirs))

    def test_c_cpp_literals_bind_but_comments_do_not(self):
        text = '// SM_Only is mentioned in a comment\nLoad(TEXT("/Game/Dink/A/SM_Door.SM_Door"));'
        for lit in A.CPP_LITERAL.findall(text):
            A.bind_string(lit, 'x.cpp', self.pk, self.roots)
        self.assertEqual(sorted(self.roots), ['/Game/Dink/A/SM_Door'])


class OwnerIds(unittest.TestCase):
    def test_owner_ids_must_exist(self):
        ids = A.table_ids()          # reads doc/remaster in a full checkout
        self.assertIn('A209', ids)              # a bug-list row (queue rows are retired by design)
        self.assertEqual(A.OWNER_ID.findall('see A204 and DS-07, PQ-Q5'), ['A204', 'DS-07', 'PQ-Q5'])
        A.known_rows()               # every id art_wiring_known.json names exists (or is declared pending)


class Swaps(unittest.TestCase):
    """environment.json mesh_swaps: which roots the runtime swaps (review 2 of PR #154)."""

    def test_authored_swapped_context_and_family_not(self):
        swapped = {'/Game/K/SM_Oak': ['/Game/P/SM_Veg_Oak']}
        roots = {'/Game/K/SM_Oak': {'Content/Dink/Data/Art/stonebrook_exterior.json', 'Content/Dink/Data/Art/vista.json',
                                    'Content/Dink/Data/Art/families.json', 'Content/Dink/Data/Art/camera_exteriors.json'}}
        authored = {'Content/Dink/Data/Art/stonebrook_exterior.json': 439}
        context = {'Content/Dink/Data/Art/vista.json'}
        done, decided, missed = A.swap_status(['/Game/K/SM_Oak'], roots, swapped, {}, authored, context)
        self.assertEqual(done, ['Content/Dink/Data/Art/stonebrook_exterior.json'])
        self.assertEqual(decided, [])
        self.assertEqual(missed, ['Content/Dink/Data/Art/families.json', 'Content/Dink/Data/Art/vista.json'])  # camera_* ignored

    def test_only_tag_limits_the_swap_on_purpose(self):
        g = '/Game/K/SM_Cottage'
        swapped = {g: ['/Game/P/SM_Cottage_PR']}
        only = {g: 'DinkArtScreen_439'}
        roots = {g: {'a439.json', 'a001.json', 'vista.json'}}
        done, decided, missed = A.swap_status([g], roots, swapped, only, {'a439.json': 439, 'a001.json': 1}, {'vista.json'})
        self.assertEqual(done, ['a439.json'])
        self.assertEqual(decided, ['a001.json', 'vista.json'])   # kept old on purpose, not a wiring bug
        self.assertEqual(missed, [])


class Deliveries(unittest.TestCase):
    """Review of PR #162: one export is one delivery; name the one each package came from."""

    def test_export_mirror_and_lod_folders_fold(self):
        self.assertEqual(A.delivery_root('Stonebrook440/Export/LODs/SM_HayBale_01_LOD0.fbx'), 'Stonebrook440')
        self.assertEqual(A.delivery_root('Stonebrook440/Export/Game/Dink/Props/Stonebrook440/SM_HayBale_01.fbx'), 'Stonebrook440')
        self.assertEqual(A.delivery_root('PhotorealPass/Corpses/Corpse_Girl/SM_Corpse_Girl_PR.fbx'), 'PhotorealPass/Corpses/Corpse_Girl')

    def test_detail_names_the_imported_delivery(self):
        class PK:
            def import_sources(self, g):
                return ['PhotorealPass/Corpses/Corpse_Girl/SM_Corpse_Girl_PR.fbx'] if g.endswith('Girl_PR') else []
        pk = PK()
        pk.files = {'/Game/Dink/Photoreal/Corpses/SM_Corpse_Girl_PR': 1}
        d = A.delivery_detail(['PhotorealPass/Corpses/Corpse_Girl', 'PhotorealPass/Unclaimed/corpse_girl/Corpse_Girl'],
                              {'SM_Corpse_Girl_PR'}, pk)
        self.assertIn('PhotorealPass/Corpses/Corpse_Girl imported as /Game/Dink/Photoreal/Corpses/SM_Corpse_Girl_PR', d)
        self.assertIn('PhotorealPass/Unclaimed/corpse_girl/Corpse_Girl: not imported (no package records it)', d)

    def test_import_source_is_read_from_the_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'SM_X.uasset'
            f.write_bytes(b'x' * 300 + b'{ "RelativeFilename" : "../../../SourceAssets/Art/Kit/Export/SM_X.fbx", "Timestamp" }')
            pk = FakePackages({})
            pk.files = {'/Game/X/SM_X': str(f)}
            pk.lfs = None
            self.assertEqual(A.Packages.import_sources(pk, '/Game/X/SM_X'), ['Kit/Export/SM_X.fbx'])


class OwnerIdHistory(unittest.TestCase):
    """Review 2 of PR #162: a removed queue row must never stop the run (CI clones depth 1; snapshots have no .git)."""

    def test_stale_and_unknown_ids_only_classify(self):
        rows = [{'why': 'owned by DS-07'}, {'why': 'see GP-Q9'}, {'why': 'VS-15 pending', 'pending_ids': ['VS-15']}]
        self.assertEqual(A.check_owner_ids(rows, {'DS-07'}, {'DS-07', 'GP-Q9'}), ([], ['GP-Q9'], []))
        self.assertEqual(A.check_owner_ids(rows, {'DS-07'}, None), (['GP-Q9'], [], []))      # history unknown
        self.assertEqual(A.check_owner_ids(rows, {'DS-07', 'VS-15'}, set())[2], ['VS-15'])

    def _fixture(self, root):
        ue = root / 'DinkRemasterUE'
        (ue / 'Scripts').mkdir(parents=True)
        (root / 'doc' / 'remaster').mkdir(parents=True)
        (ue / 'Scripts' / 'art_wiring_audit.py').write_text(SCRIPT.read_text())
        (ue / 'Scripts' / 'art_wiring_known.json').write_text(json.dumps({'rows': [
            {'match': '^SM_A$', 'kind': 'queued', 'why': 'owned by DS-08'},
            {'match': '^SM_B$', 'kind': 'bug', 'why': 'bug row A209'}]}))
        (root / 'doc' / 'remaster' / 'ALPHA_BUG_LIST.md').write_text('| A209 | S3 | x |\n')
        (root / 'doc' / 'remaster' / 'FABLE_ART_QUEUE.md').write_text('| DS-08 | x |\n')
        return ue

    def _run(self, ue):
        return subprocess.run([sys.executable, '-I', '-c', 'import sys; sys.path.insert(0, "Scripts"); '
                               'import art_wiring_audit as A; A.known_rows(); print("ran", sorted(A.STALE_IDS))'],
                              cwd=ue, capture_output=True, text=True)

    def test_removed_row_in_a_shallow_clone_and_without_git_warns_and_runs(self):
        if shutil.which('git') is None:
            self.skipTest('no git')
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'src'
            ue = self._fixture(src)
            env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.invalid',
                       GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.invalid')
            git = lambda *a, cwd=src: subprocess.run(['git', '-c', 'core.hooksPath=/dev/null'] + list(a), cwd=cwd, env=env,
                                                     capture_output=True, text=True, check=True)
            git('init', '-q'); git('add', '-A'); git('commit', '-q', '-m', 'one')
            (src / 'doc' / 'remaster' / 'FABLE_ART_QUEUE.md').write_text('')            # DS-08 removed (its PR merged)
            git('commit', '-q', '-am', 'two')
            full = self._run(ue)                                                         # full history: stale
            self.assertEqual(full.returncode, 0, full.stderr)
            self.assertIn("ran ['DS-08']", full.stdout)
            self.assertIn('DS-08 was removed', full.stderr)
            clone = Path(d) / 'clone'
            subprocess.run(['git', 'clone', '-q', '--depth', '1', 'file://' + str(src), str(clone)], check=True,
                           capture_output=True)
            shallow = self._run(clone / 'DinkRemasterUE')                               # CI: depth-1 checkout
            self.assertEqual(shallow.returncode, 0, shallow.stderr)
            self.assertIn('DS-08 is missing from both tables (git history unknown', shallow.stderr)
            self.assertIn("ran ['DS-08']", shallow.stdout)                              # the reason is marked stale
            plain = Path(d) / 'plain'
            shutil.copytree(src, plain, ignore=shutil.ignore_patterns('.git'))           # snapshot without .git
            nogit = self._run(plain / 'DinkRemasterUE')
            self.assertEqual(nogit.returncode, 0, nogit.stderr)
            self.assertIn('DS-08 is missing from both tables (git history unknown', nogit.stderr)
            self.assertIn("ran ['DS-08']", nogit.stdout)
            self.assertNotIn('A209', nogit.stdout)                                     # a present row is not stale

    def test_removing_a_named_row_from_a_copy_of_the_tables_keeps_the_run_going(self):
        with tempfile.TemporaryDirectory() as d:
            bug = Path(d) / 'ALPHA_BUG_LIST.md'
            bug.write_text('| A209 | S3 | x |\n')
            q = Path(d) / 'FABLE_ART_QUEUE.md'
            q.write_text('| DS-07 | x |\n')     # DS-08 removed
            current = A.table_ids([str(bug), str(q)])
            unknown, stale, _ = A.check_owner_ids([{'why': 'DS-08 and A209'}], current, {'DS-08', 'A209', 'DS-07'})
            self.assertEqual((unknown, stale), ([], ['DS-08']))


class ProvenanceIndex(unittest.TestCase):
    def test_a_delivery_imported_under_another_name_is_found(self):
        class PK:
            files = {'/Game/P/SK_Pig_Photoreal': 1, '/Game/C/SK_Pig': 1, '/Game/R/SM_Fireplace_V4': 1}
            def import_sources(self, g):
                return {'/Game/P/SK_Pig_Photoreal': ['PhotorealPass/Creatures/Pig/Export/SK_Pig_LOD0.fbx'],
                        '/Game/C/SK_Pig': ['Creatures/Pig/Export/SK_Pig_LOD0.fbx'],
                        '/Game/R/SM_Fireplace_V4': ['Refinements/FiredClayV4/FBX/SM_Fireplace_Other.fbx']}[g]
        pk = PK()
        d = A.delivery_detail(['Creatures/Pig', 'PhotorealPass/Creatures/Pig'], {'SK_Pig'}, pk)
        self.assertIn('PhotorealPass/Creatures/Pig imported as /Game/P/SK_Pig_Photoreal', d)
        self.assertIn('Creatures/Pig imported as /Game/C/SK_Pig', d)
        d = A.delivery_detail(['Refinements/FiredClayV4', 'Refinements/Old'], {'SM_Contact'}, pk)
        self.assertIn('delivery is the import source of /Game/R/SM_Fireplace_V4', d)   # keep it
        self.assertIn('Refinements/Old: not imported (no package records it)', d)


class InCommit(unittest.TestCase):
    def test_bound_at_the_commit_by_its_root(self):
        A._COMMIT_CACHE['c0ffee'] = ({'/Game/A/SM_Old', '/Game/A/MI_Old', '/Game/A/SM_New'}, {'/Game/A/SM_Old': {'f.json'}})
        A.ROOT_OF.update({'/Game/A/MI_Old': '/Game/A/SM_Old', '/Game/A/SM_New': '/Game/A/SM_New'})
        via = {'/Game/A/SM_Old': 'f.json', '/Game/A/MI_Old': 'via SM_Old (f.json)', '/Game/A/SM_New': 'g.json'}
        self.assertTrue(A.in_commit('/Game/A/MI_Old', 'c0ffee', via))      # reached from a root bound there
        self.assertFalse(A.in_commit('/Game/A/SM_New', 'c0ffee', via))     # existed but not bound there
        self.assertFalse(A.in_commit('/Game/A/SM_Gone', 'c0ffee', via))    # did not exist
        self.assertTrue(A.in_commit('/Game/A/SM_New', 'c0ffee', via, {'/Game/A/SM_New': {'g.json', 'world map L_X'}}))



class AuditSkips(unittest.TestCase):
    def test_damaged_and_zero_filled_lines_are_counted(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'audit.jsonl'
            f.write_bytes(b'{"screen":1,"prims":[]}\n{"screen":595,"prims":[{"o"\x00\x00\x00\n'
                          b'\x00\x00\x00\x00\n\x01garbage\n{"screen":3,"prims":[]}\n\x00\x00\x00\x00')  # EOF padding
            screens = A.captured_screens(str(f))
            self.assertEqual(screens, {1, 3})
            self.assertEqual(A.AUDIT_SKIPPED, [595, None, None])
            self.assertEqual((A.AUDIT_STATS['damaged_with_header'], A.AUDIT_STATS['damaged_no_header'],
                              A.AUDIT_STATS['nul_only'], A.AUDIT_STATS['parsed']), (1, 1, 1, 2))
            self.assertEqual(A.AUDIT_STATS['eof_padding'], 1)       # zero fill after the last newline is no lost line


class CommitEvidence(unittest.TestCase):
    def test_unavailable_commit_answers_unknown(self):
        A._COMMIT_CACHE['badc0de'] = ({'/Game/A/SM_X'}, {'/Game/A/SM_X': {'f.json'}})
        A.COMMIT_UNAVAILABLE.add('badc0de')
        try:
            self.assertFalse(A.in_commit('/Game/A/SM_X', 'badc0de', {'/Game/A/SM_X': 'f.json'}))
        finally:
            A.COMMIT_UNAVAILABLE.discard('badc0de')
        self.assertTrue(A.in_commit('/Game/A/SM_X', 'badc0de', {'/Game/A/SM_X': 'f.json'}))



class CommitAbsence(unittest.TestCase):
    """Review of #171: a package absent at the evidence commit is never 'present'."""

    def setUp(self):
        A._COMMIT_CACHE['abc123'] = ({'/Game/A/SM_Root'}, {'/Game/A/SM_Root': {'f.json'}})
        A.ROOT_OF.update({'/Game/A/MI_New': '/Game/A/SM_Root', '/Game/A/SM_Map': '/Game/A/SM_Map'})

    def test_absent_package_reached_from_a_world_map_is_not_present(self):
        via = {'/Game/A/SM_Map': 'world map L_X'}
        self.assertFalse(A.in_commit('/Game/A/SM_Map', 'abc123', via, {'/Game/A/SM_Map': {'world map L_X'}}))

    def test_absent_package_whose_root_existed_is_not_present(self):
        via = {'/Game/A/SM_Root': 'f.json', '/Game/A/MI_New': 'via SM_Root (f.json)'}
        self.assertFalse(A.in_commit('/Game/A/MI_New', 'abc123', via))
        self.assertTrue(A.in_commit('/Game/A/SM_Root', 'abc123', via))


class GitFailures(unittest.TestCase):
    def test_a_failing_git_show_marks_the_commit_unavailable(self):
        real = A.subprocess.run

        class R:
            def __init__(self, rc, out=''):
                self.returncode, self.stdout, self.stderr = rc, out, ''

        def fake(cmd, **kw):
            if 'cat-file' in cmd or 'rev-parse' in cmd:
                return R(0, '')
            if 'ls-tree' in cmd:
                return R(0, 'Content/Dink/Data/Art/x.json\n')
            return R(128)                       # git show: missing blob
        A.subprocess.run = fake
        try:
            A._COMMIT_CACHE.pop('deadbeef', None)
            A.commit_roots('deadbeef')
            self.assertIn('deadbeef', A.COMMIT_UNAVAILABLE)
            self.assertIn('unavailable', A.after_commit_note('deadbeef', 'cook'))
        finally:
            A.subprocess.run = real
            A.COMMIT_UNAVAILABLE.discard('deadbeef')
            A._COMMIT_CACHE.pop('deadbeef', None)


class StaleWording(unittest.TestCase):
    def test_removed_never_and_unknown_are_worded_apart(self):
        w = A.stale_wording(['DS-77'], ['GP-Q9'], {'GP-Q9'})
        self.assertIn('never existed', w['DS-77'])
        self.assertIn('was removed', w['GP-Q9'])
        self.assertIn('history unknown', A.stale_wording(['GP-Q9'], [], None)['GP-Q9'])


if __name__ == '__main__':
    unittest.main()
