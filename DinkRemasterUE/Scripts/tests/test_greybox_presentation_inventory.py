"""Frozen physical-builder invariants and generation wiring; actual geometry is covered by native tests."""
from pathlib import Path
import hashlib,unittest
P=Path(__file__).resolve().parents[2]
I=P/'Plugins/DinkImport/Source/DinkImport/Private'
C=P/'Plugins/DinkCore/Source/DinkCore'
class Tests(unittest.TestCase):
 def test_collision_hash_and_builders_keep_original_exact_bytes(self):
  s=(I/'DinkGreyboxAssets.cpp').read_text()
  a=s.index('\t\tconst FString GeoHash =');b=s.index('\n\n',a)
  self.assertEqual(hashlib.sha256(s[a:b].encode()).hexdigest(),'7f2a56728126dd0c9549a70a416f7d12413fb4e2b40222900fb4e88a74c91a2d')
  a=s.index('\t\t// collision: solid');b=s.index('\n\t\treturn true;',a)
  self.assertEqual(hashlib.sha256(s[a:b].encode()).hexdigest(),'8c6ab14248d72314242d4e13d1a458df1a683551e04f5c8ace10b48ade817ea5')
  s=(C/'Private/Greybox/DinkPlaceholderActor.cpp').read_text();a=s.index('\tCollisionSolid =');b=s.index('\n}\n',a)
  self.assertEqual(hashlib.sha256(s[a:b].encode()).hexdigest(),'baa856ed6f3215639e325e5f596f23747a4ada968e28d00ea499c83ff7b98daf')
 def test_visual_only_cache_and_actor_generation_salts(self):
  s=(I/'DinkGreyboxAssets.cpp').read_text();h=(I/'DinkGreyboxAssets.h').read_text();a=(I/'DinkGreyboxImporter.cpp').read_text()
  self.assertIn('AssetGeneratorVersion = TEXT("greybox-assets/3")',h)
  self.assertIn('TEXT("visual-ground-water/1"), GeoHash, MiPkg',s);self.assertIn('TEXT("debug-blockers/1"), GeoHash',s)
  self.assertEqual(a.count('greybox-ground-water-debug-split/1'),1)
  self.assertIn('A->DebugBlockers->SetStaticMesh(Assets.ScreenMesh(S.Screen, TEXT("DebugBlockers")))',a)
 def test_normal_material_inventory_excludes_blocker_materials(self):
  s=(I/'DinkGreyboxAssets.cpp').read_text();a=s.index('const FString VisualHash =');b=s.index('// An empty debug mesh',a);normal=s[a:b]
  self.assertIn('TEXT("Ground")',normal);self.assertIn('TEXT("Water")',normal);self.assertNotIn('MI_DinkBlocker',normal)
  self.assertIn('ShouldPruneUnusedDebugMesh(Pair.Key, C)',s);self.assertIn('bKeep = !bLowGone && !bDebugGone;',s)
  self.assertIn('if (Debug.Triangles > 0)',s);self.assertIn('if (!HasDebugBlockers(Coll)) return nullptr;',s)
 def test_no_physical_or_shadow_debug_authority(self):
  s=(C/'Private/Greybox/DinkPlaceholderActor.cpp').read_text();a=s.index('DebugBlockers =');b=s.index('CollisionSolid =',a);debug=s[a:b]
  for text in ['NoCollision_ProfileName','SetGenerateOverlapEvents(false)','SetHiddenInGame(true)','SetCastShadow(false)','SetCastHiddenShadow(false)','SetCanEverAffectNavigation(false)']:self.assertIn(text,debug)
  method=s[s.index('void ADinkGreyboxScreen::RefreshDebugBlockers()'):]
  self.assertIn('SetHiddenInGame',method);self.assertNotIn('CollisionSolid',method);self.assertNotIn('SetActor',method);self.assertNotIn('SetStaticMesh',method)
if __name__=='__main__':unittest.main()
