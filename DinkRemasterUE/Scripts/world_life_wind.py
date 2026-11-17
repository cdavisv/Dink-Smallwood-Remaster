"""Shared foliage wind for the vegetation parents (M_Veg_Foliage, M_Veg_Bark): one definition, used by
Scripts/import_photoreal_art.py (full photoreal import) and Scripts/import_world_life.py (world-alive stream: rebuilds
only what reads the wind). Presentation only: a world-position offset, nothing the simulation reads.

Inputs of the custom node (all wired by `wire_wind`):
  VC, VA     vertex colour wind weights of the photoreal vegetation (R trunk sway 0 ground..1 top, G branch phase,
             B leaf flutter, A branch bend)
  T, Obj, WP time, object pivot, vertex world position
  Wind       MPC_Dink_Environment.Wind: the global multiplier of `dink.Wind` (UDinkEnvironmentSubsystem; 0 = still)
  Scale      the material instance's WindScale (0 for deadwood and tilled dirt)
  WD         MPC_Dink_World.WindDir    (x, y: unit direction the wind blows TO; z: strength 0..2; w: gustiness 0..1)
  WG         MPC_Dink_World.WindGust   (x: slow global gust 0.3..1.8 set by UDinkWorldLifeSubsystem; y: gust-field travel speed;
             z, w: the gust field's travel, integrated on the CPU (direction x speed x dt), so a change of wind never
             makes the field jump: absolute Time is never multiplied by a value that changes)
  WL         MPC_Dink_World.WorldLife  (0 = the asset default and dink.World.Life 0: exactly the sway of the photoreal pass
             before this layer, travel float2(0.92, 0.39) * T * 0.11 and no lean; 1 = the subsystem's wind)
  PushOn     1 on the foliage parent, 0 on bark: trunks never bend away from a walker
  P0..P3     MPC_Dink_World.Push0..3   (x, y world cm; z radius cm; w strength 0..1): Dink and the nearest creatures
             bend grass, crops and bush tips away from them as they walk through. Strength 0 = unused slot.
  Cam, Rnd, Fade, FadeNear, FadeFar   scatter thinning of the grass carpet (unchanged)
UDinkWorldLifeSubsystem (DinkCore) writes MPC_Dink_World every frame; with it absent (or dink.World.Life 0) WorldLife is
0 and the foliage sways exactly as before this change (direction 0.8/0.6, strength 1, gust field travelling
(0.92, 0.39) * T, no lean, no pushes).
"""

MPC_WORLD = '/Game/Dink/WorldLife/MPC_Dink_World'

# name -> default (x, y, z, w)
MPC_WORLD_VECTORS = {
    'WindDir': (0.8, 0.6, 1.0, 1.0),
    'WindGust': (1.0, 1.0, 0.0, 0.0),
    'Push0': (0.0, 0.0, 1.0, 0.0),
    'Push1': (0.0, 0.0, 1.0, 0.0),
    'Push2': (0.0, 0.0, 1.0, 0.0),
    'Push3': (0.0, 0.0, 1.0, 0.0),
}
MPC_WORLD_SCALARS = {'WorldLife': 0.0}   # the subsystem writes 1 while it runs

