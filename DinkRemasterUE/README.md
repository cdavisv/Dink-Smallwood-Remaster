> This Unreal project lives in `DinkRemasterUE/` inside `cdavisv/Dink-Smallwood-Remaster`. Run the commands below from this directory. Extraction tools, the original game and the design bible live in the parent directory. The older standalone/sibling checkout layout remains supported.

# Dink Smallwood Remaster (Unreal Engine 5.8)

A free fan remaster of Dink Smallwood (1997) as a third-person 3D game, built with Unreal
Engine 5.8. The Unreal project lives inside the
[Dink-Smallwood-Remaster repository](../), alongside the design documents, original game data
and extraction pipeline. Read [the remaster plan](../doc/remaster/REMASTER_PLAN.md) first.

Status: pre-production. There is C++ gameplay core (quest facts, world state, origin IDs, the
original combat maths, inventory and save) with automated tests, and a headless importer that
turns the original world into a walkable 3D greybox (every screen, placement, warp and blocker of
the 1997 map, a third-person character at Dink's start). The original scripts, converted to Ink,
run in the greybox: Dink's mother greets you on a new game, NPCs talk with their original words
and menus, and their choices write the original quest facts. The original engine's gameplay rules
decide when scripts run: hitting things (a minimal fist attack), touching pickups and enemies,
pushing, deaths with their drops and experience, items and spells, level-ups. Every creature and
townsperson runs its original "brain" (monsters wander, chase and attack Dink, villagers, ducks and
pigs wander, missiles stop at walls), locked fights close the screen's exits until the last monster
dies, and an optional, data-driven 3D layer telegraphs attacks and limits attackers to two. The starting house and yard have an authored Blender art pass, with new Dink and mother character candidates. Combat animation and the wider world remain unfinished. The owner’s selected44SFX and28music cues are imported and play through the approved audio layer; four rejected sound effects remain excluded. Review/import details are in [SourceAssets/Audio/README.md](SourceAssets/Audio/README.md).

## Build and test (Linux, headless)

```
git lfs install --local
git lfs pull                            # fetch the versioned art/audio before building
python3 Scripts/verify_sources.py        # verify source syntax and every asset hash
Scripts/build.sh    # compiles DinkRemasterEditor (Linux, Development), about 30 s from clean
Scripts/test.sh     # runs the "Dink" automation tests with no display (see AGENTS.md for the count and time)
python3 Scripts/sync_story.py   # copies the converted Ink story from the data repository (after it changes)
python3 Scripts/sync_gameplay_data.py   # copies map.dat's sprite fields and dink.ini's hardboxes (after the data repo's dinkex output changes)
```

Both print one summary line and exit non-zero on failure. They expect the engine at
`~/UnrealEngine/UE_5.8.4` (override with `UE_ROOT`). See `AGENTS.md` for details, conventions and
known Linux issues.


Binary assets use **Git LFS**, as chosen by the owner. The source audit reads expected binary hashes from Git’s staged LFS pointers. `verify_sources.py --metadata-only` validates pointer metadata in a source-only checkout; the default requires and hashes the actual binary bytes.

The existing [development release pack](https://github.com/cdavisv/Dink-Smallwood-Remaster/releases/tag/unreal-house-assets-20261108-v1) is a historical recovery copy of the starting-house revision. It is optional, and is not the primary asset storage. If recovering that exact revision offline, `python3 Scripts/bootstrap_asset_pack.py --archive /path/to/unreal-house-assets-20261108-v1.tar.gz` verifies all bytes and refuses to overwrite modified local art.

## Walk the greybox

The extraction tools' outputs must be built in the parent repository (or in the older sibling data repository); see the parent `AGENTS.md`.

```
Scripts/build.sh
Scripts/import_greybox.sh --region stonebrook   # about 1 minute the first time (bundle export + import + tests)
Scripts/import_greybox.sh --region all          # the whole world, about 45 s more
```

Then open the project in the editor, File > Open Level >
`Content/Dink/_Generated/Maps/L_Greybox_World` (or `L_Greybox_Stonebrook`) and press Play. You
start in Dink's house. WASD and mouse to run (6 m/s); the line at the top left names the original
screen you are on. Console commands: `dink.Goto <screen>` jumps to any original screen,
`dink.Vision <screen> <value>` shows a quest-state variant (try `dink.Vision 1 2`), `dink.Where`.

## See a conversation

Press Play in `L_Greybox_Stonebrook` (or `_World`). On a new game Dink's mother (in the house
with you) runs her original `main`: after a second "Dink, would you go feed the pigs?" floats over
her in her colour, Dink answers, and you cannot walk until the scene ends. Space, Enter or E skips a
line. Then walk up to her and press **E**: her talk menu opens in the middle of the screen
(Up/Down or W/S and Enter, or the number keys). Other scripted placements talk the same way, e.g.
farmer SmileStein (placement `S003_P23`, `dink.Goto 3`). The mother's scene and talk have been checked in automated PIE tests and on the rendered desktop with the E key.

Console (`~`): `dink.Run <script> <procedure> [S001_P26|handle]` runs any converted procedure
(`dink.Run s1-h1-m talk`), `dink.Say <text>` makes Dink say something, `dink.Fact <name> [value]`
reads or writes a quest fact by its original name (`dink.Fact story`, `dink.Fact gold 500`),
`dink.Choose <n>`, `dink.Skip`, `dink.Story` (running scripts, texts, audio cues, errors),
`dink.ScreenScripts 0|1` (run screen `main` procedures on entry, default 1), `dink.SmokeRun`
(the whole-story smoke run, report in `Saved/Narrative/smoke_report.txt`). Approved music and sound cues play through the audio layer and are also logged (`LogDinkAudio`).

Everything the importer writes lives in `Content/Dink/_Generated/` (git-ignored, regenerable, never
edited by hand). `Saved/Import/coverage.csv` lists every original screen, placement and warp and
what it became. The questions the greybox should answer, and what is checked automatically versus
by eye, are in `AGENTS.md`, section "Greybox import".

## Play the gameplay rules

In `L_Greybox_Stonebrook`: **F** (or Left Ctrl) attacks with the armed item (fists on a new game;
the hit lands on the attack animation's hit frame, about 0.2 s later, 28 px of the original screen
in front of Dink), **Q** (or Left Shift) casts the armed spell, **E** talks. Walk onto the sack of
pig feed in Dink's house to pick it up; `dink.Inventory` lists items, `dink.Arm 2` arms slot 2 (or
`dink.Arm item-pig`), `dink.ArmMagic 1` arms a spell (there is no inventory screen yet). Hit the
furniture in the houses (`S002_P21`, `S003_P16`), the pillbugs south of the village (`dink.Goto 278`)
or the AlkTree (`dink.Goto 474`). Dink’s fist action uses the authored animation with the original hit timing. Dying enemies
and vanishing pickups still use provisional presentation. Fireballs are a placeholder cylinder (they stop at walls and
fly over water). `dink.Attack`, `dink.Magic` and `dink.Seed <n>` do the same from the console.

