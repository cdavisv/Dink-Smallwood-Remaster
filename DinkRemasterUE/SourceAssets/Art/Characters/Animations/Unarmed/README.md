# Dink forward fist — source animation candidate

One original hand-keyed comic cross for the existing anatomical Dink and exact89-bone project Manny-compatible skeleton. It adds presentation only. The original hero geometry/weights/assets, UVs, materials, outfits, collision, stats, original actor/script/save identity and all creature art remain unchanged; the separately named corrected-hand mesh is an isolated candidate. The delivered FBX contains an armature and animation only; the source `.blend` includes the separately authorized HandBindingV2 corrected-hand candidate as an explicitly labeled preview reference. The original SK_Dink files remain unchanged.

## Original timing and motion contract

Authoritative `bin/dink/story/item-fst.c` maps diagonal facing1/3→2 and7/9→8, sets `sp_seq(1,100+direction)`, resetsframe1, calls `sp_kill_wait`, and sets `sp_nocontrol(1,1)` until the logical animation completes. Sound8 follows the script's1ms wait. `dink.ini` and extracted/copied `frames.csv` agree for all four fist sequences102/104/106/108:

| Original frame | Duration | Begins | Meaning |
|---|---:|---:|---|
|1|75ms|0ms|ready / motion begins|
|2|100ms|75ms|wind-up|
|3|75ms|175ms|special hit frame|
|4|75ms|250ms|recoil|
|5|75ms|325ms|return|

The new animation is exactly0.400s,40fps,frames1–17; impact isframe8 at0.175s. The motion follows original106's shoulder-led forward cross with opposite arm counterbalance. Feet remain stationary, the root remains identity/in-place, and the original idle pose is restored at the end. Finger flexion, index adduction, wrist pronation and thumb opposition are hand keyed; they do not alter hero binding. The old hand binding formed an unacceptable ring gesture; the separate HandBindingV2 per-digit fit/weight correction removes that opening. Tiny angular thumb-web/knuckle folds remain close-view candidate polish. The clip should be reviewed with SK_Dink_Hands, not used to claim that the original hand binding was corrected.

`FDinkGameplayData::HitFrameDelayMs` sums75+100ms, and `UDinkGameplay::OnSequenceSet` schedules the existing pending hit independently of skeletal playback. Native logical completion is tick-quantized;400ms is the source authored duration, not a promise of an exact wall-clock input-unlock instant. No AnimNotify, collision sweep or skeletal fist position is allowed to replace damage authority or alter reach. Original `sp_seq`/frame/state remain the trigger; the Unreal integration must preserve the current locomotion AnimBP and original script behavior.

## Idle boundary and provenance

`idle_boundary_pose.json` caches the evaluated first pose of the existing project asset `/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle`, exported by the project's existing reference workflow. Both source endpoints match it. The exported animation preview uses Quinn, but its evaluated animated joint distances match Manny's actual rig (upper arm0.277707m/forearm0.272510m); the generator copies evaluated component matrices onto the existing Dink rig, never the preview mesh or its rest proportions. The identity root is retained explicitly. The cached source FBX SHA256 is recorded.

The new punch, counterbalance and finger keyframes are original project-authored motion. The shared rig and idle boundary are existing Epic project content and retain their own Epic terms; they are not relabeled as CC0/original anatomy. The existing Dink anatomical preview comes from the project's documented CC0 MakeHuman body/hair plus original project clothes; see `../../README.md` and character provenance. No Epic robot geometry is saved in this source or exported. No paid generation or new mesh/texture downloads were used.

## Reproduce and inspect

From the Unreal project root:

```
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Characters/Animations/Unarmed/Tools/build_fist.py
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Characters/Animations/Unarmed/Tools/export_fist.py
python3 SourceAssets/Art/Characters/Animations/Unarmed/Tools/inspect_fist.py
python3 SourceAssets/Art/Characters/Animations/Unarmed/Tools/prepare_fist_ledger.py
```

The generator uses the cached idle pose. If regenerating that reference, `DINK_IDLE_REFERENCE` can point to a fresh official project idle FBX when the cache is absent; source extraction is not a live-game operation. `Dink_Fist.blend` stays in metres with original89 rest transforms and unchanged existing texture references rebased to the Characters folder. `Previews/fist_windup.png`, `fist_impact.png`, `fist_impact_side.png`, `fist_recoil.png`, `fist_idle.png` and `fist_end.png` show the reviewed pose sequence.

The export process alone becomes a temporary centimetre scene: edit-bone coordinates and animated location keys/handles×100, scene scale0.01, FBX_SCALE_ALL/header1cm, identity root, Armature wrapper, no leaf bones, no mesh/material export. Source `.blend` is never overwritten by this conversion. `animation_manifest.json` describes the separate local import contract and does not mutate the shared character manifest. `fist_source_report.json`, `fist_validation.json` and `fbx_inspection.json` record impact timing, all-frame finite/unit-scale/root/foot/joint/end checks and independent binary-FBX unit/hierarchy/key-span checks. Unreal import, cosmetic playback and actual-keyboard combat QA remain separate staged integration checks; source checks do not claim them complete.

The art plan's hand-keyed combat/comedy and recognisable Dink identity informed this motion. Current hero outfit still differs from the guide's brown jerkin/backpack, grey-blue sleeves, olive trousers and red bracers; that is a later explicit wardrobe task, not part of this animation delivery. Local ledger rows remain candidate pending staged review; the shared ledger is parent-coordinated.

The separate `Scripts/import_hero_animation.py`/`.sh` bridge resolves the real shared Skeleton through verified `SK_Dink.skeleton`, validates its type and89-bone rig, imports only `AN_Dink_Fist`, and checks native duration/root/scales/finite/endpoints before saving that animation. Shared Skeleton package SHA and original mesh rest poses must remain unchanged. On success it atomically publishes optional `Art/hero_actions.json` with the four original sequence IDs,400ms duration and175ms documentary impact. Initial runtime playback restores the original AnimBP; no timed-blend promise or damage authority is encoded. Import is parent-controlled and must wait for editor-slot release.

Staged import checkpoint (7Nov2026): the clip imported successfully after correcting a validation-category error. Native `InspectCreatureAnimation.bone_count` counts the full shared USkeleton (161), while SK_Dink and this source clip each use89 bones/tracks. The importer now requires exact89 AnimationDataModel track-name equality with the source and verified mesh, and independently compares the entire161-bone shared reference inventory/poses and package hash before/after. All duration/root/scale/endpoint gates remain strict. Actual imported duration0.40000000596s, root motion0, scale error0.00001705 and endpoint translation0/rotation2.98e-8rad passed. Staged import is asset validation; it does not claim live keyboard punch/rendered combat QA. The first rejection log and diagnosis are preserved separately, not discarded.
