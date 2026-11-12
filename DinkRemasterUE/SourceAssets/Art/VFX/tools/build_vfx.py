#!/usr/bin/env python3
"""Rebuild every procedural VFX source texture, preview and manifest.

    python3 SourceAssets/Art/VFX/tools/build_vfx.py            # everything (~3-5 min, 1 core)
    python3 SourceAssets/Art/VFX/tools/build_vfx.py --only fire,smoke
    python3 SourceAssets/Art/VFX/tools/build_vfx.py --quick    # reduced frame counts, writes to ./_quick

numpy + Pillow only.  No downloads, no generative models, no input images.
All randomness is seeded; output is bit-reproducible for a given numpy build.
"""
import argparse, csv, json, os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vfxlib import *
import vfx_fire as FIRE
import vfx_smoke as SMOKE
import vfx_misc as MISC

VERSION = "vfx-v1"
GEN_DATE = "2026-11-08"
SEEDS = dict(fire=1997_01, smoke=1997_02, embers=1997_03, ash=1997_04, fireball=1997_05, trail=1997_06,
             glow=1997_07, flash=1997_08, dust=1997_09, noise=1997_10, masks=1997_11, blue=1997_12)

try:
    os.nice(10)
except Exception:
    pass

ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT_TEX = OUT_PRE = None
MANIFEST = []
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------ preview helpers
def bg_gradient(h, w, lo=0.26, hi=0.46):
    g = np.linspace(hi, lo, h, dtype=F32)[:, None, None]       # lighter "sky" on top
    return np.repeat(np.repeat(g, w, 1), 3, 2)


def composite(rgba, mode):
    rgb, a = rgba[..., :3], rgba[..., 3:4]
    if mode == "add":
        return np.clip(rgb * a, 0, 1)
    return rgb * a + bg_gradient(*rgba.shape[:2]) * (1 - a)


def contact_sheet(atlas, mode, name, size=1024):
    img = composite(atlas, mode) if atlas.shape[2] == 4 else atlas
    im = Image.fromarray(to_u8(img), "RGB").resize((size, size), Image.LANCZOS)
    im.save(os.path.join(OUT_PRE, name + "_contact.png"), optimize=True)