WIND_HLSL = '''
float ph = VC.g * 6.2832 + dot(Obj.xy, float2(0.0031, 0.0047));
float2 wd = WD.xy / max(length(WD.xy), 0.001);
float strength = WD.z;
float sway = (sin(T * 0.62 + ph * 0.3) + 0.35 * sin(T * 1.37 + ph)) * VC.r * VC.r * 5.0;
float bend = sin(T * 1.9 + ph) * VA * 4.0;
float flutter = sin(T * 7.3 + ph * 3.1) * VC.b * 0.9;
float3 dir = float3(wd, 0.0);
// gusts: a slow value-noise field (about 14 m and 5 m) travelling down the wind, so a field leans in passing waves
float wl = saturate(WL);
float2 travel = lerp(float2(0.92, 0.39) * T, WG.zw, wl);
float2 gp = Obj.xy / 1400.0 - travel * 0.11;
float2 gi = floor(gp); float2 gf = gp - gi; gf = gf * gf * (3.0 - 2.0 * gf);
#define DINK_GH(c) frac(sin(dot(c, float2(127.1, 311.7))) * 43758.5453)
float g1 = lerp(lerp(DINK_GH(gi), DINK_GH(gi + float2(1.0, 0.0)), gf.x), lerp(DINK_GH(gi + float2(0.0, 1.0)), DINK_GH(gi + float2(1.0, 1.0)), gf.x), gf.y);
float2 hp = Obj.xy / 520.0 - travel * 0.23;
float2 hi = floor(hp); float2 hf = hp - hi; hf = hf * hf * (3.0 - 2.0 * hf);
float g2 = lerp(lerp(DINK_GH(hi), DINK_GH(hi + float2(1.0, 0.0)), hf.x), lerp(DINK_GH(hi + float2(0.0, 1.0)), DINK_GH(hi + float2(1.0, 1.0)), hf.x), hf.y);
#undef DINK_GH
float field = 0.45 + 1.5 * smoothstep(0.35, 0.85, 0.65 * g1 + 0.35 * g2);
float gust = lerp(1.0, field, saturate(WD.w)) * WG.x;
// a steady lean down the wind grows with strength (tall grass and crowns lie over in a strong wind)
float lean = VC.r * VC.r * 6.0 * saturate(strength - 0.6) * gust * wl;
float3 offset = (dir * ((sway + bend) * gust + lean) + float3(0.0, 0.0, 1.0) * (bend * 0.3 + flutter * (0.6 + 0.4 * gust))) * Wind * Scale * strength;
// walk-through: blades and twig tips near a pusher lean away from it and press down a little (eased falloff, 16 Nov: the quadratic one was too weak to see);
// weight by height so roots stay put; independent of the wind strength (still air still bends grass under a foot)
float2 push = float2(0.0, 0.0);
float4 Ps[4] = { P0, P1, P2, P3 };
[unroll] for (int i = 0; i < 4; ++i)
{
    float2 d = WP.xy - Ps[i].xy;
    float dist = length(d);
    float f = saturate(1.0 - dist / max(Ps[i].z, 1.0));
    push += d / max(dist, 1.0) * f * (2.0 - f) * Ps[i].w;   // eased: blades a stride away still part visibly
}
// only low growth: grass, crops, bush tips; nothing more than 1.5 m above the mesh pivot, and never on bark
float h = saturate(VC.r) * saturate(VC.r + VA) * saturate(1.0 - (WP.z - Obj.z) / 150.0) * saturate(PushOn);
float pl = min(length(push), 1.0);
offset += float3(push * 52.0 * h, -18.0 * pl * h) * saturate(Scale);
// scatter thinning: beyond FadeNear an instance shrinks into its pivot once its random number exceeds the
// share still kept at that distance; none are left at FadeFar
float keep = saturate((FadeFar - distance(Cam, Obj)) / max(FadeFar - FadeNear, 1.0));
float s = lerp(1.0, saturate((keep - Rnd * 0.85) * 6.0), saturate(Fade));
return offset * s + (Obj - WP) * (1.0 - s);'''

WIND_INPUTS = ['VC', 'VA', 'T', 'Obj', 'Wind', 'Scale', 'WD', 'WG', 'WL', 'PushOn', 'P0', 'P1', 'P2', 'P3', 'Cam', 'WP', 'Rnd', 'Fade', 'FadeNear', 'FadeFar']


