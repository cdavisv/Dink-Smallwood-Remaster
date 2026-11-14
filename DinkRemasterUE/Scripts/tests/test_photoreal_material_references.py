"""Two faults that draw a mesh with the engine's grey default material, read from the package files.

1. Every package a material names must be in the repository.

A material whose texture parameter points at a deleted texture does not compile: Unreal logs "Failed to compile
Material ... Default Material will be used in game" and every mesh that uses an instance of it is drawn with the grey
default material, without its colour or normal map. That shipped once: the master material of the unclaimed-families
kit kept the textures of an asset that was removed before the merge, and all 34 of the kit's props lost their
materials in the game (found 13 Nov 2026).

2. A mesh that is drawn as instances needs "Used with Instanced Static Meshes" on its base materials.

Background placements, town-house modules, grass and ceilings are drawn by instanced components. Outside the editor a
base material without that usage flag is not compiled for them: "Material ... missing usage flag InstancedStaticMeshes!
Default Material will be used in game". That shipped too: the boulder rows of families.json bound the old kit boulder,
whose material has no flag, and the background boulders were grey (found 13 Nov 2026). The kit importers set the flag;
hand-made materials may not have it.

Unit tests do not start the editor, so this reads the package files: the names a .uasset refers to, and the names of
the properties it stores (a flag that is set), are plain text in its name table.
"""
import json
import os
import re
import unittest

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTENT = os.path.join(PROJECT, "Content")
ROOT = os.path.join(CONTENT, "Dink")  # every material of the project; the generated world (git-ignored) has none of its own
REFERENCE = re.compile(rb"/Game/Dink/[A-Za-z0-9_/]+")
LFS_POINTER = b"version https://git-lfs.github.com/spec/"
ANY_REFERENCE = re.compile(rb"/Game/[A-Za-z0-9_/]+")
MESH_PATH = re.compile(r"/Game/[A-Za-z0-9_/]+/SM_[A-Za-z0-9_]+")
INSTANCED_FLAG = b"bUsedWithInstancedStaticMeshes"
ART = os.path.join(CONTENT, "Dink", "Data", "Art")
ENVIRONMENT = os.path.join(CONTENT, "Dink", "Data", "Environment", "environment.json")

# Family meshes whose base material has no flag and is pinned by a source contract (hash in the asset ledger), so it is
# not re-saved here. Allowed only because every 1997 placement of the row's classes is an actor card today (it carries
# a script or a hardbox the greybox keeps as an actor), and an actor is dressed with an ordinary mesh component:
# `python3 -I Scripts/art_coverage.py` lists them as "actor", never "instance". Rebind the row, or set the flag on the
# material, before one of these meshes is given to a class with background placements.
ACTOR_ONLY_FAMILY_MESHES = {
    "/Game/Dink/Kits/StonebrookExterior/SM_Fence_SplitRail_4m_01": "fence_rail_ew: 18 placements, all actors",
    "/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01": "barrel: 95 placements, all actors",
}


def package_file(game_path):
    return os.path.join(CONTENT, *game_path[len("/Game/"):].split("/"))


class PhotorealMaterialReferences(unittest.TestCase):
    def test_materials_name_only_packages_that_exist(self):
        missing, read = [], 0
        for folder, folders, files in os.walk(ROOT):
            folders[:] = sorted(f for f in folders if f != "_Generated")
            for name in sorted(files):
                if not (name.endswith(".uasset") and name.startswith(("M_", "MI_", "MPC_"))):
                    continue
                path = os.path.join(folder, name)
                with open(path, "rb") as handle:
                    data = handle.read()
                if data.startswith(LFS_POINTER):
                    continue  # a checkout without the binaries: nothing to read
                read += 1
                for ref in sorted({m.decode("ascii") for m in REFERENCE.findall(data)}):
                    target = package_file(ref)
                    if os.path.isfile(target + ".uasset") or os.path.isdir(target):
                        continue
                    # Unreal stores a name that ends in _<number> as the stem and the number: MI_Decal_BloodSplat_0 is "MI_Decal_BloodSplat" in the file
                    stem = os.path.basename(target) + "_"
                    if os.path.isdir(os.path.dirname(target)) and any(f.startswith(stem) and f[len(stem):-len(".uasset")].isdigit() for f in os.listdir(os.path.dirname(target)) if f.endswith(".uasset")):
                        continue
                    missing.append("%s -> %s" % (os.path.relpath(path, PROJECT), ref))
        if not read:
            self.skipTest("the materials are Git LFS pointers in this checkout")
        self.assertEqual(missing, [], "materials that name a package that is not in the repository (they will not compile):\n  " + "\n  ".join(missing))