def make_gif(frames_rgba, mode, name, size=192, ms=40, relit=None):
    ims = []
    for f in frames_rgba:
        c = composite(f, mode) if relit is None else f
        ims.append(Image.fromarray(to_u8(c), "RGB").resize((size, size), Image.LANCZOS))
    # one shared palette built from a sample montage keeps the GIF from shimmering
    step = max(1, len(ims) // 8)
    mont = Image.new("RGB", (size * 4, size * 2))
    for k, i in enumerate(range(0, len(ims), step)[:8]):
        mont.paste(ims[i], ((k % 4) * size, (k // 4) * size))
    pal = mont.quantize(256, Image.MEDIANCUT, dither=Image.NONE)
    q = [im.quantize(palette=pal, dither=Image.FLOYDSTEINBERG) for im in ims]
    q[0].save(os.path.join(OUT_PRE, name + ".gif"), save_all=True, append_images=q[1:], duration=ms, loop=0, disposal=1)


def seam_ratio(frames):
    """Loop-seam quality: mean |last->first| / mean |consecutive| (1.0 = seamless)."""
    f = np.stack([x for x in frames])
    cons = np.mean(np.abs(f[1:] - f[:-1]))
    seam = np.mean(np.abs(f[0] - f[-1]))
    return float(seam / max(cons, 1e-9))


def write_tex(name, arr, *, srgb, **meta):
    """arr float (H,W,C) in the texture's final encoding (sRGB-encoded colour if srgb)."""
    path = os.path.join(OUT_TEX, name + ".png")
    save_png(path, to_u8(arr if arr.ndim == 3 else arr))
    h, w = arr.shape[:2]
    ch = 1 if arr.ndim == 2 else arr.shape[2]
    entry = dict(name=name, file=f"Textures/{name}.png", width=w, height=h, channels=ch,
                 bytes=os.path.getsize(path), sha256=sha256(path),
                 colour_space=("sRGB (RGB), linear alpha" if srgb and ch >= 3 else "linear (data)"))
    entry.update(meta)
    MANIFEST.append(entry)
    log(f"wrote {name} {w}x{h}x{ch} {entry['bytes'] / 1e6:.2f} MB")
    return entry


def ue(compression, srgb, mips="FromTextureGroup", group="TEXTUREGROUP_Effects", address="Clamp", extra=None):
    d = dict(compression_settings=compression, srgb=srgb, mip_gen_settings=mips, lod_group=group,
             address_x=address, address_y=address, filter="Default")
    if extra: d.update(extra)
    return d


def layout(cols, rows, frames, cell_px, fps, loop, atlas_px=None, **kw):
    d = dict(type="flipbook", columns=cols, rows=rows, frames=frames, frame_order="row-major, top-left first",
             cell_px=cell_px, fps=fps, duration_s=round(frames / fps, 4), loop=loop)
    d.update(kw)
    return d


# ------------------------------------------------------------------ builders
def build_fire(quick):
    n, cell = (16, 256) if quick else (64, 256)
    cols = rows = 8 if not quick else 4
    col, tmp = FIRE.render_flipbook(n, cell, SEEDS["fire"], progress=lambda i, n: None)
    atlas_px = cell * cols
    A = pack_atlas(col, cols, rows, atlas_px)
    Tm = pack_atlas(tmp, cols, rows, atlas_px)
    contact_sheet(A, "add", "fire_color_8x8")
    make_gif(col, "add", "fire_color_8x8", ms=40)
    seam = seam_ratio([c[..., :3] * c[..., 3:] for c in col])
    lay = layout(cols, rows, n, cell, 30, True, loop_seam_ratio=round(seam, 3),
                 uv_note="cell = atlas/8 exactly; 6% transparent border per cell")
    write_tex("T_VFX_Fire_Color_8x8", A, srgb=True, layout=lay, role="fire_colour",
              channels_desc="RGB = baked blackbody flame colour (straight, bled into transparent texels); A = flame opacity/density",
              blend_modes=["Additive (emissive = RGB*A*Intensity)", "Translucent/AlphaComposite with soot from Fire_Temp.B"],
              ue_texture=ue("TC_BC7 (or TC_Default/BC3 if memory-bound)", True),
              niagara=dict(renderer="Sprite (SubUV)", subuv="Niagara SubUV Animation, 8x8, Linear blend, loop over particle Age/LoopDuration",
                           material="M_VFX_Fire: Emissive = tex.rgb * tex.a * EmissiveScale (HDR 4-30 for bloom); Opacity = tex.a for translucent variant",
                           sprite="Facing=camera, vertical-up aligned, size ~ (width 0.6 x height 1.0) of flame height; per-particle random start frame offset"),
              seed=SEEDS["fire"], generator="vfx_fire.flame_field (curl-warped looping fBm erosion + blackbody ramp)")
    write_tex("T_VFX_Fire_Temp_8x8", Tm, srgb=False, layout=lay, role="fire_temperature",
              channels_desc="R = normalised temperature (0=850 K .. 1=2350 K); G = density; B = soot (cool dark smoke inside flame); A = hot-core mask",
              ue_texture=ue("TC_BC7 (linear)", False),
              niagara=dict(renderer="Sprite (SubUV)", subuv="same SubUV params as Fire_Color (shared frame index)",
                           material="Sample R, remap by (particle heat * k), look up T_VFX_Blackbody_LUT (U=R) for HDR colour; multiply LUT.A*4 as emissive intensity; use G as opacity, lerp toward black by B for soot. Lets one texture serve embers-to-white-hot flames and colour-graded fire (green/blue spell fire)."),
              seed=SEEDS["fire"])
    return col


def build_smoke(quick):
    n = 16 if quick else 64
    cols = rows = 4 if quick else 8
    A_, B_, C_ = SMOKE.render_smoke(n, 256, SEEDS["smoke"])
    atlas_px = 256 * cols
    AA = pack_atlas(A_, cols, rows, atlas_px); BB = pack_atlas(B_, cols, rows, atlas_px)
    CC = pack_atlas(C_, cols, rows, atlas_px)
    contact_sheet(CC, "alpha", "smoke_baked_8x8")
    make_gif(C_, "alpha", "smoke_baked_8x8", ms=42)
    # visual check of the 6-way channels
    contact_sheet(np.dstack([AA[..., :3], np.ones_like(AA[..., 0])]), "rgb", "smoke_6way_A_rgb_8x8")
    contact_sheet(np.dstack([BB[..., :3], np.ones_like(BB[..., 0])]), "rgb", "smoke_6way_B_rgb_8x8")
    # relit demo: light orbits the puff, proving the 6-way maps work
    relit = []
    for i in range(n):
        a, b = A_[i], B_[i]
        th = 2 * np.pi * i / n
        L = np.array([np.cos(th) * 0.8, 0.6, np.sin(th) * 0.9]); L /= np.linalg.norm(L)   # x right, y up, z toward camera
        wR, wL = max(L[0], 0), max(-L[0], 0); wT, wB = max(L[1], 0), max(-L[1], 0); wF, wK = max(L[2], 0), max(-L[2], 0)
        lit = wR * a[..., 0] + wL * a[..., 1] + wT * a[..., 2] + wB * b[..., 0] + wK * b[..., 1] + wF * b[..., 2]
        rgb = np.clip(lit[..., None] * 0.9 * np.array([1.0, 0.97, 0.92]), 0, 1)
        rgb = srgb_encode(rgb * 0.55)
        al = a[..., 3:4]
        relit.append(rgb * al + bg_gradient(256, 256, 0.1, 0.22) * (1 - al))
    make_gif(relit, "rgb", "smoke_6way_relit_demo", ms=42, relit=True)
    lay = layout(cols, rows, n, 256, 24, True, loop_seam_ratio=round(seam_ratio([c[..., :3] * c[..., 3:] for c in C_]), 3))
    sixway_n = dict(renderer="Sprite (SubUV)", subuv=f"Niagara SubUV Animation {cols}x{rows}, Linear blend",
                    material="6-way lighting: dot(LightDir_world->camera-space, axes) -> weights max(+/-L.x..z,0) over (R,L,T,B,K,F); sum weights*maps; multiply by albedo colour and light colour; Opacity = map A.A")
    write_tex("T_VFX_Smoke_6Way_A_8x8", AA, srgb=False, layout=lay, role="smoke_lightmap_A",
              channels_desc="R = light from +X (right), G = light from -X (left), B = light from top (+Y), A = opacity (view-projected extinction)",
              ue_texture=ue("TC_BC7 (linear)", False, extra=dict(note="do not use TC_Masks/BC1: RGB+A all carry data")),
              niagara=sixway_n, seed=SEEDS["smoke"], generator="vfx_smoke: curl-advected looping fBm density volume 128x128x32, Wrenninge multiple-scatter transmittance along 6 axes, projected along view")
    write_tex("T_VFX_Smoke_6Way_B_8x8", BB, srgb=False, layout=lay, role="smoke_lightmap_B",
              channels_desc="R = light from bottom (-Y), G = light from back (-Z, away from camera), B = light from front (+Z, camera side), A = normalised optical thickness (for backlit translucency / SSS fudge)",
              ue_texture=ue("TC_BC7 (linear)", False), niagara=sixway_n, seed=SEEDS["smoke"])
    write_tex("T_VFX_Smoke_BakedTopLit_8x8", CC, srgb=True, layout=lay, role="smoke_baked_colour",
              channels_desc="RGB = smoke lit from above (sky 1.0) with warm key from upper-left/front, neutral grey albedo 0.45; A = opacity. Use when 6-way is overkill.",
              blend_modes=["AlphaComposite / Translucent"], ue_texture=ue("TC_BC7", True),
              niagara=dict(renderer="Sprite (SubUV)", subuv=f"SubUV {cols}x{rows}", material="Colour = tex.rgb * TintColour; Opacity = tex.a * ParticleAlpha; soft-particle depth fade 20-80 cm; tint dark (0.15-0.3) for house-fire smoke"),
              seed=SEEDS["smoke"])


def build_embers_ash(quick):
    em = MISC.render_embers(128, SEEDS["embers"])
    A = pack_atlas(em, 4, 4, 512)
    contact_sheet(A, "add", "embers_4x4", size=1024)
    write_tex("T_VFX_Embers_4x4", A, srgb=True,
              layout=dict(type="sprite_sheet", columns=4, rows=4, frames=16, cell_px=128, loop=False,
                          cells={"0-7": "ember dots (random sprite per particle)", "8-11": "spark streaks, head at +X (align to velocity)",
                                 "12-15": "one ember cooling hot->dark (use as SubUV over lifetime)"}),
              role="embers_sparks", channels_desc="RGB = blackbody colour (straight); A = coverage",
              blend_modes=["Additive"], ue_texture=ue("TC_BC7", True),
              niagara=dict(renderer="Sprite (random SubUV 0-7) / Sprite velocity-aligned for 8-11 / Ribbon-free", subuv="Niagara SubUV Image Index: Random 0..7 for dots; Linear 12..15 over Age for cooling",
                           material="Additive, emissive = rgb*a*EmissiveScale (10-40), flicker with per-particle sin(Age) multiplier"),
              seed=SEEDS["embers"])
    ash = MISC.render_ash(128, SEEDS["ash"])
    A2 = pack_atlas(ash, 4, 4, 512)
    contact_sheet(A2, "alpha", "ash_flakes_4x4", size=1024)
    write_tex("T_VFX_AshFlakes_4x4", A2, srgb=True,
              layout=dict(type="sprite_sheet", columns=4, rows=4, frames=16, cell_px=128, loop=False,
                          cells={"all": "16 distinct torn flakes, charcoal (2/3) and pale grey ash (1/3)"}),
              role="ash_flakes", channels_desc="RGB = burnt-paper albedo (straight, bled); A = flake mask",
              blend_modes=["Masked/AlphaComposite (dithered translucency OK)"], ue_texture=ue("TC_BC7", True),
              niagara=dict(renderer="Sprite, random SubUV, random rotation; 3D spin via Rotation Rate", subuv="Image Index random 0..15",
                           material="Lit translucent/masked; colour tint from fire proximity (lerp to dark red near flames via Fire_Temp)"),
              seed=SEEDS["ash"])


def build_fireball(quick):
    n = 16
    col, tmp = MISC.render_fireball_core(n, 256, SEEDS["fireball"])
    A = pack_atlas(col, 4, 4, 1024); Tm = pack_atlas(tmp, 4, 4, 1024)
    contact_sheet(A, "add", "fireball_core_4x4")
    make_gif(col, "add", "fireball_core_4x4", ms=40)
    lay = layout(4, 4, n, 256, 24, True, loop_seam_ratio=round(seam_ratio([c[..., :3] * c[..., 3:] for c in col]), 3),
                 orientation="head (sphere) at +U/right, flame streams toward -U; rotate sprite to velocity")
    write_tex("T_VFX_Fireball_Core_4x4", A, srgb=True, layout=lay, role="fireball_core",
              channels_desc="RGB = blackbody colour (straight); A = density", blend_modes=["Additive"], ue_texture=ue("TC_BC7", True),
              niagara=dict(renderer="Sprite, Alignment = Velocity aligned (Facing Camera)", subuv="SubUV 4x4 looping @24 fps",
                           material="Additive emissive; spawn a point light of the same colour (intensity ~ 3000-8000 cd) from the same emitter"),
              seed=SEEDS["fireball"])
    write_tex("T_VFX_Fireball_Core_Temp_4x4", Tm, srgb=False, layout=lay, role="fireball_core_temperature",
              channels_desc="R temperature, G density, B soot, A hot core (same encoding as Fire_Temp)", ue_texture=ue("TC_BC7 (linear)", False),
              niagara=dict(material="Blackbody LUT lookup for coloured (arcane/blue) fireball variants"), seed=SEEDS["fireball"])
    tc, tt = MISC.render_fireball_trail(1024, 256, SEEDS["trail"])
    contact_sheet(np.pad(tc, ((0, 768), (0, 0), (0, 0))), "add", "fireball_trail", size=1024)
    # horizontal-tile seam metric
    seam = float(np.mean(np.abs(tc[:, 0, :3] - tc[:, -1, :3])) / max(np.mean(np.abs(tc[:, 1:, :3] - tc[:, :-1, :3])), 1e-9))
    # tiling preview: 2 tiles side by side as a static contact sheet
    two = np.concatenate([tc, tc], 1)
    Image.fromarray(to_u8(composite(two, "add")), "RGB").resize((1024, 128), Image.LANCZOS).save(os.path.join(OUT_PRE, "fireball_trail_tiled2x_contact.png"))
    os.remove(os.path.join(OUT_PRE, "fireball_trail_contact.png"))
    write_tex("T_VFX_Fireball_Trail", tc, srgb=True,
              layout=dict(type="strip", tile_u=True, tile_v=False, u_tile_seam_ratio=round(seam, 3), u_axis="along ribbon (pan toward tail via UV.x -= Time*Speed)", v_axis="across ribbon"),
              role="fireball_trail", channels_desc="RGB = blackbody colour; A = density. Tileable in U, constant along length (taper/fade in material using ribbon normalised age).",
              blend_modes=["Additive"], ue_texture=ue("TC_BC7", True, address="Wrap U / Clamp V", extra=dict(address_x="Wrap", address_y="Clamp")),
              niagara=dict(renderer="Ribbon, UV0 distribution = Tiled over Length (tile distance ~ 1 texture per 2*width), Facing=camera",
                           material="Opacity = tex.a * (1-NormalizedAge)^1.5 * edge fade; pan U for flow; Width over life 1->0.15"),
              seed=SEEDS["trail"])
    write_tex("T_VFX_Fireball_Trail_Temp", tt, srgb=False,
              layout=dict(type="strip", tile_u=True, tile_v=False), role="fireball_trail_temperature",
              channels_desc="R temperature, G density, B soot, A hot core", ue_texture=ue("TC_BC7 (linear)", False, extra=dict(address_x="Wrap", address_y="Clamp")),
              niagara=dict(material="Blackbody LUT lookup; cool the trail along ribbon age by subtracting age*0.6 from R"), seed=SEEDS["trail"])


def build_glow(quick):
    tiles = MISC.render_glow_sheet(256, SEEDS["glow"])
    A = pack_atlas([t[..., None] for t in tiles], 2, 2, 512, channels=1)[..., 0]
    Image.fromarray(to_u8(A), "L").save(os.path.join(OUT_PRE, "magic_glow_2x2_contact.png"))
    write_tex("T_VFX_MagicGlow_2x2", A, srgb=False,
              layout=dict(type="sprite_sheet", columns=2, rows=2, frames=4, cell_px=256, loop=False,
                          cells={"0": "soft halo (truncated Lorentzian^1.5)", "1": "4-point diffraction sparkle", "2": "thin ring", "3": "log-spiral swirl wisp"}),
              role="magic_glow", channels_desc="single-channel linear intensity; tint in material (any colour: heal=green, arcane=blue, pickup=gold)",
              blend_modes=["Additive"], ue_texture=ue("TC_Grayscale (BC4)", False),
              niagara=dict(renderer="Sprite, Facing camera", subuv="Image Index chosen per emitter (no animation)", material="Emissive = tex.r * ColourHDR; Opacity = tex.r for translucent"),
              seed=SEEDS["glow"])


def build_hit(quick):
    n = 36
    fl = MISC.render_hit_flash(n, 341, SEEDS["flash"])
    A = pack_atlas(fl, 6, 6, 2048)
    contact_sheet(A, "add", "hit_flash_6x6")
    make_gif(fl, "add", "hit_flash_6x6", ms=33)
    lay = layout(6, 6, n, 341, 60, False, uv_note="2048/6 = 341.33: frames are placed at round(i*341.333) and are 341 px; Unreal's SubUV cell is 341.33 px so drift is <0.7 px. Every frame has >=14 px of empty border.")
    write_tex("T_VFX_HitFlash_6x6", A, srgb=True, layout=lay, role="hit_flash",
              channels_desc="RGB = blackbody flash/spark colour; A = coverage. Frame 0-5 white-hot core+starburst, then shock ring and ballistic sparks.",
              blend_modes=["Additive"], ue_texture=ue("TC_BC7", True),
              niagara=dict(renderer="Sprite (1 particle per hit, lifetime 0.6 s @ 60 fps), random Rotation + mirror U", subuv="SubUV 6x6, Linear blend OFF (flash wants crisp frames) or ON for smoothness",
                           material="Additive emissive, EmissiveScale 8-20; scale sword hits 1.0, fist hits 0.55 + desaturate via LUT"),
              seed=SEEDS["flash"])
    du = MISC.render_dust(n, 341, SEEDS["dust"])
    A2 = pack_atlas(du, 6, 6, 2048)
    contact_sheet(A2, "alpha", "dust_puff_6x6")
    make_gif(du, "alpha", "dust_puff_6x6", ms=42)
    write_tex("T_VFX_DustPuff_6x6", A2, srgb=True, layout=layout(6, 6, n, 341, 30, False, uv_note=lay["uv_note"]), role="dust_puff",
              channels_desc="RGB = dust lit from above (baked, tan-grey albedo); A = opacity. Expanding hemispherical puff that thins out.",
              blend_modes=["AlphaComposite / Translucent"], ue_texture=ue("TC_BC7", True),
              niagara=dict(renderer="Sprite (1-3 per impact, ground-aligned origin at bottom-centre of the puff), lifetime ~1.2 s @ 30 fps", subuv="SubUV 6x6, Linear blend ON",
                           material="Colour = tex.rgb * SurfaceTint (sample ground albedo colour for fist-on-dirt vs stone dust); Opacity = tex.a; soft-particle depth fade 15 cm"),
              seed=SEEDS["dust"])


def build_masks(quick):
    A, B = MISC.soft_masks(256, SEEDS["masks"])
    Image.fromarray(to_u8(np.concatenate([A[..., :3], B[..., :3]], 1)), "RGB").save(os.path.join(OUT_PRE, "soft_masks_contact.png"))
    write_tex("T_VFX_SoftMask_A_256", A, srgb=False, layout=dict(type="single"), role="soft_masks",
              channels_desc="R = (1-r^2)^2 smooth falloff, G = gaussian exp(-4.5 r^2) windowed, B = linear cone, A = soft ring (r=0.62)",
              ue_texture=ue("TC_Default (BC7/BC3, sRGB off)", False), niagara=dict(material="Radial masks for sprite particles, decals, light-cookie-like glows, depth-fade shaping"), seed=SEEDS["masks"])
    write_tex("T_VFX_SoftMask_B_256", B, srgb=False, layout=dict(type="single"), role="soft_masks",
              channels_desc="R = soft superellipse square, G = horizontal streak (4:1), B = vertical edge fade, A = cloudy circle (radial * fBm)",
              ue_texture=ue("TC_Default (BC7/BC3, sRGB off)", False), niagara=dict(material="Ground-contact dust shapes, light shafts, streak particles"), seed=SEEDS["masks"])
    names, rows = MISC.gradient_luts(256)
    G = np.repeat(rows[..., None], 3, 2)
    G = np.dstack([G, np.ones_like(G[..., 0])])
    write_tex("T_VFX_Gradients_256x16", G, srgb=False,
              layout=dict(type="lut_rows", rows=16, row_names=names, sample="V = (row+0.5)/16, U = normalised value / age; Wrap=Clamp, filter=Bilinear, NoMipmaps"),
              role="curve_lut", channels_desc="each row is one scalar curve replicated in RGB; A=1", ue_texture=ue("TC_Default", False, mips="NoMipmaps", group="TEXTUREGROUP_Pixels2D"),
              niagara=dict(material="Cheap curve lookup in materials / Niagara texture sample (age fade, attack-decay, flicker hold)"), seed=0)
    L = MISC.blackbody_lut(256, 4)
    write_tex("T_VFX_Blackbody_LUT_256x4", L, srgb=True,
              layout=dict(type="lut_row", kelvin_range=[850, 2350], u_axis="normalised temperature 0..1", sample="V=0.5 (4 identical rows to satisfy minimum height); Clamp, Bilinear, NoMipmaps"),
              role="blackbody_ramp", channels_desc="RGB = sRGB tone-mapped blackbody colour (true Planck chromaticity, compressed radiance); A (linear) = relative emissive multiplier / 4",
              ue_texture=ue("TC_Default (uncompressed RGBA8 recommended)", True, mips="NoMipmaps", group="TEXTUREGROUP_Pixels2D"),
              niagara=dict(material="u = Fire_Temp.R * Heat; Emissive = LUT.rgb * (LUT.a*4) * EmissiveScale"), seed=0)
    Bn = MISC.blue_noise(128, SEEDS["blue"])
    write_tex("T_VFX_BlueNoise_128", Bn, srgb=False, layout=dict(type="tile", tile_u=True, tile_v=True, rank_uniform=True),
              role="blue_noise_dither", channels_desc="single channel, rank-uniform high-pass noise (void-and-cluster approximation via iterative FFT high-pass + rank remap)",
              ue_texture=ue("TC_Grayscale", False, mips="NoMipmaps", address="Wrap", group="TEXTUREGROUP_Pixels2D"),
              niagara=dict(material="Dithered opacity (Masked) for soft particles, temporal dithering of dissolve"), seed=SEEDS["blue"])


def build_noise(quick):
    A, B, C = MISC.noise_packs(512, SEEDS["noise"])
    tile_ok = lambda X: float(max(np.abs(X[0] - X[-1]).mean(), np.abs(X[:, 0] - X[:, -1]).mean()) /
                              max(np.abs(X[1:] - X[:-1]).mean(), 1e-9))
    prev = np.concatenate([np.concatenate([x[..., i] for i in range(4)], 1) for x in (A, B, C)], 0)
    Image.fromarray(to_u8(prev), "L").resize((1024, 768), Image.LANCZOS).save(os.path.join(OUT_PRE, "noise_packs_contact.png"))
    common = dict(layout=dict(type="tile", tile_u=True, tile_v=True), seed=SEEDS["noise"],
                  ue_texture=ue("TC_Default (BC7, sRGB off)", False, mips="FromTextureGroup", address="Wrap", group="TEXTUREGROUP_Effects"))
    write_tex("T_VFX_NoisePack_A_512", A, srgb=False, role="noise_pack", seam_ratio=round(tile_ok(A[..., 0]), 3),
              channels_desc="R = Perlin fBm (6 oct, 4 cells), G = 1-Worley F1 (8 cells), B = Worley F2-F1 cell edges, A = Perlin-Worley (cloud base remap)",
              niagara=dict(material="Erosion/dissolve masks, smoke detail, sprite UV distortion, Perlin-Worley for billowy opacity"), **common)
    write_tex("T_VFX_NoisePack_B_512", B, srgb=False, role="curl_noise", seam_ratio=round(tile_ok(B[..., 2]), 3),
              channels_desc="R = curl vx, G = curl vy (0.5 +/- 0.5*v/vmax, subtract 0.5 and *2 to recover), B = |curl| normalised, A = scalar potential (fBm 4 oct)",
              niagara=dict(material="Flow-map/advection: UV += (RG*2-1)*Strength; Niagara Sample Texture for curl forces in particles (sampled as 2D field wrapped over world XY)"), **common)
    write_tex("T_VFX_NoisePack_C_512", C, srgb=False, role="noise_pack", seam_ratio=round(tile_ok(C[..., 0]), 3),
              channels_desc="R = ridged turbulence, G = 1-Worley F1 (6 large cells), B = 1-Worley F1 (24 small cells), A = Worley cell random id",
              niagara=dict(material="Per-cell random (A) for sparkle/flicker, ridged R for lightning/magic veins, Worley for embers/bubbles"), **common)


STAGES = [("fire", build_fire), ("smoke", build_smoke), ("embers", build_embers_ash), ("fireball", build_fireball),
          ("glow", build_glow), ("hit", build_hit), ("masks", build_masks), ("noise", build_noise)]


def write_manifest(out_root, full):
    meta = dict(version=VERSION, generated=GEN_DATE, generator="SourceAssets/Art/VFX/tools/build_vfx.py",
                libraries=dict(numpy=np.__version__, pillow=Image.__version__ if hasattr(Image, "__version__") else "?"),
                notes=["All textures are original procedural output (numpy + Pillow); no input images, downloads or generative models.",
                       "Colour textures: RGB is sRGB-encoded and STRAIGHT (not premultiplied) with colour bled into transparent texels so bilinear/mip filtering does not fringe; multiply by A in the material for additive/premultiplied use.",
                       "Data textures (Temp, 6-way, noise, masks, LUTs) must be imported with sRGB OFF.",
                       "Flipbook frames carry a transparent border; no frame content reaches its cell edge, so mips down to ~1/8 are free of neighbour bleed.",
                       "Frame order is row-major from the top-left, the Niagara SubUV convention."],
                complete=full)
    prev = {}
    mp = os.path.join(out_root, "vfx_manifest.json")
    if not full and os.path.exists(mp):
        try:
            prev = {t["name"]: t for t in json.load(open(mp))["textures"]}
        except Exception:
            prev = {}
    for t in MANIFEST:
        prev[t["name"]] = t
    meta["textures"] = sorted(prev.values(), key=lambda t: t["name"])
    json.dump(meta, open(mp, "w"), indent=1)
    return meta


LEDGER_COLS = ["asset_path", "derived_path", "kind", "replaces", "source", "tool_model", "prompt", "parameters",
               "generation_id", "flow_id", "generated_on", "credits", "licence", "sha256", "duration_s", "status", "notes"]


def write_ledger(out_root, meta):
    rows = []
    for t in meta["textures"]:
        lay = t.get("layout", {})
        params = f"seed={t.get('seed')}; {t['width']}x{t['height']}; {t['colour_space']}"
        if lay.get("type") == "flipbook":
            params += f"; {lay['columns']}x{lay['rows']} flipbook {lay['frames']}f @{lay['fps']}fps loop={str(lay['loop']).lower()}"
        rows.append({
            "asset_path": f"SourceAssets/Art/VFX/{t['file']}",
            "derived_path": f"Content/Dink/Textures/VFX/{t['name']}.uasset",
            "kind": "texture",
            "replaces": "House fire / fireball / hit / pickup VFX (new; no prior asset)",
            "source": "Original project-authored procedural texture synthesis",
            "tool_model": "Python numpy + Pillow (SourceAssets/Art/VFX/tools/build_vfx.py); no generative model or external input assets",
            "prompt": t["role"].replace("_", " ") + ": " + t["channels_desc"][:140],
            "parameters": params, "generation_id": VERSION, "flow_id": "", "generated_on": GEN_DATE, "credits": "0",
            "licence": "Original project asset; no third-party source material", "sha256": t["sha256"],
            "duration_s": f"{lay['duration_s']:.3f}" if lay.get("type") == "flipbook" else "",
            "status": "candidate",
            "notes": "Procedural VFX source. Rebuild with SourceAssets/Art/VFX/tools/build_vfx.py; Niagara/material setup pending; human art approval pending.",
        })
    with open(os.path.join(ROOT, "ledger_rows_proposed.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader(); w.writerows(rows)


def main():
    global OUT_TEX, OUT_PRE
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    out_root = a.out or (os.path.join(ROOT, "_quick") if a.quick else ROOT)
    OUT_TEX = os.path.join(out_root, "Textures"); OUT_PRE = os.path.join(out_root, "Preview")
    os.makedirs(OUT_TEX, exist_ok=True); os.makedirs(OUT_PRE, exist_ok=True)
    only = set(filter(None, a.only.split(",")))
    for key, fn in STAGES:
        if only and key not in only:
            continue
        log(f"== {key}")
        fn(a.quick)
    meta = write_manifest(out_root, full=not only and not a.quick)
    if not a.quick:
        write_ledger(out_root, meta)
    log("done")


if __name__ == "__main__":
    main()
