# Expanded content: DinkExpanded (15 Nov 2026)

The owner's order of 15 Nov 2026 (22:00): after the 1997 map is enlarged (stream `feat/world-scale`), keep expanding with
additional content, "like DLC areas". The plan already fixes the frame: REMASTER_PLAN pillar 5, "Base game is sacred,
expanded content is additive and lives in a separate plugin that can be switched off", section 11 (the waves), and the
beta gate, "Parity tests pass with `DinkExpanded` off".

This document is the architecture of that plugin, the content slate per pack, and the first playable greybox slice
(Murkwood Deep). Everything under section 6 that a character says is a **draft for the owner's approval**.

## 1. Rules

1. **Nothing of 1997 changes.** No 1997 tile, hardness pixel, placement, script, global or line is edited by a pack. A pack
   adds screens, placements, scripts and globals in its own namespace, and attaches to the 1997 world by designed joins
   that are overlays only.
2. **Off means off.** The switch is off by default. Off, the plugin hooks nothing: the 1997 story, tables and world load
   byte-for-byte as without the plugin (section 2.1). The plugin can also be disabled in `DinkRemaster.uproject`; the 1997
   code never depends on it.
3. **On is still the 1997 game until a pack is entered.** With packs on, the probe and every `Dink.*` test must pass with
   the same results. A pack touches no 1997 story global and draws nothing from the shared random stream until the player
   walks through one of its joins (section 2.8).
4. **Saves cross the switch.** A 1997 save loads with packs on or off. A save made inside a pack loads with packs off into the
   1997 world at the join's 1997 side, without the pack's script state (section 2.7).
5. **The 1997 tone, gore and dark comedy, never sanitised** (owner rule). New lines are written in Dink's voice: short,
   rude, self-satisfied, the joke undercut by the next line. Death, blood and bodies at least at the 1997 level.

## 2. Architecture

```
Plugins/DinkExpanded/
  DinkExpanded.uplugin            module DinkExpanded (Runtime), depends on DinkCore + DinkNarrative
  Packs/<pack>/pack.toml          a pack: sheets, screens (greybox solids), placements, joins
  Packs/<pack>/story/*.c          its DinkC scripts (x<n>-*.c)
  Content/Data/                   what tools/expanded builds from Packs/ (tracked; never hand-edited)
    packs.json                    the registry the module loads
    Gameplay/placements.csv       the packs' placements (1997 header, origin S<screen>_P<index>)
    Gameplay/screens.csv          the packs' screens and base scripts
    Gameplay/Hardness/SCR_nnn.txt the packs' screens' hardness (the 1997 RLE format)
    Story/dink.json, names.csv    the 1997 story plus the packs' knots and VARs
    lines.csv                     every pack line, status "draft, owner to approve"
    manifest.json                 counts and hashes (incl. the 1997 story's sha256 the merge was made from)
  Source/DinkExpanded/            switch, registry, layout, world builder, joins, saves, tests (Dink.Expanded.*)
tools/expanded/                   the pack builder (python3 -m expanded build) and its tests; probe_parity.py
```

### 2.1 The switch

Read once when the module starts, in this order (later wins): `[DinkExpanded] Enabled=True|False` in Game.ini (default
False; `Packs=a,b` limits the packs, default all built packs), the environment `DINK_EXPANDED=0|1`, the command line
`-DinkExpanded=0|1` (`-DinkExpandedPacks=a,b`). The console command `dink.Expanded` prints the state; `dink.Expanded 1
[packs]` writes the user Game.ini and applies at the next start (the story and the tables load when the game instance
starts, so a running game is never switched under its own feet).

On, the module sets exactly two hooks in DinkNarrative and creates two subsystems:

