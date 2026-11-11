"""Portable production math and immutable shipped-default controls; no UE."""
import json,subprocess,tempfile,unittest,sys,re,hashlib
from pathlib import Path
P=Path(__file__).resolve().parents[2]
class FamilyCollisionFitTests(unittest.TestCase):
 def test_actual_production_convex_and_warped_raster_math(self):
  with tempfile.TemporaryDirectory(prefix='dink-family-fit-') as td:
   exe=Path(td)/'fit';subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fno-exceptions','-fno-rtti','-I',str(P/'Plugins/DinkCore/Source/DinkCore/Public'),str(P/'Scripts/tests/native/family_collision_fit.cpp'),'-o',str(exe)],check=True,capture_output=True)
   result=subprocess.run([str(exe)],check=True,text=True,capture_output=True);self.assertIn('PASS actual convex/raster/map boundary math',result.stdout)
 def test_actual_source_fbx_uses_fitted_projected_footprint(self):
  sys.path.insert(0,str(P/'Scripts'));import barrel_fbxparse as F
  source=P/'SourceAssets/Art/Stonebrook/Export/Game/Dink/Props/Stonebrook/SM_Barrel_Oak_01.fbx'
  _,nodes=F.parse(source);by={n.name:n for n in nodes};objects=by['Objects'];models={n.props[0]:n.props[1].split('\x00')[0]for n in objects.children if n.name=='Model'}
  geometries={n.props[0]:n for n in objects.children if n.name=='Geometry'};geometry=None
  for c in by['Connections'].children:
   if c.name=='C'and c.props[0]=='OO'and c.props[1]in geometries and models.get(c.props[2])=='SM_Barrel_Oak_01':geometry=geometries[c.props[1]]
  self.assertIsNotNone(geometry);v=geometry.first('Vertices').props[0]
  with tempfile.TemporaryDirectory(prefix='dink-family-fit-fbx-')as td:
   td=Path(td);points=td/'vertices.txt';points.write_text(''.join(f'{v[i]*100} {-v[i+1]*100} {v[i+2]*100}\n'for i in range(0,len(v),3)))
   exe=td/'fit';subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fno-exceptions','-fno-rtti','-I',str(P/'Plugins/DinkCore/Source/DinkCore/Public'),str(P/'Scripts/tests/native/family_collision_fit.cpp'),'-o',str(exe)],check=True,capture_output=True)
   result=subprocess.run([str(exe),str(points)],check=True,text=True,capture_output=True);self.assertIn('PASS actual FBX projected with production math',result.stdout)
 def test_shipped_families_data_keeps_real_size_and_explicit_policy(self):
  data=json.loads((P/'Content/Dink/Data/Art/families.json').read_text())
  policy=data['collision_fit']
  origins=[row['origin'] for row in policy['origins']]
  self.assertEqual(len(origins),len(set(origins)))
  if policy['schema']=='dink-family-collision-fit/1':
   self.assertEqual(set(origins),{'S031_P03','S209_P13'})
  else:
   self.assertEqual(policy['schema'],'dink-family-collision-fit/3')
   self.assertEqual(len(origins),85)
   self.assertEqual(sum(row['source_type']==0 for row in policy['origins']),3)
  barrel=next(r for r in data['families'] if r['family']=='barrel');self.assertEqual(barrel['fit'],'none');self.assertTrue(barrel['scripted']);self.assertFalse(barrel['yaw_from_sprite'])
  self.assertEqual(barrel['mesh'],'/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01')
  for row in policy['origins']:
   self.assertNotIn('geometry_sha1',row);self.assertEqual(row['surface_sha1'],'de0f514e0172077e7bbd9dc0b30c75f5c40939e6');self.assertEqual(row['surface_algorithm'],'DinkOrientedTrianglesF32LEMaterialU16LE/1')
 def test_frozen85_sources_exclusions_and_manifest_hashes(self):
  data=json.loads((P/'Content/Dink/Data/Art/families.json').read_bytes())
  expected=set(re.findall(r'TEXT\("([^"\n]+)"\)',(P/'Plugins/DinkParity/Source/DinkParity/Private/Tests/DinkBarrelRolloutSourcePins.inl').read_text()))
  actual={f"{r['origin']}|{r['source_hash']}|{r['source_script']}|{r['source_type']}" for r in data['collision_fit']['origins']}
  self.assertEqual(len(expected),85);self.assertEqual(actual,expected)
  for control in ('S060_P08','S060_P09','S060_P10','S063_P06','S063_P07','S096_P06','S222_P06','S222_P07','S222_P08','S224_P07','S439_P06','S439_P22'):
   self.assertNotIn(control,{r['origin'] for r in data['collision_fit']['origins']})
  gameplay=P/'Content/Dink/Data/Gameplay';manifest=json.loads((gameplay/'gameplay_manifest.json').read_bytes())
  targets={int(r['origin'][1:4]) for r in data['collision_fit']['origins']};self.assertEqual(len(targets),38)
  for screen in targets:
   self.assertTrue((gameplay/f'Hardness/Foundations/SCR_{screen:03}.json').is_file())
   names=[f'Hardness/SCR_{screen:03}{suffix}_layers.json' for suffix in ('','_v1','_v2')]
   for name in names:self.assertEqual(hashlib.sha256((gameplay/name).read_bytes()).hexdigest(),manifest['files'][name])
 def test_source_guide_and_drop_identity_are_unchanged(self):
  repo=P.parent;ini=(repo/'bin/dink/dink.ini').read_text(errors='replace');self.assertIn('173 75 41 44 -17 -15 20 6',ini)
  for name,item in [('bar-gh','gheart'),('bar-f1','food1')]:
   source=(repo/f'bin/dink/story/{name}.c').read_text();self.assertIn('&save_x = sp_x(&current_sprite, -1)',source);self.assertIn('&save_y = sp_y(&current_sprite, -1)',source);self.assertIn('external("make", "'+item+'")',source);self.assertIn('sp_hard(&current_sprite, 1)',source);self.assertIn('draw_hard_sprite(&current_sprite)',source)
 def test_no_physical_authority_or_automatic_visual_apply(self):
  family=(P/'Plugins/DinkCore/Source/DinkCore/Private/DinkArtFamilySubsystem.cpp').read_text();producer=(P/'Plugins/DinkCore/Source/DinkCore/Private/DinkFamilyCollisionFit.cpp').read_text()
  self.assertNotIn('ApplyCollisionFitVisual(',family);self.assertNotIn('PrepareCollisionFit(',family)
  self.assertIn('Authority.CanPublishVisual(C,Error)',producer);self.assertNotIn('ApplyScreenSolidChanges(',producer);self.assertNotIn('SetCollisionEnabled(',producer);self.assertNotIn('SetActorLocation(',producer)
if __name__=='__main__':unittest.main()