def ensure_world_mpc(unreal, save):
    """MPC_Dink_World with every parameter above (missing ones are added, existing ones keep their defaults)."""
    lib = unreal.EditorAssetLibrary
    folder, name = MPC_WORLD.rsplit('/', 1)
    mpc = lib.load_asset(MPC_WORLD) if lib.does_asset_exist(MPC_WORLD) else None
    if mpc is None:
        mpc = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.MaterialParameterCollection,
                                                                       unreal.MaterialParameterCollectionFactoryNew())
    vectors = list(mpc.get_editor_property('vector_parameters'))
    scalars = list(mpc.get_editor_property('scalar_parameters'))
    have_v = {str(p.get_editor_property('parameter_name')) for p in vectors}
    have_s = {str(p.get_editor_property('parameter_name')) for p in scalars}
    changed = False
    for pname, d in MPC_WORLD_VECTORS.items():
        if pname in have_v:
            continue
        p = unreal.CollectionVectorParameter()
        p.set_editor_property('parameter_name', pname)
        p.set_editor_property('default_value', unreal.LinearColor(*d))
        vectors.append(p)
        changed = True
    for pname, d in MPC_WORLD_SCALARS.items():
        if pname in have_s:
            continue
        p = unreal.CollectionScalarParameter()
        p.set_editor_property('parameter_name', pname)
        p.set_editor_property('default_value', d)
        scalars.append(p)
        changed = True
    if changed:
        mpc.set_editor_property('vector_parameters', vectors)
        mpc.set_editor_property('scalar_parameters', scalars)
    save(mpc)
    return mpc


def wire_wind(unreal, mat, expr, custom, link, out, env_mpc, world_mpc, push=True):
    """Adds the wind node graph to `mat` (same node positions as before) and outputs it to world position offset."""
    F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
    vc = expr(mat, unreal.MaterialExpressionVertexColor, -700, 1000)
    time = expr(mat, unreal.MaterialExpressionTime, -700, 1200)
    obj = expr(mat, unreal.MaterialExpressionObjectPositionWS, -700, 1280)
    amount = expr(mat, unreal.MaterialExpressionCollectionParameter, -700, 1360, collection=env_mpc, parameter_name='Wind')
    scale = expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1440, parameter_name='WindScale', default_value=1.0)
    wpo = custom(mat, -350, 1100, WIND_HLSL, F3, WIND_INPUTS, 'Wind offset (cm), walk-through bend and scatter thinning')
    link(expr(mat, unreal.MaterialExpressionCameraPositionWS, -700, 1520), '', wpo, 'Cam')
    link(expr(mat, unreal.MaterialExpressionWorldPosition, -700, 1600), '', wpo, 'WP')
    link(expr(mat, unreal.MaterialExpressionPerInstanceRandom, -700, 1680), '', wpo, 'Rnd')
    link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1760, parameter_name='ScatterFade', default_value=0.0), '', wpo, 'Fade')
    link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1840, parameter_name='FadeNearCm', default_value=1200.0), '', wpo, 'FadeNear')
    link(expr(mat, unreal.MaterialExpressionScalarParameter, -700, 1920, parameter_name='FadeFarCm', default_value=3700.0), '', wpo, 'FadeFar')
    y = 2000
    for pin, pname in (('WD', 'WindDir'), ('WG', 'WindGust'), ('P0', 'Push0'), ('P1', 'Push1'), ('P2', 'Push2'), ('P3', 'Push3')):
        link(expr(mat, unreal.MaterialExpressionCollectionParameter, -700, y, collection=world_mpc, parameter_name=pname), '', wpo, pin)
        y += 80
    link(expr(mat, unreal.MaterialExpressionCollectionParameter, -700, y, collection=world_mpc, parameter_name='WorldLife'), '', wpo, 'WL')
    link(expr(mat, unreal.MaterialExpressionConstant, -700, y + 80, r=1.0 if push else 0.0), '', wpo, 'PushOn')
    link(vc, '', wpo, 'VC'); link(vc, 'A', wpo, 'VA'); link(time, '', wpo, 'T'); link(obj, '', wpo, 'Obj')
    link(amount, '', wpo, 'Wind'); link(scale, '', wpo, 'Scale')
    out(wpo, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    return wpo