def read_package(game_path, cache={}):
    """-> the package's bytes; None when it is missing or a Git LFS pointer."""
    if game_path not in cache:
        path = package_file(game_path) + ".uasset"
        data = None
        if os.path.isfile(path):
            with open(path, "rb") as handle:
                data = handle.read()
            if data.startswith(LFS_POINTER):
                data = None
        cache[game_path] = data
    return cache[game_path]


def is_material(game_path):
    return os.path.basename(game_path).startswith(("M_", "MI_"))


def material_references(game_path):
    data = read_package(game_path) or b""
    return sorted({m.decode("ascii") for m in ANY_REFERENCE.findall(data)} - {game_path})


def base_materials(game_path, seen=None):
    """The base materials a material or material instance compiles from (an instance names its parent)."""
    seen = set() if seen is None else seen
    data = read_package(game_path)
    if game_path in seen or data is None:
        return set()
    seen.add(game_path)
    if b"MaterialInstanceConstant" not in data:
        return {game_path}
    found = set()
    for ref in material_references(game_path):
        if is_material(ref):
            found |= base_materials(ref, seen)
    return found


def unflagged_base_materials(mesh):
    """-> (readable, [base materials of the mesh that lack the instanced-mesh usage flag])."""
    if read_package(mesh) is None:
        return False, []
    bad = set()
    for ref in material_references(mesh):
        if is_material(ref):
            bad |= {base for base in base_materials(ref) if INSTANCED_FLAG not in read_package(base)}
    return True, sorted(bad)


def meshes_named_in(path, only_under=None):
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as handle:
        found = set(MESH_PATH.findall(handle.read()))
    return {m for m in found if only_under is None or m.startswith(only_under)}


class InstancedMeshMaterialUsage(unittest.TestCase):
    """Meshes that the runtime draws through instanced components (DinkArtFamilySubsystem::DressInstances,
    UDinkEnvironmentSubsystem: town houses, structure sets, grass, ceilings, mesh swaps on instanced decor)."""

    def sources(self):
        yield "families.json", meshes_named_in(os.path.join(ART, "families.json")), ACTOR_ONLY_FAMILY_MESHES
        yield "town_houses.json", meshes_named_in(os.path.join(ART, "town_houses.json")), {}
        yield "structure_sets.json", meshes_named_in(os.path.join(ART, "structure_sets.json")), {}
        # environment.json also names the old kit meshes it swaps out: only the photoreal ones are drawn
        yield "environment.json", meshes_named_in(ENVIRONMENT, "/Game/Dink/Photoreal/"), {}

    def test_instanced_meshes_have_the_usage_flag_on_their_base_materials(self):
        problems, read = [], 0
        for source, meshes, allowed in self.sources():
            for mesh in sorted(meshes):
                readable, bad = unflagged_base_materials(mesh)
                read += readable
                if bad and mesh not in allowed:
                    problems.append("%s: %s -> %s" % (source, mesh, ", ".join(bad)))
        if not read:
            self.skipTest("the meshes are Git LFS pointers in this checkout")
        self.assertEqual(problems, [], "meshes drawn as instances whose base material lacks 'Used with Instanced Static Meshes' "
                         "(they are drawn with the grey default material in the game):\n  " + "\n  ".join(problems))

    def test_the_actor_only_exceptions_are_still_needed(self):
        bound = meshes_named_in(os.path.join(ART, "families.json"))
        for mesh, why in sorted(ACTOR_ONLY_FAMILY_MESHES.items()):
            readable, bad = unflagged_base_materials(mesh)
            if not readable:
                continue
            self.assertIn(mesh, bound, "%s is no longer bound by families.json: remove it from ACTOR_ONLY_FAMILY_MESHES" % mesh)
            self.assertTrue(bad, "%s (%s) has the usage flag now: remove it from ACTOR_ONLY_FAMILY_MESHES" % (mesh, why))


if __name__ == "__main__":
    unittest.main()