| Hook / subsystem | What it does | Off |
|---|---|---|
| `FDinkInkStory::StoryDataOverrideDir()` | the story loads `Content/Data/Story/dink.json` and `names.csv` (the merged story) | empty: `Content/Dink/Data/Story` |
| `FDinkGameplayData::ExtraDataDirs()` | the pack rows are appended after the 1997 rows of `placements.csv` and `screens.csv` (header must be identical); a pack screen's `Hardness/` file is found in the pack dir (1997 screens have their own, so they never resolve there) | empty: 1997 tables only |
| `UDinkExpandedWorldSubsystem` | when a game world begins play: builds the pack screens beyond the 1997 world (2.4) and the join triggers (2.5) | not created |
| `UDinkExpandedGameSubsystem` | rewrites a save made on a pack screen (2.7) | not created |

The only other 1997-side change is generic: `UDinkStorySubsystem::LoadStateFromJson` leaves out the instances (and their
Ink flows, texts and menu) of scripts the loaded story does not hold, with a warning. It is what lets a pack save load with
packs off, and it equally protects a save across a story version that renamed a script.

### 2.2 Content packs: data plus DinkC

A pack is a directory with a `pack.toml` and DinkC scripts. DinkC rather than hand-written Ink: the pack scripts go
through the same converter as the 380 1997 scripts (`tools/dinkc` -> `tools/dinkink` -> inklecate), so they run on the
same director with the same commands, the same blocking rules, the same menu numbering and the same line ids
(`x3-burt.talk.004`) the voice pipeline keys on. A modder writes the language the game was written in.

`python3 -m expanded build` (in `tools/expanded`, about 6 s) checks every rule below against the 1997 data the project
ships and writes `Content/Data`. `--check` writes nothing and fails when the output is stale; the unit test
`TestCommittedOutput` does the same. The merge (2.6) refuses to run when the converter's 1997 knots differ from the shipped
story (sync the story first).

### 2.3 Namespaces