Enemies and townsfolk move by the 1997 engine's rules ("Classic", in the original screen's pixels):
the placeholder cards slide around. Hit a Bonca (`dink.Goto 29`) and it chases you and swings; its
hit lands on its attack animation's hit frame. A locked fight (`dink.Goto 302`, two Boncas) raises
grey slabs on the screen's open edges until both are dead (sound 43 in the audio log). The 3D
adaptation layer is on in play: before each attack a red sphere over the monster marks a 0.45 s
wind-up, and at most two monsters attack you at once; its numbers are in
`Content/Dink/Data/AI/adaptation.ini` (`Enabled=0` gives the original's rules).

## Authored Blender art and rendered playtests

The starting house now has an authored 3D environment: oak floors and ceiling, timber-and-plaster walls, windows and an open doorway, furniture, a stone hearth, barrels, feed sack and pie. Sources and rebuild instructions are in [SourceAssets/Art/README.md](SourceAssets/Art/README.md). The player and mother now use authored humanoid candidates with CC0 anatomy, original clothing and four actual LODs, retaining the existing animation rig and original scripts. The initial art pass is documented in [Characters/README.md](SourceAssets/Art/Characters/README.md); fine clothing polish, the house-fire variants and wider world remain in progress.

```
Scripts/import_stonebrook_art.sh        # import Blender kit, PBR materials, scale and collision settings
Scripts/import_stonebrook_exterior.sh   # cottage yard, after its Blender export exists
```

`UDinkArtSubsystem` applies the text manifests under `Content/Dink/Data/Art/` at play startup. It keeps original origin IDs and scripts, replaces the dressed screens' collision with the authored meshes, and leaves generated maps regenerable. For a greybox comparison, set `dink.ArtEnabled 0` in the console and reload the map with `open /Game/Dink/_Generated/Maps/L_Greybox_World`; use `dink.ArtEnabled 1` before reloading to restore art. The imported art uses source material maps with sRGB base colour, linear ORM, flipped OpenGL normal green, and restrained normal strength. The importer explicitly controls FBX units on repeated imports and rejects a scale mismatch.

A player collision regression now walks around the furniture, out of the house, through the outside door, and back to the starting side. It caught both the original oversized capsule and a synchronous warp-overlap bounce on reentry. The imported physical dimensions are tested separately. Real desktop keyboard routes, screenshots and interaction checks complement the headless suite; see [Scripts/Playtest/README.md](Scripts/Playtest/README.md). Evidence is in `Saved/Playtest/evidence` and `Saved/Playtests/Collision`.

## Layout

| Path | What |
|---|---|
| `DinkRemaster.uproject` | Project file (UE 5.8) |
| `Source/DinkRemaster` | Thin primary game module |
| `Plugins/DinkCore` | Runtime rules: facts, world overrides, origin IDs, stats/combat, inventory, save; the layout transform; greybox actors (screen volumes, placeholders, warps, character) |
| `Plugins/DinkParity` | Developer-only automation tests: original rules (`Dink.Core`), the import (`Dink.Import`), the story runtime (`Dink.Narrative`), the gameplay triggers (`Dink.Gameplay`, including a scripted Stonebrook playthrough in PIE), the brains (`Dink.AI`) |
| `Plugins/DinkNarrative` | Story runtime: the converted Ink story, script instances, the director that runs its commands, the original engine's gameplay rules (hit, touch, push, death, drops, items, magic, status) and brains (AI), floating text and menus; `Docs/director_status.csv` lists every command's status |
| `Plugins/Inkpot` | Third-party: the InkPlusPlus C++ Ink runtime from The Chinese Room's Inkpot (MIT), see `AGENTS.md` |
| `Plugins/DinkImport` | Editor importer: import bundle to the greybox (commandlets `DinkImportGreybox`, `DinkGreyboxCapture`) |
| `Plugins/DinkExpanded` | Content plugin for non-original content (disabled) |
| `Content/Dink/Data` | Text data read at run time: the original globals table, `Story/dink.json` (the compiled Ink story) and its name tables, `Gameplay/` (map.dat sprite fields, dink.ini frames, screen base scripts, every screen's hardness map), `AI/adaptation.ini` (the 3D adaptation layer's numbers) |
| `Content/Dink/_Generated` | Greybox generated by the importer (git-ignored) |
| `ImportData` | Import bundle exported from the data repository (git-ignored) |
| `Scripts` | Build, test, data-regeneration (`regen_globals.py`, `sync_story.py`, `sync_gameplay_data.py`), bundle export, import and capture scripts |

## Licence and rights

`Plugins/Inkpot` is third-party code under the MIT licence (`Plugins/Inkpot/LICENSE`,
Copyright (c) 2023 The Chinese Room).

Dink Smallwood is by Robinson Technologies (RTsoft). This remaster is a free fan project; the
rights position (permission, credits, asset ledger) is in section 0 of the data repository's
plan. Check it before distributing anything.


The 7 Nov2026 verified build passes103/103 automation tests, with one unrelated engine HTTP connectivity warning. Rendered keyboard checks pass all12 interaction cases and the exit/yard/return route; actual approved music and swing effects were captured from the game mixer. The stable report is `Saved/Automation/final_all_verified/index.html`; screenshots/audio/launch receipts are in `Saved/Playtest/evidence`. This validates the current starting-area pass, not a finished world or complete Terris playthrough.

Fireplace source import supports `DINK_FIREPLACE_MODE=check` and `publish`. If an unpublished import was interrupted, restore its approved source bytes and use `DINK_FIREPLACE_MODE=resume Scripts/import_fireplace_refinement.sh`; this backs up and rebuilds only its six unique candidate packages. Resume refuses a published runtime refinement. Source bytes must match the ledger before import, check, render configuration or publication.
