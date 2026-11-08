#!/usr/bin/env python3
"""Self-test for the Blender asset pipeline. Runs headless Blender for every step.

    cd tools/blender && python3 run_tests.py            # all tests
    python3 run_tests.py -v                              # verbose
    python3 run_tests.py Pipeline.test_06_export         # one test
    BLENDER=/path/to/blender python3 run_tests.py        # another Blender binary

Needs: Blender 5.x on PATH (or $BLENDER), Python 3 standard library only.
Work files go to tools/blender/out/tests (ignored by git).

What the tests establish (and what they cannot): see README.md "Verified vs not verified".
Everything here is checked in Blender and by reading the exported files; nothing is imported
into Unreal.
"""
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dinkasset import conventions as C  # noqa: E402
from dinkasset import fbxparse  # noqa: E402

BLENDER = os.environ.get("BLENDER") or shutil.which("blender") or "blender"
DINK = os.path.join(HERE, "dinkasset")
TESTS = os.path.join(HERE, "tests")
WORK = os.path.join(HERE, "out", "tests")
BEGIN, END = "@@DINK_REPORT_BEGIN@@", "@@DINK_REPORT_END@@"
MEASURED = {}   # printed at the end: round-trip measurements


class Result:
    def __init__(self, code, out):
        self.code = code
        self.out = out
        self.report = None
        if BEGIN in out and END in out:
            self.report = json.loads(out[out.index(BEGIN) + len(BEGIN):out.index(END)])


def blender(script, *args, timeout=600):
    cmd = [BLENDER, "-b", "--factory-startup", "-P", script, "--"] + [str(a) for a in args]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    return Result(p.returncode, p.stdout)


def tool(name, *args):
    return blender(os.path.join(DINK, name + ".py"), *args)


def w(*parts):
    return os.path.join(WORK, *parts)


def codes(result, asset=None):
    """{asset name: {code: [findings]}} from a validate report (or validation sub-report)."""
    rep = result.report.get("validation", result.report)
    out = {}
    for a in rep["assets"]:
        d = {}
        for f in a["findings"]:
            d.setdefault(f["code"], []).append(f)
        out[a["name"]] = d
    return out


def errors(result, name):
    rep = result.report.get("validation", result.report)
    for a in rep["assets"]:
        if a["name"] == name:
            return {f["code"] for f in a["findings"] if f["severity"] == "error"}
    raise KeyError(name)


