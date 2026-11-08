"""Dink remaster asset conventions as data (no bpy import: usable from any Python).

CONVENTIONS.md explains the reasons; this file is the machine-readable copy that
validate.py, fix.py, make_lods.py, export_ue.py and import_generated.py share.
`gen_class_table.py` renders the class table in CONVENTIONS.md from CLASSES, and
run_tests.py fails if the document and this file drift apart.

Everything is in Blender metres unless a name says `_cm`.
"""
import re

SCHEMA_VERSION = 1

# --- Units, grid ------------------------------------------------------------
UNIT_TO_CM = 100.0          # 1 Blender unit (1 m) == 100 Unreal units (cm)
GRID_M = 2.0                # interior kit grid
SUBGRID_M = 0.5             # allowed sub-module
CEILING_M = 3.5             # interior storey height (floor top to ceiling underside)
SNAP_TOL_M = 0.01           # 1 cm tolerance for snapping/pivot checks
CONTENT_ROOT = "/Game/Dink"

# --- Naming -----------------------------------------------------------------
_TOKEN = r"[A-Z0-9][A-Za-z0-9]*"
ASSET_NAME_RE = re.compile(r"^(?P<prefix>SM|SK)_[A-Z][A-Za-z0-9]*(?:_%s)*$" % _TOKEN)
MATERIAL_NAME_RE = re.compile(r"^(?P<prefix>MI|M)_[A-Z][A-Za-z0-9]*(?:_%s)*$" % _TOKEN)
TEXTURE_SUFFIXES = ("BC", "N", "ORM", "E", "MSK", "H")
TEXTURE_NAME_RE = re.compile(r"^T_[A-Z][A-Za-z0-9]*(?:_%s)*_(?:%s)$" % (_TOKEN, "|".join(TEXTURE_SUFFIXES)))
LOD_RE = re.compile(r"^(?P<base>.+)_LOD(?P<n>\d+)$")
COLLISION_RE = re.compile(r"^(?P<kind>UCX|UBX|USP|UCP)_(?P<mesh>.+)_(?P<n>\d{2})$")
SOCKET_RE = re.compile(r"^SOCKET_[A-Za-z0-9_]+$")
MAX_NAME_LEN = 48

# Custom properties stored on the asset collection.
META_CLASS = "dink_class"          # key into CLASSES (required)
META_PATH = "dink_path"            # sub-folder under the class folder, e.g. "Tavern" (optional)
META_NANITE = "dink_nanite"        # "yes"/"no" override of the class policy (optional)
META_TEX_PX = "dink_tex_px"        # assumed texture size for the texel-density check (optional)
META_TRANSLUCENT = "dink_translucent"  # 1 = translucent material: forces Nanite off, LOD chain required
META_SOURCE = "dink_source"        # free text: where the mesh came from (generator, kit, ledger id)

# --- LOD policy ---------------------------------------------------------------
# Triangle ratio of each LOD relative to LOD0 (LOD1, LOD2, ...).
LOD_RATIOS_STANDARD = (0.5, 0.25, 0.10)
LOD_RATIOS_SKELETAL = (0.5, 0.25, 0.12)
LOD_MIN_TRIS = 24           # never decimate a LOD below this
LOD_MONOTONIC_SLACK = 0.98  # LODn+1 must have <= 98 % of LODn triangles

# --- Collision ------------------------------------------------------------------
COLLISION_MAX_HULL_VERTS = 32   # starting value, tune in editor (UE physics cooks any size)
COLLISION_HARD_MAX_VERTS = 255

# --- Skeletons ------------------------------------------------------------------
# Core bones every humanoid must have, using the UE5 Manny/Quinn names (lower-case,
# _l/_r side suffix). Source: memory of the UE5 mannequin skeleton: verify in editor
# by importing Manny and comparing (see CONVENTIONS.md).
_SIDE = ("l", "r")
HUMANOID_BONES = (
    ["root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
     "neck_01", "neck_02", "head"]
    + ["%s_%s" % (b, s) for s in _SIDE
       for b in ("clavicle", "upperarm", "lowerarm", "hand", "thigh", "calf", "foot", "ball")]
)
# The project quadruped skeleton is OUR definition (Unreal has no standard one).
QUADRUPED_BONES = (
    ["root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "neck_02", "head",
     "tail_01", "tail_02", "tail_03"]
    + ["%s_%s" % (b, s) for s in _SIDE
       for b in ("upperarm", "lowerarm", "hand", "thigh", "calf", "foot")]
)
SKELETONS = {"humanoid": HUMANOID_BONES, "quadruped": QUADRUPED_BONES, "custom": ("root",)}
SKELETON_ASSET = {"humanoid": "SK_Dink_Humanoid", "quadruped": "SK_Dink_Quadruped"}
MAX_BONE_INFLUENCES = 8       # hard limit; 4 preferred (Deck)
PREFERRED_BONE_INFLUENCES = 4
MAX_BONES_WARN = 256

