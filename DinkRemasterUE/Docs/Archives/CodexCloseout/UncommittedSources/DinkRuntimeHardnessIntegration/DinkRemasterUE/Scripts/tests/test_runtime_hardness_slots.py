"""Owned CPU-only adapter/core fixtures. No UE, generated Data or assets."""
from pathlib import Path
import subprocess,tempfile,unittest
P=Path(__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 def test_actual_original_slot_and_projected_admission_core(self):
  with tempfile.TemporaryDirectory(prefix='dink-hardness-slots-')as td:
   exe=Path(td)/'slots'
   subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fno-exceptions','-fno-rtti','-I',str(P/'Plugins/DinkNarrative/Source/DinkNarrative/Public'),str(P/'Scripts/tests/native/runtime_hardness_slots.cpp'),'-o',str(exe)],check=True,capture_output=True)
   out=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
   self.assertIn('PASS original slots/base-main/mixed-vs-draw',out.stdout)
 def test_production_phase_hook_order_and_no_ue_handle_renumber(self):
  story=(P/'Plugins/DinkNarrative/Source/DinkNarrative/Private/DinkStorySubsystem.cpp').read_text();start=story.index('void UDinkStorySubsystem::OnScreenEntered');part=story[start:story.index('void UDinkStorySubsystem::EnterScreenPlacements',start)]
  self.assertLess(part.index('BeginOriginalHardnessScreen'),part.index('StartProcedure(BaseScript'))
  part=story[story.index('void UDinkStorySubsystem::EnterScreenPlacements'):story.index('void UDinkStorySubsystem::UpdatePlayerPush')]
  self.assertLess(part.index('PrepareOriginalHardnessPlacements'),part.index('HandleForActor'))
  self.assertLess(part.index('FinishOriginalHardnessPlacements'),part.index('StartProcedure(S->Script'))
  self.assertIn('const auto Placements=Gameplay->GetData().GetPlacementsOnScreen(Screen)',part)
  adapter=(P/'Plugins/DinkNarrative/Source/DinkNarrative/Private/DinkRuntimeHardness.cpp').read_text()
  self.assertIn('Session::CreateProjected(HardnessProjection->Map',adapter)
  self.assertIn('Live.push_back({*Slot,Owner',adapter)
  self.assertNotIn('Live.push_back({S.Handle,',adapter)
  self.assertNotIn('GetHardbox(',adapter)
  begin=adapter[adapter.index('bool UDinkGameplay::BeginOriginalHardnessScreen'):adapter.index('bool UDinkGameplay::UsesOriginalHardnessProjection')]
  self.assertLess(begin.index('RequiresScreenCapability'),begin.index('FDinkRuntimeHardnessSource Source'))
  self.assertLess(begin.index('SelectActivation'),begin.index('AcquireOrRearm'))
  self.assertIn('AdmitRuntimeHardness(Screen,InitialVision,Owner,Error)',begin)
  vision=adapter[adapter.index('void UDinkGameplay::OriginalHardnessVisionChanged'):adapter.index('bool UDinkGameplay::AdmitRuntimeHardness')]
  self.assertLess(vision.index('AcquireOrRearm'),vision.index('AdmitRuntimeHardness'))
  self.assertNotIn('FindInitSequence',adapter)
  self.assertIn('HardnessProjection->Vision:Vision',adapter)
  forced=story[story.index('bool UDinkStorySubsystem::ForceOriginalHardnessVision'):story.index('void UDinkStorySubsystem::OnScreenEntered')]
  self.assertLess(forced.index('PreserveForceVisionCaller'),forced.index('OnScreenEntered(Caller.Screen,true,Vision)'))
  self.assertIn('Screen == LastScreen && !bForceVisionRebuild',story)

  self.assertIn('!Gameplay->IsHardnessLoading()',story)
  self.assertIn('if(Gameplay&&Gameplay->IsHardnessLoading())return;',story)

if __name__=='__main__':unittest.main()