def near(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def glb_accessors(path):
    """Parse a .glb with the stdlib: returns (json, {mesh name: {POSITION min/max}})."""
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and version == 2
    clen, ctype = struct.unpack_from("<II", data, 12)
    assert ctype == 0x4E4F534A
    js = json.loads(data[20:20 + clen])
    meshes = {}
    for m in js["meshes"]:
        for prim in m["primitives"]:
            acc = js["accessors"][prim["attributes"]["POSITION"]]
            cur = meshes.get(m["name"])
            if cur is None:   # a mesh with several materials has several primitives: take the union
                meshes[m["name"]] = {"min": list(acc["min"]), "max": list(acc["max"])}
            else:
                cur["min"] = [min(a, b) for a, b in zip(cur["min"], acc["min"])]
                cur["max"] = [max(a, b) for a, b in zip(cur["max"], acc["max"])]
    return js, meshes


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(WORK, ignore_errors=True)
        os.makedirs(WORK)

    # --- 01 build ---------------------------------------------------------------------------
    def test_01_build_test_assets(self):
        r = blender(os.path.join(TESTS, "build_assets.py"), "--out", WORK)
        self.assertEqual(r.code, 0, r.out[-2000:])
        for f in ("good.blend", "broken.blend", "units_cm.blend"):
            self.assertTrue(os.path.exists(w(f)), f)
        r = blender(os.path.join(TESTS, "make_inputs.py"), "--out", w("inputs"))
        self.assertEqual(r.code, 0, r.out[-2000:])
        for f in ("gen_barrel.obj", "gen_barrel.glb", "gen_barrel.fbx", "gen_barrel_lying.obj"):
            self.assertTrue(os.path.exists(w("inputs", f)), f)

    # --- 02 validate ------------------------------------------------------------------------
    def test_02_validate_good_needs_only_collision_and_lods(self):
        r = tool("validate", "--blend", w("good.blend"))
        self.assertEqual(r.code, 1)
        self.assertFalse(r.report["passed"])
        self.assertEqual(errors(r, "SM_Barrel_01"), {"COLLISION_MISSING"})
        self.assertEqual(errors(r, "SM_Wall_Door_2m_01"), {"COLLISION_MISSING"})
        self.assertEqual(errors(r, "SK_Test_Worm"), {"LOD_MISSING"})
        # no warnings on a clean asset
        self.assertEqual(r.report["summary"]["warnings"], 0, r.report["summary"])

    def test_03_validate_broken_fails_for_the_right_reasons(self):
        r = tool("validate", "--blend", w("broken.blend"))
        self.assertEqual(r.code, 1)
        self.assertFalse(r.report["passed"])
        old = errors(r, "Barrel old")
        for code in ("NAME_ASSET", "NAME_PREFIX", "NAME_OBJECT", "NAME_MATERIAL", "TRANSFORM_UNAPPLIED",
                     "PIVOT", "NORMALS_INVERTED", "COLLISION_MISSING"):
            self.assertIn(code, old)
        allc = codes(r)
        self.assertIn("LOOSE_GEOMETRY", allc["Barrel old"])
        self.assertIn("DUPLICATE_VERTS", allc["Barrel old"])
        nouv = errors(r, "SM_NoUv_01")
        for code in ("UV_MISSING", "SLOTS_OVER", "TRIS_OVER_BUDGET", "PIVOT"):
            self.assertIn(code, nouv)
        wall = errors(r, "SM_Wall_Wrong_01")
        self.assertIn("SNAP", wall)
        self.assertIn("PIVOT", wall)
        huge = codes(r)["SM_Huge_01"]["SCALE_RANGE"][0]
        self.assertIn("centimetres", huge["message"])
        self.assertIn("NEGATIVE_SCALE", errors(r, "SM_Mirror_01"))
        self.assertIn("UV_OVERLAP", errors(r, "SM_Stacked_01"))
        self.assertTrue({"NON_MANIFOLD", "ZERO_AREA"} <= errors(r, "SM_Open_01"), errors(r, "SM_Open_01"))
        self.assertNotIn("UV_OVERLAP", errors(r, "SM_Mirror_01"), "non-overlapping unwrap must not be flagged")
        # the well-formed ones in the same file are not blamed
        # (summary counts are consistent with the findings)
        n_err = sum(1 for a in r.report["assets"] for f in a["findings"] if f["severity"] == "error")
        self.assertEqual(r.report["summary"]["errors"], n_err + sum(1 for f in r.report["scene_findings"] if f["severity"] == "error"))

    def test_04_validate_units_and_usage_errors(self):
        r = tool("validate", "--blend", w("units_cm.blend"))
        self.assertEqual(r.code, 1)
        self.assertTrue(any(f["code"] == "SCENE_UNITS" for f in r.report["scene_findings"]))
        r = tool("validate", "--blend", w("does_not_exist.blend"))
        self.assertEqual(r.code, 2)
        self.assertTrue(r.report and "fatal" in r.report)

    def test_05_validate_skeleton_rules(self):
        r = tool("fix", "--blend", w("good.blend"), "--collection", "SK_Test_Worm", "--set-class", "character_humanoid",
                 "--output", w("worm_as_humanoid.blend"))
        self.assertEqual(r.code, 0, r.out[-1500:])
        r = tool("validate", "--blend", w("worm_as_humanoid.blend"), "--collection", "SK_Test_Worm")
        self.assertIn("SKELETON_BONES", errors(r, "SK_Test_Worm"))
        self.assertIn("LOD_MISSING", errors(r, "SK_Test_Worm"))

    # --- 06 fix ------------------------------------------------------------------------------
    def test_06_fix_is_opt_in_and_repairs_what_it_claims(self):
        # no flags: nothing changes
        r = tool("fix", "--blend", w("broken.blend"), "--collection", "Barrel old", "--output", w("noop.blend"))
        self.assertEqual(r.code, 0)
        self.assertEqual(r.report["fixes"], [])
        # real fix
        r = tool("fix", "--blend", w("broken.blend"), "--collection", "Barrel old", "--all-safe", "--rename",
                 "--output", w("broken_fixed.blend"), "--validate")
        self.assertEqual(r.report["ok"], True)
        names = {f["fix"] for f in r.report["fixes"]}
        for fx in ("apply_transforms", "merge_distance", "remove_loose", "recalc_normals", "set_pivot", "rename"):
            self.assertIn(fx, names)
        v = tool("validate", "--blend", w("broken_fixed.blend"), "--collection", "SM_Barrel_Old")
        self.assertEqual(errors(v, "SM_Barrel_Old"), {"COLLISION_MISSING"})
        b = v.report["assets"][0]["bounds"]
        self.assertTrue(near(b["size_cm"], [62.0, 77.0, 90.0], 0.3), b["size_cm"])
        self.assertTrue(abs(b["blender_min_cm"][2]) < 0.1, "pivot at the base")
        # the cm-authored scene and the other broken classes
        r = tool("fix", "--blend", w("units_cm.blend"), "--fix-units", "--output", w("units_fixed.blend"))
        self.assertEqual(r.code, 0)
        v = tool("validate", "--blend", w("units_fixed.blend"))
        self.assertFalse(v.report["scene_findings"], v.report["scene_findings"])
        self.assertTrue(near(v.report["assets"][0]["bounds"]["size_cm"], [62, 77, 90], 0.3))
        r = tool("fix", "--blend", w("broken.blend"), "--collection", "SM_Huge_01", "--apply-transforms", "--height", "0.9",
                 "--set-pivot", "--output", w("huge_fixed.blend"))
        v = tool("validate", "--blend", w("huge_fixed.blend"), "--collection", "SM_Huge_01")
        self.assertNotIn("SCALE_RANGE", errors(v, "SM_Huge_01"))
        self.assertNotIn("PIVOT", errors(v, "SM_Huge_01"))
        r = tool("fix", "--blend", w("broken.blend"), "--collection", "SM_Mirror_01", "--apply-transforms", "--recalc-normals",
                 "--output", w("mirror_fixed.blend"))
        v = tool("validate", "--blend", w("mirror_fixed.blend"), "--collection", "SM_Mirror_01")
        self.assertNotIn("NEGATIVE_SCALE", errors(v, "SM_Mirror_01"))
        self.assertNotIn("NORMALS_INCONSISTENT", errors(v, "SM_Mirror_01"))
        self.assertNotIn("NORMALS_INVERTED", errors(v, "SM_Mirror_01"))
        r = tool("fix", "--blend", w("broken.blend"), "--collection", "SM_Open_01", "--remove-degenerate", "--remove-loose",
                 "--output", w("open_fixed.blend"))
        v = tool("validate", "--blend", w("open_fixed.blend"), "--collection", "SM_Open_01")
        self.assertNotIn("ZERO_AREA", errors(v, "SM_Open_01"))
        self.assertIn("NON_MANIFOLD", errors(v, "SM_Open_01"), "fix must not pretend to close holes")
        r = tool("fix", "--blend", w("broken.blend"), "--collection", "SM_NoUv_01", "--add-uvs", "--prune-slots",
                 "--output", w("nouv_fixed.blend"))
        v = tool("validate", "--blend", w("nouv_fixed.blend"), "--collection", "SM_NoUv_01")
        self.assertNotIn("UV_MISSING", errors(v, "SM_NoUv_01"))

    # --- 07 LODs and collision -----------------------------------------------------------------
    def test_07_lods_and_collision(self):
        r = tool("make_lods", "--blend", w("good.blend"), "--output", w("good_lod.blend"), "--lods", "--collision")
        self.assertEqual(r.code, 0, r.out[-2000:])
        by = {a["asset"]: a["log"] for a in r.report["assets"]}
        # Nanite prop: no LOD chain unless forced
        self.assertTrue(any(e["action"] == "skip" and "Nanite" in e["why"] for e in by["SM_Barrel_01"]))
        lods = [e for e in by["SK_Test_Worm"] if e["action"] == "lod"]
        self.assertEqual([e["name"] for e in lods], ["SK_Test_Worm_LOD1", "SK_Test_Worm_LOD2", "SK_Test_Worm_LOD3"])
        for e, want in zip(lods, C.LOD_RATIOS_SKELETAL):
            self.assertAlmostEqual(e["ratio_achieved"], want, delta=0.04, msg=e)
        self.assertEqual(sum(1 for e in by["SM_Barrel_01"] if e["action"] == "collision"), 1)
        walls = [e for e in by["SM_Wall_Door_2m_01"] if e["action"] == "collision"]
        self.assertEqual(len(walls), 3, walls)
        for e in by["SM_Barrel_01"] + walls:
            if e["action"] == "collision":
                self.assertLessEqual(e["vertices"], C.COLLISION_MAX_HULL_VERTS)
        v = tool("validate", "--blend", w("good_lod.blend"))
        self.assertEqual(v.code, 0, json.dumps(v.report["summary"]) + v.out[-1500:])
        self.assertTrue(v.report["passed"])
        self.assertEqual(v.report["assets"][2]["tris_per_lod"].keys(), {"LOD0", "LOD1", "LOD2", "LOD3"})
        tr = v.report["assets"][2]["tris_per_lod"]
        self.assertTrue(tr["LOD0"] > tr["LOD1"] > tr["LOD2"] > tr["LOD3"], tr)
        # the door opening must stay open, the wall columns and lintel must be solid
        p = blender(os.path.join(TESTS, "probe_collision.py"), "--blend", w("good_lod.blend"), "--asset", "SM_Wall_Door_2m_01",
                    "--points", "1.0,0,1.0;1.0,0,2.0;0.25,0,1.0;1.75,0,1.0;1.0,0,3.0;0.25,0,3.4")
        hit = [bool(x["hulls"]) for x in p.report["points"]]
        self.assertEqual(hit, [False, False, True, True, True, True], p.report["points"])
        # re-running without --replace leaves existing collision alone
        r2 = tool("make_lods", "--blend", w("good_lod.blend"), "--output", w("good_lod2.blend"), "--collision")
        self.assertTrue(all(e["action"] == "skip" for a in r2.report["assets"] for e in a["log"]))

    # --- 08 export ---------------------------------------------------------------------------------
    def test_08_export_files_and_manifest(self):
        out = w("export")
        r = tool("export_ue", "--blend", w("good_lod.blend"), "--out", out)
        self.assertEqual(r.code, 0, r.out[-2000:])
        want = {"SM_Barrel_01": "Props", "SM_Wall_Door_2m_01": "Kits", "SK_Test_Worm": "Creatures"}
        for name, folder in want.items():
            for ext in (".fbx", ".glb"):
                self.assertTrue(os.path.exists(os.path.join(out, "Game", "Dink", folder, "Test", name + ext)), name + ext)
        with open(os.path.join(out, "manifest.json")) as f:
            man = json.load(f)
        self.assertEqual(man["schema_version"], 1)
        ents = {e["name"]: e for e in man["assets"]}
        self.assertEqual(set(ents), set(want))
        barrel = ents["SM_Barrel_01"]
        self.assertEqual(barrel["content_path"], "/Game/Dink/Props/Test/SM_Barrel_01")
        self.assertEqual(barrel["class"], "prop")
        self.assertTrue(barrel["nanite"])
        self.assertEqual(barrel["tris"], {"LOD0": 344})
        self.assertTrue(near(barrel["bounds_cm"]["size_cm"], [62, 77, 90], 0.2))
        self.assertTrue(near(barrel["bounds_cm"]["unreal_max_cm"], [31, 46, 90], 0.2))
        self.assertEqual(barrel["collision"], ["UCX_SM_Barrel_01_01"])
        with open(w("good_lod.blend"), "rb") as f:
            self.assertEqual(barrel["source"]["sha256"], hashlib.sha256(f.read()).hexdigest())
        worm = ents["SK_Test_Worm"]
        self.assertFalse(worm["nanite"])
        self.assertEqual(worm["lod_count"], 4)
        self.assertEqual(list(worm["tris"]), ["LOD0", "LOD1", "LOD2", "LOD3"])
        self.assertEqual(worm["skeleton"]["bones"], 4)
        wall = ents["SM_Wall_Door_2m_01"]
        self.assertTrue(near(wall["bounds_cm"]["size_cm"], [200, 20, 350], 0.2))
        self.assertTrue(near(wall["bounds_cm"]["blender_min_cm"], [0, -10, 0], 0.2), "wall pivot: grid corner, centre line, floor")
        MEASURED["manifest_sizes_cm"] = {n: e["bounds_cm"]["size_cm"] for n, e in ents.items()}

    def test_09_fbx_file_contents(self):
        """Read the FBX bytes (not Blender's importer): units, axes, node transforms, extents."""
        out = w("export", "Game", "Dink")
        facts = {}
        for rel, name in (("Props/Test", "SM_Barrel_01"), ("Kits/Test", "SM_Wall_Door_2m_01"), ("Creatures/Test", "SK_Test_Worm")):
            info = fbxparse.inspect(os.path.join(out, rel, name + ".fbx"))
            self.assertEqual(info["unit_scale_factor"], 100.0, "FBX unit header must be metres (100 cm per unit)")
            self.assertEqual(info["up_axis"], [2, 1], "Z up")
            self.assertEqual(info["front_axis"], [1, -1], "front -Y, i.e. Blender's own frame, no rotation baked")
            self.assertEqual(info["coord_axis"], [0, 1])
            for mname, m in info["models"].items():
                if m["type"] == "Mesh":
                    self.assertEqual(m["scaling"], [1, 1, 1], mname)
                    self.assertEqual(m["rotation"], [0, 0, 0], mname)
                    self.assertEqual(m["translation"], [0, 0, 0], mname + ": asset must be exported at the origin")
            facts[name] = info
        barrel = facts["SM_Barrel_01"]["models"]["SM_Barrel_01"]
        self.assertTrue(near(barrel["size_cm"], [62, 77, 90], 0.2), barrel["size_cm"])
        self.assertAlmostEqual(barrel["min_cm"][2], 0.0, delta=0.05)
        self.assertAlmostEqual(barrel["min_cm"][1], -46.0, delta=0.1, msg="tap (front) stays on -Y in the file")
        self.assertIn("UCX_SM_Barrel_01_01", facts["SM_Barrel_01"]["models"])
        wall = facts["SM_Wall_Door_2m_01"]["models"]
        self.assertEqual(sum(1 for n in wall if n.startswith("UCX_SM_Wall_Door_2m_01_")), 3)
        self.assertAlmostEqual(wall["SM_Wall_Door_2m_01"]["min_cm"][0], 0.0, delta=0.05)
        self.assertEqual(facts["SM_Wall_Door_2m_01"]["models"]["SM_Wall_Door_2m_01"]["tris"], 28, "triangulated on export")
        worm = facts["SK_Test_Worm"]["models"]
        self.assertEqual([n for n in worm if n.startswith("SK_Test_Worm_LOD")], ["SK_Test_Worm_LOD%d" % i for i in range(4)])
        self.assertIn("root", worm)
        MEASURED["fbx_header"] = {n: (f["unit_scale_factor"], f["up_axis"], f["front_axis"]) for n, f in facts.items()}

    def test_10_gltf_file_contents(self):
        out = w("export", "Game", "Dink")
        js, meshes = glb_accessors(os.path.join(out, "Props/Test/SM_Barrel_01.glb"))
        mn, mx = meshes["SM_Barrel_01"]["min"], meshes["SM_Barrel_01"]["max"]
        # glTF: metres, Y up, +Z forward. Blender (x, y, z) -> glTF (x, z, -y).
        self.assertTrue(near([mx[i] - mn[i] for i in range(3)], [0.62, 0.90, 0.77], 0.002), (mn, mx))
        self.assertAlmostEqual(mn[1], 0.0, delta=0.001)
        self.assertAlmostEqual(mx[2], 0.46, delta=0.002, msg="Blender front (-Y) marker is +Z in glTF")
        self.assertEqual(len(js["meshes"]), 1, "glTF carries LOD0 only, no collision")
        js, meshes = glb_accessors(os.path.join(out, "Creatures/Test/SK_Test_Worm.glb"))
        self.assertEqual(list(meshes), ["SK_Test_Worm_LOD0"])
        self.assertIn("skins", js)
        MEASURED["glb_barrel_extent_m"] = [round(mx[i] - mn[i], 4) for i in range(3)]

    def test_11_roundtrip_reimport_dimensions(self):
        """Re-import both formats into Blender: sizes in cm must match the manifest, front must stay -Y."""
        out = w("export", "Game", "Dink")
        res = {}
        for fmt in ("fbx", "glb"):
            r = blender(os.path.join(TESTS, "roundtrip.py"), "--file", os.path.join(out, "Props/Test/SM_Barrel_01." + fmt))
            self.assertEqual(r.code, 0, r.out[-1500:])
            meshes = {m["name"].split(".")[0]: m for m in r.report["meshes"]}
            b = meshes["SM_Barrel_01"]
            self.assertTrue(near(b["size_cm"], [62, 77, 90], 0.5), (fmt, b["size_cm"]))
            self.assertAlmostEqual(b["min_cm"][1], -46.0, delta=0.5, msg=fmt + ": front marker must come back on -Y")
            self.assertAlmostEqual(b["min_cm"][2], 0.0, delta=0.5)
            res[fmt] = b["size_cm"]
            if fmt == "fbx":
                self.assertIn("UCX_SM_Barrel_01_01", meshes)
        MEASURED["roundtrip_barrel_size_cm"] = res
        # wall: collision count and pivot survive
        r = blender(os.path.join(TESTS, "roundtrip.py"), "--file", os.path.join(out, "Kits/Test/SM_Wall_Door_2m_01.fbx"))
        meshes = {m["name"].split(".")[0]: m for m in r.report["meshes"]}
        self.assertTrue(near(meshes["SM_Wall_Door_2m_01"]["size_cm"], [200, 20, 350], 0.5))
        self.assertAlmostEqual(meshes["SM_Wall_Door_2m_01"]["min_cm"][0], 0.0, delta=0.5)
        self.assertEqual(sum(1 for n in meshes if n.startswith("UCX_")), 3)
        # skinned creature: mesh size and bone chain
        r = blender(os.path.join(TESTS, "roundtrip.py"), "--file", os.path.join(out, "Creatures/Test/SK_Test_Worm.fbx"))
        meshes = {m["name"].split(".")[0]: m for m in r.report["meshes"]}
        self.assertTrue(near(meshes["SK_Test_Worm_LOD0"]["size_cm"], [24, 24, 120], 1.0), meshes["SK_Test_Worm_LOD0"]["size_cm"])
        bones = {b["name"].split(".")[0]: b for b in r.report["armatures"][0]["bones"]}
        for n, z in (("root", 0.0), ("spine_01", 20.0), ("spine_02", 60.0), ("head", 100.0)):
            self.assertIn(n, bones)
            self.assertTrue(near(bones[n]["head_cm"], [0.0, 0.0, z], 0.5), (n, bones[n]["head_cm"]))
        top = bones["head"]["head_cm"][2]
        MEASURED["roundtrip_worm_size_cm"] = meshes["SK_Test_Worm_LOD0"]["size_cm"]
        MEASURED["roundtrip_worm_head_bone_z_cm"] = top

    def test_12_export_rejects_failing_assets_and_merges_manifest(self):
        out = w("export")
        r = tool("export_ue", "--blend", w("broken.blend"), "--out", out, "--collection", "SM_Huge_01", "--formats", "fbx")
        self.assertEqual(r.code, 1)
        self.assertEqual(r.report["exported"], [])
        self.assertEqual(r.report["rejected"][0]["name"], "SM_Huge_01")
        self.assertFalse(os.path.exists(os.path.join(out, "Game", "Dink", "Props", "Test", "SM_Huge_01.fbx")))
        # second blend into the same tree: manifest is merged by asset name
        r = tool("make_lods", "--blend", w("broken_fixed.blend"), "--output", w("fixed_ready.blend"), "--collection", "SM_Barrel_Old", "--collision")
        self.assertEqual(r.code, 0, r.out[-1500:])
        r = tool("export_ue", "--blend", w("fixed_ready.blend"), "--out", out, "--collection", "SM_Barrel_Old", "--formats", "fbx")
        self.assertEqual(r.code, 0, r.out[-1500:])
        with open(os.path.join(out, "manifest.json")) as f:
            names = [e["name"] for e in json.load(f)["assets"]]
        self.assertEqual(sorted(names), ["SK_Test_Worm", "SM_Barrel_01", "SM_Barrel_Old", "SM_Wall_Door_2m_01"])

    # --- 13 import_generated --------------------------------------------------------------------------
    def test_13_import_generated(self):
        sizes = {}
        for fname in ("gen_barrel.obj", "gen_barrel.glb", "gen_barrel.fbx"):
            out = w("imported_%s.blend" % fname)
            r = tool("import_generated", "--input", w("inputs", fname), "--name", "SM_Gen_Barrel_01", "--class", "prop",
                     "--height", "0.9", "--out", out, "--source", "unit test")
            self.assertEqual(r.code, 0, fname + r.out[-2500:])
            self.assertTrue(r.report["compliant"], fname)
            a = r.report["validation"]["assets"][0]
            self.assertTrue(near(a["bounds"]["size_cm"], [62, 77, 90], 0.5), (fname, a["bounds"]["size_cm"]))
            self.assertAlmostEqual(a["bounds"]["blender_min_cm"][2], 0.0, delta=0.1)
            sizes[fname] = a["bounds"]["size_cm"]
            v = tool("validate", "--blend", out)
            self.assertEqual(v.code, 0, fname)
        MEASURED["import_generated_size_cm"] = sizes
        # a lying generator output needs --rotate; the height is then taken from the corrected Z
        r = tool("import_generated", "--input", w("inputs", "gen_barrel_lying.obj"), "--name", "SM_Gen_Lying_01", "--class", "prop",
                 "--height", "0.9", "--rotate", "0", "90", "0", "--out", w("imported_lying.blend"))
        self.assertEqual(r.code, 0, r.out[-2000:])
        sz = r.report["validation"]["assets"][0]["bounds"]["size_cm"]
        self.assertTrue(near(sz, [62, 77, 90], 1.0), sz)

    def test_14_over_budget_import_is_decimated(self):
        r = tool("import_generated", "--input", w("inputs", "gen_dense.glb"), "--name", "SM_Gen_Dense_01", "--class", "prop",
                 "--height", "1.0", "--out", w("imported_dense.blend"))
        self.assertEqual(r.code, 0, r.out[-2500:])
        a = r.report["validation"]["assets"][0]
        tris = a["tris_per_lod"]["LOD0"]
        self.assertLessEqual(tris, C.CLASSES["prop"]["tris"][1])
        self.assertTrue(any(f["fix"] == "decimate" for f in r.report["fixes"]))
        MEASURED["dense_import_tris"] = tris
        r = tool("import_generated", "--input", w("inputs", "gen_dense.glb"), "--name", "SM_Gen_Dense_02", "--class", "prop",
                 "--height", "1.0", "--no-decimate", "--out", w("imported_dense2.blend"))
        self.assertEqual(r.code, 1, "without decimation the import must report non-compliance")
        self.assertIn("TRIS_OVER_BUDGET", errors(r, "SM_Gen_Dense_02"))

    # --- 15 docs --------------------------------------------------------------------------------------------
    def test_15_docs_match_code(self):
        with open(os.path.join(HERE, "CONVENTIONS.md")) as f:
            conv = f.read()
        sys.path.insert(0, HERE)
        import gen_class_table
        table = gen_class_table.render()
        self.assertIn(table, conv, "class table in CONVENTIONS.md is stale: run python3 gen_class_table.py --write")
        for name in C.CLASSES:
            self.assertIn("`%s`" % name, conv, name)
        for key in (C.META_CLASS, C.META_PATH, C.META_NANITE, C.META_TEX_PX, C.META_TRANSLUCENT):
            self.assertIn(key, conv)
        with open(os.path.join(HERE, "README.md")) as f:
            readme = f.read()
        for script in ("validate.py", "fix.py", "make_lods.py", "export_ue.py", "import_generated.py", "run_tests.py"):
            self.assertIn(script, readme)

    def test_16_tmp_files_ignored(self):
        with open(os.path.join(HERE, ".gitignore")) as f:
            g = f.read()
        self.assertIn("out/", g)
        self.assertIn("*.blend1", g)


def main():
    if not shutil.which(BLENDER) and not os.path.exists(BLENDER):
        print("Blender not found: install it or set $BLENDER", file=sys.stderr)
        return 2
    prog = unittest.main(module=__name__, exit=False, argv=[sys.argv[0]] + sys.argv[1:])
    print("\nRound-trip measurements:")
    print(json.dumps(MEASURED, indent=1))
    return 0 if prog.result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