# --- Asset classes ---------------------------------------------------------------
# pivot rules (see validate.pivot_expectation):
#   base_center  x,y = bounds centre, z = bounds min
#   grid_wall    bounds min x = 0, y centre = 0 (wall centre line on the grid line), min z = 0
#   grid_floor   bounds min x = min y = 0, max z = 0 (top surface is the floor level)
#   grid_ceiling bounds min x = min y = 0, min z = 0 (underside is the ceiling level)
#   grid_piece   min z = 0, origin inside the XY footprint
#   hinge        min x = 0 (hinge edge), y centre = 0, min z = 0
#   feet         min z = 0, x,y within pivot_xy of the bounds centre
#   grip         origin inside bounds and a SOCKET_Grip empty exists
CLASSES = {
    "prop_small": dict(
        kind="static", folder="Props", pivot="base_center", longest=(0.03, 0.6),
        tris=(1500, 5000), slots=2, collision=False, lods=0, lod_ratios=(0.5, 0.25),
        nanite="no", uv_overlap=False, manifold="error", texel=1024, tex_px=1024, tex_max=2048,
        texel_check=True,
        doc="Clutter and hand-sized props (mug, key, book). Nanite off: tiny meshes cost more in Nanite than they save."),
    "prop": dict(
        kind="static", folder="Props", pivot="base_center", longest=(0.3, 3.5),
        tris=(6000, 20000), slots=3, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=False, manifold="error", texel=512, tex_px=2048, tex_max=2048,
        texel_check=True,
        doc="Furniture-sized props (barrel, crate, chair, table, lamp)."),
    "prop_large": dict(
        kind="static", folder="Props", pivot="base_center", longest=(1.5, 10.0),
        tris=(20000, 60000), slots=4, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=False, manifold="error", texel=256, tex_px=4096, tex_max=4096,
        texel_check=True,
        doc="Large props and set pieces (wagon, statue, fountain, boat)."),
    "foliage": dict(
        kind="static", folder="Foliage", pivot="base_center", longest=(0.2, 25.0),
        tris=(8000, 25000), slots=3, collision=False, lods=3, lod_ratios=(0.5, 0.25, 0.10),
        nanite="no", uv_overlap=True, manifold="warning", texel=256, tex_px=2048, tex_max=2048,
        texel_check=False,
        doc="Trees, bushes, plants with masked leaf cards. Classic LOD chain; Nanite foliage is a verify-in-editor decision."),
    "kit_wall": dict(
        kind="static", folder="Kits", pivot="grid_wall", longest=(0.5, 8.0),
        tris=(2500, 8000), slots=2, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=True, manifold="error", texel=512, tex_px=2048, tex_max=4096,
        texel_check=False, snap=True, grid_axes="x", height_snap=True,
        doc="Modular wall segment on the 2 m grid, 3.5 m high, centre line on the grid line."),
    "kit_floor": dict(
        kind="static", folder="Kits", pivot="grid_floor", longest=(0.5, 8.0),
        tris=(1000, 4000), slots=2, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=True, manifold="error", texel=512, tex_px=2048, tex_max=4096,
        texel_check=False, snap=True, grid_axes="xy", height_snap=False,
        doc="Modular floor tile, top surface at z = 0."),
    "kit_ceiling": dict(
        kind="static", folder="Kits", pivot="grid_ceiling", longest=(0.5, 8.0),
        tris=(1000, 4000), slots=2, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=True, manifold="error", texel=512, tex_px=2048, tex_max=4096,
        texel_check=False, snap=True, grid_axes="xy", height_snap=False,
        doc="Modular ceiling tile or beam, underside at z = 0 (placed at 3.5 m)."),
    "kit_piece": dict(
        kind="static", folder="Kits", pivot="grid_piece", longest=(0.3, 8.0),
        tris=(3000, 10000), slots=3, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=True, manifold="error", texel=512, tex_px=2048, tex_max=4096,
        texel_check=False, snap=False,
        doc="Other kit parts: pillars, corners, stairs, arches, roof pieces. Origin on a grid vertex at floor level."),
    "door": dict(
        kind="static", folder="Kits", pivot="hinge", longest=(0.5, 3.5),
        tris=(4000, 12000), slots=3, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=False, manifold="error", texel=512, tex_px=2048, tex_max=2048,
        texel_check=True,
        doc="Door leaf or gate leaf: pivot at the hinge, closed, leaf extends along +X."),
    "building": dict(
        kind="static", folder="Buildings", pivot="base_center", longest=(4.0, 40.0),
        tris=(60000, 200000), slots=6, collision=True, lods=0, lod_ratios=(),
        nanite="yes", uv_overlap=True, manifold="warning", texel=256, tex_px=4096, tex_max=4096,
        texel_check=False,
        doc="Monolithic exterior buildings (not built from the interior kit)."),
    "weapon": dict(
        kind="static", folder="Items", pivot="grip", longest=(0.2, 2.5),
        tris=(3000, 8000), slots=3, collision=False, lods=0, lod_ratios=(0.5, 0.25),
        nanite="no", uv_overlap=False, manifold="error", texel=1024, tex_px=1024, tex_max=2048,
        texel_check=True, needs_socket="SOCKET_Grip",
        doc="Held items (sword, axe, bow, bomb). Origin at the grip, SOCKET_Grip empty marks it."),
    "character_hero": dict(
        kind="skeletal", folder="Characters", pivot="feet", pivot_xy=0.15, longest=(1.4, 2.2),
        height=(1.4, 2.2), tris=(40000, 70000), slots=6, collision=False, lods=4,
        lod_ratios=LOD_RATIOS_SKELETAL, nanite="no", uv_overlap=False, manifold="warning",
        texel=1024, tex_px=4096, tex_max=4096, texel_check=True, skeleton="humanoid",
        doc="Dink. Humanoid skeleton, highest budget."),
    "character_humanoid": dict(
        kind="skeletal", folder="Characters", pivot="feet", pivot_xy=0.15, longest=(0.8, 2.4),
        height=(0.8, 2.4), tris=(20000, 35000), slots=5, collision=False, lods=4,
        lod_ratios=LOD_RATIOS_SKELETAL, nanite="no", uv_overlap=False, manifold="warning",
        texel=1024, tex_px=2048, tex_max=4096, texel_check=True, skeleton="humanoid",
        doc="NPCs, children, goblins: anything on the shared humanoid skeleton."),
    "creature_quadruped": dict(
        kind="skeletal", folder="Creatures", pivot="feet", pivot_xy=0.5, longest=(0.4, 4.0),
        tris=(15000, 30000), slots=4, collision=False, lods=3,
        lod_ratios=LOD_RATIOS_SKELETAL, nanite="no", uv_overlap=False, manifold="warning",
        texel=512, tex_px=2048, tex_max=2048, texel_check=True, skeleton="quadruped",
        doc="Pig, bonca and other four-legged animals on the shared quadruped skeleton."),
    "creature": dict(
        kind="skeletal", folder="Creatures", pivot="feet", pivot_xy=0.5, longest=(0.2, 15.0),
        tris=(25000, 60000), slots=6, collision=False, lods=3,
        lod_ratios=LOD_RATIOS_SKELETAL, nanite="no", uv_overlap=False, manifold="warning",
        texel=512, tex_px=2048, tex_max=4096, texel_check=True, skeleton="custom",
        doc="Bespoke creatures with their own skeleton (dragon, pillbug, duck, stone giant)."),
}

STATIC_PREFIX = "SM"
SKELETAL_PREFIX = "SK"


def class_info(name):
    return CLASSES.get(name)


def nanite_enabled(cls_name, override=None, translucent=False):
    """Resolve whether the manifest should say Nanite is on for this asset."""
    if translucent:
        return False
    if override in ("yes", "no"):
        return override == "yes"
    return CLASSES[cls_name]["nanite"] == "yes"


def lods_required(cls_name, override_nanite=None, translucent=False):
    """Minimum number of LOD levels (including LOD0) the validator demands."""
    c = CLASSES[cls_name]
    need = c["lods"]
    if translucent or (c["kind"] == "static" and override_nanite == "no" and need == 0):
        need = max(need, 3)
    return need


def content_path(cls_name, name, sub=""):
    """Unreal content path for an asset: /Game/Dink/<Folder>[/<sub>]/<Name>."""
    sub = (sub or "").strip("/\\")
    parts = [CONTENT_ROOT.strip("/"), CLASSES[cls_name]["folder"]]
    if sub:
        parts.append(sub)
    parts.append(name)
    return "/" + "/".join(parts)
