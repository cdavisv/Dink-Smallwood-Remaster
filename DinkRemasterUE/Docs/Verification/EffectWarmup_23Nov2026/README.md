# One-shot effect materials warmed at screen entry (23 Nov 2026)

Seen by art-fx-2 / art-people-2 in the rendered game (Master log 23 Nov 07:50, frame 06_dialogue_10 on SCR_086): the 161
fire burst that s7-mil.c:125-126 creates when Seth casts on Milder showed as a WHITE rectangle at its first use. Its atlas
has no white frame (all 32 checked by art-fx-2).

## Cause, confirmed in code
- The card: UDinkArtFamilySubsystem dresses a script-made 161 sprite with a UMaterialBillboardComponent holding a dynamic
  instance of MI_FX_Atomic (families.json row `161 effects/atomic/atomc-`); the effect materials are loaded at world begin.
- The captures run the editor binary with `-game` on uncooked content (Scripts/PhotorealQA/run_capture.sh), and each
  private copy has its own DerivedDataCache, so shader maps compile in the background while the game runs.
- Engine, MaterialShared.cpp (FMaterial::GetShaders, 5.8.4): a shader missing from a material's shader map at draw time
  sets bMissingShader and requests a compile (ForceLocal); the render proxy then draws with the default surface material
  (FMaterialRenderProxy fallback): a flat grey-white card the size of the effect. A one-shot drawn for the first time
  while its material is still compiling is exactly that.
- Cooked games have every shader; there the billboard precaches its PSOs when it gets a material
  (MaterialBillboardComponent.cpp AddElement -> PrecachePSOs) and the proxy waits for them
  (r.PSOPrecache.ProxyCreationStrategy 1, PSOPrecache.cpp), so the first frames of a one-shot could be skipped instead.

## What changed
- `UDinkArtFamilySubsystem::WarmEffects()`, at every screen entry (before the screen is dressed):
  1. rendering builds only: every effect material whose shader map is still compiling has its compile finished
     (FMaterial::FinishCompilation; a no-op in a cooked game and when nothing is pending);
  2. once: a hidden, collision-free billboard of the same class as the effect cards holds every effect material, so
     their PSOs are requested ahead of the first use.
- Presentation only; nothing under -nullrhi (FApp::CanEverRender); the probe md5s cannot move.

## Proof
- `Dink.Art.Family.EffectMaterialsWarmedAtScreenEntry` (PIE on the real world): the warm card exists after the first
  screen entry, holds every effect material of families.json once (the 161 burst among the one-shots), is never drawn,
  has no collision; a second warm-up has nothing left to compile and makes no second card.
- Build 0 warnings, full Dink suite and probe: see the PR text.

## Not checked (why this PR stays open)
- The white card itself: needs the rendered game (RENDER_PENDING line: Seth's scene on SCR_086 in a FRESH copy, i.e.
  with an empty DerivedDataCache, frame of the 161 burst at s7-mil.c:125).
