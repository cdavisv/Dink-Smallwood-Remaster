"""Write <Char>/manifest.json from the export report and the delivered files. usage: write_manifest.py <CharDir> <Name> <json extra>"""
import sys, json, hashlib
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
d = Path(sys.argv[1]); name = sys.argv[2]; extra = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else {}
rep = json.loads((d / 'export_report.json').read_text())
tex = []
for p in sorted((d / 'Textures').glob('*.png')):
    im = Image.open(p); tex.append({'file': 'Textures/' + p.name, 'size': list(im.size), 'mode': im.mode})
slots = rep['materials']
def tx(k): return {s: f'Textures/T_{name}_PR_{k}_{s}.png' for s in ('BC', 'N', 'ORM')}
m = {
 'schema': 'dink-photoreal-character/1', 'asset': rep['asset'], 'class': extra.get('class', 'character_hero'),
 'source_blend': f'{d.name}/SK_{name}_Photoreal.blend',
 'fbx': [f'Export/{rep["asset"]}_LOD{i}.fbx' for i in range(4)],
 'dimensions_m': rep['dimensions_m'], 'bone_count': rep['bone_count'], 'root_bone': 'root',
 'skeleton': '/Game/Characters/Mannequins/Meshes/SK_Mannequin (89 bones, names/hierarchy/rest pose unchanged from Characters/Dink/HandBindingV2)',
 'lods': rep['lods'], 'lod0_triangles': rep['lods'][0]['triangles'],
 'material_slots': slots,
 'materials': {
   slots[0]: {'textures': {**tx('Skin'), 'SSS': f'Textures/T_{name}_PR_Skin_SSS.png'}, 'shading': 'subsurface profile / skin; SSS.rgb = scatter colour x thickness', 'normal': 'OpenGL (+Y), flip green for UE as the existing importer does'},
   slots[1]: {'textures': tx('Eyes'), 'shading': 'default lit, low roughness from ORM.G; single-shell eye with modelled cornea bulge'},
   slots[2]: {'textures': {**tx('Hair'), 'FLOW': f'Textures/T_{name}_PR_Hair_FLOW.png', 'MSK': f'Textures/T_{name}_PR_Hair_MSK.png'},
              'shading': 'hair shading model, MASKED (alpha in BC.a, clip about 0.33 with dithered opacity / TAA), two-sided; cap shell + lock cards + brow and lash cards in one slot',
              'anisotropy': 'FLOW.rg = strand direction in UV space, encoded 0.5 + 0.5 * d (root to tip): world tangent = normalize(d.x * dP/du + d.y * dP/dv); use it as the hair tangent / anisotropy direction so highlights run along the hair. Baked from the strand groom (cap rect) and from the strand clumps (card tiles). N is the strand-relief normal (OpenGL), ORM.r = strand depth occlusion, ORM.g = roughness.',
              'masks': 'FLOW.b = back-light mask (0 on the opaque cap shell, 1 on cards: scale back-scatter / two-sided transmission by it). MSK.r = strand depth, MSK.g = per-strand id (use for per-strand colour / roughness jitter), MSK.b = root-to-tip gradient (0 root, 1 tip; the BC already carries a root-dark to tip-light gradient).',
              'atlas_layout': 'uv: cap texture u 0-0.5, v 0.5-1 (whole groom projected about the head centre, opaque under-fill inside the hairline); 32 narrow lock tiles u 0.5-1, v 0.25-1 (root at top); 4 wide tiles u 0-0.5, v 0.25-0.5; brow groom band u 0-0.5, v 0-0.25; lash band u 0.5-1, v 0-0.25',
              'shell_order': 'vertex attribute hl (also the build order, inner first): 1 = cap shell (opaque, never drop, casts the shadow), 2 = mid lock cards, 3 = outer lock cards, 4 = brows and lashes, 5 = hairline wisps and flyaways. LOD1 keeps all, LOD2 drops 5, LOD3 keeps 1, 3, 4. Custom split normals are scalp-blended and exported in the FBX: import normals, do not recompute.'},
   slots[3]: {'textures': tx('Outfit'), 'shading': 'default lit'},
   slots[4]: {'textures': tx('Gear'), 'shading': 'default lit, metallic from ORM.B (buckles)'}},
 'textures': tex, 'validation': rep['validation'], 'validator_findings': rep['findings'],
}
m.update(extra)
(d / 'manifest.json').write_text(json.dumps(m, indent=1) + '\n')
print('manifest', d / 'manifest.json')