| Thing | 1997 | Pack n (1-9) | Checked by |
|---|---|---|---|
| Screen numbers | the 644 with a map.dat record | **unused 1997 map slots** (124 exist: no map.dat record, no 1997 script names them) | build (screens.csv, every `&player_map =` in bin/dink/story), runtime (1..768, unique) |
| Origins | `S412_P03` | `S<slot>_P<nn>` on the pack's own screens | build, runtime |
| Scripts | `s1-h1-m` | `x<n>-*` (and 1997 creature scripts may be reused, e.g. `en-pill1`) | build, runtime |
| Globals / facts | `&story`, `&s2-nad` ... | `&x<n>_*`, initial value 0 | build (make_global_int), merge |
| Script locals | `s1_h1_m__crap` | `x<n>_<script>__<local>` (the converter's naming) | merge |
| Warp ids | `S419_P02` | `XJ_<join>_in` / `_out`, kind `pack_join` | runtime |
| Art queue rows | VS-, GP- ... | `EX-` | this doc |

Why unused 1997 slots as screen numbers: the whole 1997 runtime (origin ids `Snnn_Pnn`, `FDinkOriginId::MaxScreen` 768, the
hardness sessions, the save's override table) keys on 1..768. Using the free slots makes a pack screen a first-class screen
for the director, the brains, the hardness and the saves with no change to any of them. The slot number says nothing about
where the screen is (2.4). The 124 slots are enough for the slate below (about 90 screens); when they run out, the
extension is to raise the range (4-digit origin text) in one change, not per pack. **Claim:** the stream that enlarges the
map must not give these slots screen volumes (written in the Master log of COMMON_RULES, 15 Nov 22:25).

Pack scripts may READ any 1997 global (`if (&story > 5)`) but write only engine stats a reward or a fight changes (gold,
life, lifemax, strength, defense, magic, exp, vision, result and the missile/enemy registers). They may not call
`script_attach` (a pack script ends with its screen), `save_game`, `load_game`, `restart_game` or `kill_game`, and may not set
`&player_map` (Dink moves between pack screens by walking, in and out by joins).

### 2.4 Layout: beyond the loaded world, scale-agnostic

A pack has one or more **sheets** (a rectangle grid of its screens, like an analyse sheet). When a game world begins play,
`DinkExpanded::LayoutPackScreens` reads the 1997 screen volumes that are actually in that world and

- sizes a pack screen as the **median size of the loaded 1997 screens of the sheet's kind** (wilderness, settlement,
  dungeon, interior; the plan's defaults only if none is loaded),
- pushes each sheet from the centre of everything already placed along its `direction` until its box is `gap_m` (1,500 m,
  the analyse `min_gap_m`: past the fog horizon) clear of the bounding box of the whole loaded world and of the sheets placed
  before it.

Nothing in the plugin knows the 1997 map's extent or the region multipliers. Whatever `feat/world-scale` makes of
`regions.toml` (its ratios: wilderness 3.6, dungeon 2.7, settlement 4.6, interior 2.0), the packs follow: their screens take
the new size and stand beyond the new bounds. `Dink.Expanded.Layout` checks this at two scales. The join triggers sit on
the 1997 screens' own corners, so they move with the 1997 screen they belong to. (`world-scale_15nov.md` did not exist yet
when this was written; nothing here needs its numbers.)

A pack screen is an `ADinkScreenVolume` (its number, region, kind, music, base script), a greybox ground slab at z 0,
solid blocks (3 m, profile `DinkHardSolid`) for its hardness rectangles, edge walls where the sheet has no neighbour, and
one `ADinkPlaceholderActor` per placement with its origin and script (the director runs it like any 1997 placement; the art
families may dress it by its 1997 picture). Screens of one sheet share edges, so walking between them is seamless.

### 2.5 Designed joins

`regions.toml` `[[join]]` (the cobbler's booth doorway, 9 Nov) is an owner decision that edits 1997 map data. A pack join
never does. It is two overlay triggers, reusing the 1997 warp component (`UDinkWarpComponent`, kind `pack_join`, walk-in):

```toml
[[join]]
id = "murkwood_thin_place"
from = { screen = 301, rect = [252, 318, 292, 372] }   # 1997 screen, trigger rectangle (map pixels)
to = { screen = 332, point = [520, 200] }              # pack screen, arrival
back = { screen = 332, rect = [566, 158, 600, 242] }   # pack-side trigger
return = { screen = 301, point = [312, 345] }          # 1997 arrival (also where a pack save lands with packs off)
requires = { fact = "x3_seal", at_least = 1 }          # optional: a pack fact opens it
```

The build checks the 1997 side against the shipped 1997 data: the trigger rectangle and the return point are open ground
(hardness 0) in every vision of that screen; no scripted 1997 sprite or warp stands within 40 px (the overlay must not stand
on 1997 business); and, when `tools/analyse/out` exists, the screen is reached by design (`regions.csv` `reach_level`).
A locked fight on the trigger's 1997 screen (`screenlock(1)`) closes the join as it closes every other exit of that screen
(SCR_301's pillbugs lock it in 1997: kill them first). With the switch off the trigger does not exist; with it on, it is an invisible box no 1997 actor, brain or missile sees
(warp-trigger profile), so a 1997 route that does not walk into it plays as before.

### 2.6 Scripts in the director

The pack scripts are compiled together with the 1997 ones (so they share the 1997 globals), then **merged into the shipped
1997 story**: the packs' knots are added to the root's named containers and their VARs appended to `global decl`; every
1997 container, the root flow and `listDefs` stay byte-identical (the build refuses otherwise; `TestBuild` re-checks). The
names table is the 1997 one with the packs' rows appended. Pack globals are facts like any other (`x3_burt`), saved with the
facts; they start at 0 because a fact that does not exist reads 0.

The director needs nothing new: `StartProcedure("x3-burt", "talk", ...)`, `say_stop`, `choice_start`, `create_sprite`,
`sp_script`, `editor_type` on a pack origin all run the 1997 code paths.

### 2.7 Saves

| Save made | Loaded with packs ON | Loaded with packs OFF (or plugin gone) |
|---|---|---|
| in the 1997 world, packs off | as always; pack facts read 0 | as always |
| in the 1997 world, packs on | as always (pack facts restored) | as always; the pack facts in the save are unused facts |
| on a pack screen | the 1997 load lands on the join's return point, then the module moves Dink back to where the save was made (`SubsystemState["expanded"]`); that screen's scripts start fresh, as a 1997 `load_game` starts a screen | lands on the join's return point in the 1997 world; the pack's script instances are left out by the 1997 loader; quest progress (pack facts) waits in the save for when packs are on again |

The save's own `CurrentScreen` and `PlayerTransform` are rewritten to the 1997 return point by the module when it is on
(`UDinkExpandedGameSubsystem::MakeSaveSafe`), so the base fields of a save are always a 1997 place. Tests:
`Dink.Expanded.Save`, `Dink.Expanded.Murkwood.SaveLoadsWithPacksOff`.

### 2.8 Parity

- **Off:** no hook, no subsystem, no actor; `Dink.Expanded.Switch` checks the 1997 paths are returned untouched.
- **On, pack not entered:** the merged story holds every 1997 container unchanged and the 1997 facts are pushed the same;
  the pack rows of the tables are on screens no 1997 code visits; the pack actors are 1.5 km away and the triggers are overlays.
  Nothing of a pack runs before Dink walks through a join: no pack script, so no `random()` draw from the shared stream,
  no sprite handle, no fact write.
- **Proof:** the probe (`Dink.Gameplay.Probe`, twenty chapters) and every `Dink.*` test, run once with
  `DINK_EXPANDED=0` and once with `DINK_EXPANDED=1`; `tools/expanded/probe_parity.py` compares the twenty trace md5s of
  the two logs (and checks each log shows the switch state it claims). Results: in the PR.
- **Inside a pack** the shared random stream and the sprite handles are used as 1997 scripts use them (a pack is new
  gameplay; its own determinism comes from the same seeded stream).

### 2.9 Text and voice

New lines are DinkC `say`/`say_stop` lines with the 1997 colour codes, ids like `x3-burt.talk.004`, all listed in
`Content/Data/lines.csv` with the status "draft, owner to approve". Voice comes later through the same pipeline as the 1997
lines (the ids are stable). Dink's tone: he is rude, greedy, cowardly and pleased with himself; NPCs are blunt and a little
mad; jokes land on the second line; death and body parts are played straight and then made worse.

### 2.10 Not done yet (known limits)

- Packaged builds: `Content/Data` is not yet staged into packages (`DirectoriesToAlwaysStageAsUFS` covers `Dink/Data`
  only). Packs work in the editor and PIE; a packaged build runs with packs unavailable (the module logs it and stays off).
- Joins are walk-in only (no talk-to-open). Locked joins (`requires`) simply do not fire; a "locked" line needs a pack
  script on the 1997 side, which rule 3 keeps out for now.
- Pack screens are one size per sheet; an interior inside a pack is a second sheet of kind `interior`.
- Greybox only: art is `EX-` rows in `doc/remaster/FABLE_ART_QUEUE.md` (Fable 5.2).

## 3. How it grows from 1997 material

Section 11 of the plan lists what each wave grows from. The 1997 hooks, with where they are:

| Hook | Where (bin/dink/story) |
|---|---|
| "Danger! Murkwood Forest - Has been magically sealed shut by decree of King Daniel." | `s2-signe.c:3`, the sign S366_P05 beside the gate S366_P15 (`s2-fgate.c`: touching it costs 5 life and throws Dink back) |
| "There's some talk of an old evil awakening to the west." | `s1-wand.c:113` (the travelling man's news) |
| The cult of little girls worshipping the Dead Dragon Carcass in the Murkwood clearing | `s2-cult.c` (SCR_238) |
| PortTown: "the Pirates in PortTown are looking for some more help", war with "the Northern Trading Company" | `s1-lg.c:145-147` |
| PortTown "rowdy ... because of the frequenting of pirates" | `s1-wand.c:121-124` |
| "I hope I can make it to PortTown and get away for a while." (escaped from the Goblin Sanctuary) | `s1-wand2.c:97` |
| A hunter from PortTown; Libby's bossy boyfriend "from PortTown" | `s1-h3-of.c:82`, `s1-lg.c:120` |
| Blistering Pete: "This be Blistering Pete's weapons shop", "a small run in with the Royal navy", "my treasure awaits me right where I buried it" | `s4-st3p.c:190-216` |
| "Blistering Pete waz here" | `s8-sign.c` (Koka Isle) |
| Goblin George, "my nam is george. whe kin bey gud frins?"; "Goblin Sanctuary - Humans keep out to avoid incidents." | `s3-gob.c:66`, `s3-sign7.c` |
| Dink's father, "a wonderful farmer and husband", "Of course not" good with the sword | `s1-h1-m.c:109-114` |
| "House for Sale: Contact Charlie for information." | `s2-sale.c:8` (Terris) |
| The duck arena: "don't make me put you in the arena!" | `s8-duck4.c:19` (Koka) |
| The roadside robbery | `s1-rob.c` |
| The boat that leaves without Dink ("Come back here!") | `s7-boat.c`, `s7-hell.c` |
| Unused creatures: green and blue slimes, spike | `en-slimg.c`, `en-slimb.c`, `s7-slimb.c`; the unused sprite sequences in `doc/remaster/reference/sequences.txt` |
| The East Wilds: 55 screens behind the cobbler's booth, 22 reached by design, 33 only by sequence breaks or not at all | `tools/analyse` `regions.csv` (`east_wilds`), `regions.toml` `cobbler_booth_doorway` |

## 4. Content slate

Screen counts are rough greybox counts of NEW screens (pack slots); 1997 screens a wave changes the behaviour of are
"overlay" (joins and pack-only placements on pack screens, never 1997 placements).

### Beta systems (no new area; mostly code in DinkExpanded)

| Item | What | Grows from |
|---|---|---|
| Clothing and armour slots | head, body, feet; first sets from the Windemere furrier; stat bonuses on the 1997 formula | the furrier and pawn stubs |
| Pawn shop | rotating random stock (from the pack's own random draws, inside the shop only), sells monster parts | slayer claw, monster drops |
| Monster parts | pillbug shells, bonca teeth, slayer claws, goblin ears (gross, valuable) | 1997 drops (`emake.c`) |
| Reputation | towns react to "hero" or "menace" (killed pets, ducks, villagers); the King's News poster reports it | the "madman who kills pets" rumours |
| More hit/talk lines | per prop and per NPC type, in Dink's voice | fountain and furniture gags |
| Luck | fed by fountain coins; drives crits and loot rolls | fountain gag |

Note: these change 1997 screens' behaviour, so they are the hardest to keep inside rule 3; each needs its own parity
argument (most become pack-only lines on top of the 1997 ones, never instead of them).

### Pack 1: monsters and arms (about 4 screens)

| | |
|---|---|
| Areas | boss arenas for regions without a boss (a mud pit off the Terris dam country, a bramble ring in the Windemere marshes, a flooded cave below KernSin): 3-4 pack screens behind joins |
| Enemies | spike (rolling, can only be hit from behind), green slime (splits on a kill; the green splatter of `en-slimg`), biome variants (marsh pillbug, snow bonca, cave goblin), bosses: the Dam Hog, the Marsh Mother, the Cave Bonca King |
| Items | spear (reach, slow), crossbow (no charge, slow reload), shield (blocks frontal hits, slows the swing) |
| Quests | "Hog wild" (Terris farmers pay for the hog's tusks), "Mother of all slimes" |
| 1997 material | unused slime scripts and sprites, the 1997 bow and sword formulas |

### Pack 2: PortTown and the pirates (about 26 screens)

| | |
|---|---|
| Areas | PortTown (12: harbour, market, the Northern Trading Company office, the pirates' tavern, Aby's house, the gallows), the harbour waters and a pirate ship (6), Pete's island (5), the ferry crossing (3) |
| Joins | a road off the south-coast beaches; the ferry from the Windemere jetty |
| Quests | "Help wanted" (the pirates' war with the Northern Trading Company: pick a side, both lie), "Pete's buried treasure" (Pete's map, his old crew who want it too, the treasure is his ex-wife's skeleton and a lot of gold), Libby's bossy boyfriend (Dink can ruin it), the ferryman who will not take Dink back until paid twice |
| Enemies | pirates (sword, pistol), trading-company guards, a sea serpent, gulls |
| Items | cutlass, flintlock (loud, one shot), Pete's map |
| 1997 material | every PortTown line above, Pete's shop dialogue and the Koka graffiti, the boat |

### Pack 3: Murkwood and the goblin war (about 30 screens)

| | |
|---|---|
| Areas | **Murkwood Deep** (the sealed forest west of the 1997 clearing, 14; the first slice, 6 of them, is section 6), the old evil's barrow (5), goblin war camps (6), the Smallwood farm's cellar and the hermit's tower (5) |
| Joins | the clearing's west treeline (SCR_301); a goblin trail off the KernSin wilds; the Smallwood farm's well |
| Quests | "Old Burt's leg" (slice), "What the seal keeps in" (King Daniel's decree was not to keep people out; the "old evil awakening to the west"), "The goblin war" (the goblins march on the Sanctuary's neighbours; Dink can fight, or take the **peaceful route through the Sanctuary via George**: talk George into telling the goblins something stupid they will believe, as the 1997 traveller says they will), "The Smallwood family secret" (Dink's father was "a wonderful farmer", and it turns out a very good one at burying things) |
| Enemies | Murk boar, bark leeches, the cult's grown-up members, goblin war bands, the barrow thing |
| Items | Burt's stuffed-leg trophy (a joke item), the seal key, father's spade |

### Pack 4: home and play (about 12 screens)

| | |
|---|---|
| Areas | the player house in Terris (house for sale: 3 interior screens), the bigger duck arena on Koka (4), gambling den in Windemere (2), road encounter screens (3, reused by the random roadside events) |
| Quests | buy the house from Charlie (he has never sold anything and does not know how), duck tournament (bet on ducks, fight ducks, eat ducks), random road encounters (the 1997 robbery as a family business, a merchant who sells Dink his own stolen boots) |
| Items | furniture and trophies for the house (the stuffed leg, a duck head), a betting slip |

### The East Wilds (1997 screens, reached since the booth doorway)

33 of its 55 screens are unreached by design. Those are 1997 screens, so a pack cannot put placements on them (rule 1). Two
ways, for the owner to choose: (a) leave them as 1997 terrain and run pack screens off the East Wilds' reached part by joins
(a cave below the cobbler's meadows: 6 screens), or (b) an owner decision like the booth doorway that opens a designed path
into them (a `regions.toml` join: that is a 1997 data change and does not belong to DinkExpanded). Recommended: (a) first.

**Owner 16 Nov 2026: leave the East Wilds as 1997 terrain for now, revisit** (no pack screens and no new paths there yet;
the question stays open, bug list row A212).

## 5. Why Murkwood first

It has the strongest hook (a sign that says "sealed shut by decree of King Daniel", a gate that hurts, a cult in the
clearing behind it, a rumour of an old evil to the west), the 1997 map leaves the cells west of the clearing empty, the
clearing is reached by design, and it seeds the biggest pack (the goblin war, the peaceful Sanctuary route, the family
secret). The East Wilds would need an owner decision first (section 4).

## 6. First slice: Murkwood Deep (greybox, pack 3)

Six screens on the sheet `deep` (west of the loaded world):

```
  (0,0) 267 The Boar's Wallow  ── (1,0) 268 Rotting Hollow ── (2,0) 300 Seal Stones
          │                                                        │
  (0,1) 330 Bonepicker Trail  ── (1,1) 331 Burt's Camp    ── (2,1) 332 The Thin Place ══ join ══ 1997 SCR_301
```

- **Join:** `murkwood_thin_place`, a gap in the west treeline of the 1997 Murkwood clearing (SCR_301, map 252-292 x
  318-372, open ground, 1997 screen reached by design) to the east edge of The Thin Place; back the same way.
- **Placements:** Old Burt (S331_P01, `x3-burt`), the Murk boar (S267_P01, `x3-boar`), four 1997 pillbugs (`en-pill1`,
  S330_P01-02, S268_P01-02), a seal stone (S300_P01, `x3-stone`). Burt's leg appears when the boar dies (`x3-leg`, made by
  `create_sprite` as 1997 drops are; the wallow's base script `x3-wallow` puts it back if Dink left without it).
- **Quest "Old Burt's leg":** Burt has been sealed in since the decree ("went out for kindling"); a boar ate his leg with his
  good boot on. Kill the boar in the wallow, pick up the leg, bring it back; he has it stuffed for over the fireplace and pays
  150 gold. Facts: `&x3_burt` 0 unmet, 1 asked, 2 done; `&x3_boar` 1 dead; `&x3_leg` 1 carried, 2 given; `&x3_thin` 1 seen.
- **Tests:** `Dink.Expanded.Murkwood.Quest` runs the quest end to end through the real merged story and director (talk, the
  boar's death and drop, the pickup, the menu choice, the reward) and checks every 1997 story fact is untouched;
  `Dink.Expanded.Murkwood.Data` the tables on and off; `Dink.Expanded.Murkwood.SaveLoadsWithPacksOff` a mid-conversation
  pack save loading into the 1997 story.

### Draft lines (draft, owner to approve)

All 30 lines of the slice, from `Plugins/DinkExpanded/Content/Data/lines.csv` (speaker 1 = Dink, colour as in DinkC):

| id | speaker | line | status |
|---|---|---|---|
| x3-thin.main.001 | Dink | Whoa. The air in here is all thick. Like Mom's porridge. | draft, owner to approve |
| x3-thin.main.002 | Dink | So THIS is what King Daniel sealed shut. | draft, owner to approve |
| x3-thin.main.003 | Dink | Nobody seals a forest unless there's something good in it. | draft, owner to approve |
| x3-burt.talk.001 | Old Burt | Well I'll be. A visitor! Nobody visits. | draft, owner to approve |
| x3-burt.talk.002 | Old Burt | Not since King Daniel sealed the forest. With me in it. | draft, owner to approve |
| x3-burt.talk.003 | Dink | You've been stuck in here the whole time? | draft, owner to approve |
| x3-burt.talk.004 | Old Burt | Went out for kindling. Came back, there's a magic wall. Nobody told me. | draft, owner to approve |
| x3-burt.talk.005 | Dink | Uh, where's your other leg? | draft, owner to approve |
| x3-burt.talk.006 | Old Burt | Boar ate it. Big ugly thing, up in the wallow north of the trail. | draft, owner to approve |
| x3-burt.talk.007 | Old Burt | Had my good boot on, too. Bring 'em back and I'll make it worth your while. | draft, owner to approve |
| x3-burt.talk.008 | Dink | You want me to fetch your leg. Out of a boar. | draft, owner to approve |
| x3-burt.talk.009 | Old Burt | Leg AND boot. The boot's the important bit. | draft, owner to approve |
| x3-burt.talk.010 | Old Burt | Isn't she lovely? Gonna hang her right over the fire. | draft, owner to approve |
| x3-burt.talk.011 | Dink | It's a leg, Burt. | draft, owner to approve |
| x3-burt.talk.c1.1 | (option) | Give Burt his leg | draft, owner to approve |
| x3-burt.talk.c1.2 | (option) | Ask about the seal | draft, owner to approve |
| x3-burt.talk.c1.3 | (option) | Leave | draft, owner to approve |
| x3-burt.talk.012 | Dink | Here. One leg, slightly chewed. Boot included. | draft, owner to approve |
| x3-burt.talk.013 | Old Burt | My boot! Still laced, too. Look at that. | draft, owner to approve |
| x3-burt.talk.014 | Dink | Are you going to... put it back on? | draft, owner to approve |
| x3-burt.talk.015 | Old Burt | Don't be daft, boy. I'm having it stuffed. Over the fireplace. | draft, owner to approve |
| x3-burt.talk.016 | Old Burt | Here. Took this off a tax collector the boar didn't finish. | draft, owner to approve |
| x3-burt.talk.017 | Dink | 150 gold! Your leg was worth every bite. | draft, owner to approve |
| x3-burt.talk.018 | Dink | Why'd the King seal this place, anyway? | draft, owner to approve |
| x3-burt.talk.019 | Old Burt | Folk say it's to keep people out. | draft, owner to approve |
| x3-burt.talk.020 | Old Burt | Folk are idiots. You don't build a wall that strong to keep a thing OUT. | draft, owner to approve |
| x3-burt.talk.021 | Dink | I'm going to pretend you didn't say that. | draft, owner to approve |
| x3-boar.die.001 | Dink | Something fell out of it. With a boot on. | draft, owner to approve |
| x3-leg.touch.001 | Dink | Burt's leg. Still warm. I'm not thinking about why. | draft, owner to approve |
| x3-stone.talk.001 | sign | By decree of King Daniel this forest is SEALED. Do not enter. Do not feed it. | draft, owner to approve |

The greybox draws Burt as a cylinder, the boar as a red sphere, the leg as a yellow block until the `EX-` art exists. The
boar dies with the 1997 bonca death sequence (550) as its placeholder; the art row asks for a death at the 1997 gore level.

## 7. What the owner must approve

Owner decisions of 16 Nov 2026: the framework (this document's architecture, the module and the switch, OFF by default)
is merged; the Murkwood Deep pack (section 6) is HELD until the owner has read its draft lines and names; the East Wilds
stay 1997 terrain for now (section 4). Items 1, 2 and 6 below are therefore decided; 3-5 remain open.


1. The architecture rules of section 1, in particular rule 3 (packs do nothing in the 1997 world until a join is walked
   through) and the save behaviour of 2.7.
2. Unused 1997 map slots as pack screen numbers (2.3), and the claim on them against the world-scale stream.
3. The first area: Murkwood Deep behind the clearing's west treeline (not through the sealed gate itself, which stays the
   1997 gate and still hurts).
4. Every line in the table of section 6 (draft), the quest, and the names Old Burt, the Murk boar, The Thin Place.
5. The slate (section 4), its order (Pack 3 first, then 2, 1, 4) and the East Wilds choice (a) or (b).
6. The switch default (OFF) and the enabling in `DinkRemaster.uproject` of the (inert) module.

## 8. Commands

```
cd tools/expanded
python3 -m expanded build [--analyse ../analyse/out] [--check]   # packs -> Plugins/DinkExpanded/Content/Data
python3 -m unittest discover -s tests                              # 20 tests, about 15 s
# In a built copy, two Unreal turns, then the comparison:
DINK_TEST_RUN=expanded_off DINK_EXPANDED=0 Scripts/test.sh Dink
DINK_TEST_RUN=expanded_on  DINK_EXPANDED=1 Scripts/test.sh Dink
python3 -I ../tools/expanded/probe_parity.py Saved/Logs/test_expanded_off.log Saved/Logs/test_expanded_on.log
# In game: -DinkExpanded=1, then walk into the gap in the west treeline of SCR_301 (dink.Goto 301 272 345).
```
