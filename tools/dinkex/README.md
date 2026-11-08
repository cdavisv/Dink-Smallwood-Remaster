# dinkex: stage 1 of the remaster data pipeline

Reads the original Dink Smallwood data in `bin/dink/` and writes a neutral
intermediate representation (JSON + PNG) that later stages consume. It never
modifies `bin/`, `source/` or `doc/`. Python 3.14, stdlib + numpy + Pillow only.

Byte layouts: `doc/remaster/bible/04-engine-and-file-formats.md` section 1.
Engine behaviour is cited as `D:<line>` against `source/dink/dink.cpp`.

## Commands

Run from `tools/dinkex/`:

```
python3 -m dinkex extract --data ../../bin/dink --out out     # everything (~7 s)
python3 -m dinkex extract --only screens,hardness              # subset: screens sequences sprites tiles hardness world
python3 -m dinkex facts                                        # headline counts, writes nothing
python3 -m dinkex unff ../../bin/dink/graphics /tmp/bmps       # dump every BMP from .ff + loose files
python3 -m unittest discover -s tests                          # tests (~7 s; real-data tests extract to a temp dir)
```

`out/` is git-ignored (`.gitignore` in this directory). `--only screens` still
needs sequence data internally (hardbox sizes) but does not write it.

## Output layout

```
out/
  summary.json            counts and anomalies (see below)
  world.json              32x24 grid of screen numbers (0 = none), indoor and music grids
  world_tiles.png         whole tile layer, 3840x1920 (box-filtered 5x downsample)
  sequences.json          every sequence from dink.ini
  screens/SCR_nnn.json    one per used screen (644)
  hardness/SCR_nnn.png    600x400 collision map, vision 0
  hardness/SCR_nnn_owner.png          which placement stamped each pixel
  hardness/SCR_nnn_vV.png (+_owner)   one extra pair per nonzero vision value V on that screen
  sprites/<seq>/<NN>.png  RGBA, colour key transparent (seq plain number, NN two digits)
  tiles/tsNN.png          RGB, no colour key
```

Origin IDs: screen `SCR_nnn` (nnn = 1..768 screen number, NOT the map.dat
record), tile `Snnn_Tnn` (nn = 00..95), placement `Snnn_Pnn` (nn = index in the
screen record, 1..99, as the editor and `spmap[]` number them).
Sprite frames are identified by `(seq, frame)` and carry their archive, entry
name, byte offset and size.

## Hardness PNG encoding

8-bit palette PNG; the pixel *value* is the code (open with a library that does
not apply the palette, or read the index):

| value | meaning |
|---|---|
| 0 | walkable |
| 1 | solid, tile hardness 1 |
| 2 | low, tile hardness 2 (water, fences; projectiles and flyers cross; does not start a push) |
| 3 | other non-zero tile hardness (one block in `hard.dat` holds a single 3; blocks) |
| 100 | hardbox stamped by a placed sprite (engine value 100+index; blocks) |
| 200 | hardbox stamped by a placement with `prop != 0` (warp trigger) |

Built as the engine does on screen load: `fill_whole_hard` (tile hardness via
`hard.dat`, `althard` overrides) then `place_sprites_game` visits placements in
rank order (ascending `que`, or `y` when `que` is 0; ties to lower index; only
indices 1..99), skips those whose `vision` is non-zero and differs from the
current vision, and stamps the frame's hardbox (relative to the origin, x minus
20) for those with `hard == 0`. Later stamps overwrite earlier ones. The `_owner`
image holds the stamping placement index (0 = tile layer only).

`SCR_nnn.png` is vision 0, which is what the engine starts with; the base
script's `main` runs before placement and may set `&vision`, so screens with
vision-gated placements also get `_vV` variants for each value V present. Not
modelled: anything a script changes at run time (`fill_hard_sprite`, moving
live sprites, `sp_hard`, killed sprites, `spmap` save state).

## `screens/SCR_nnn.json`

Top level: `schema` ("dinkex.screen/1"), `id`, `screen` (1..768), `col`, `row`
(0-based on the 32x24 grid), `map_record` (1-based record in map.dat), `name`
(record name, usually empty), `indoor` (bool) and `indoor_raw`, `music`,
`base_script` (lower-cased; the engine lower-cases script names), `random_script`,
`load_script`, `neighbours` (`left/right/up/down` screen number or null; a
neighbour exists only if it has a map record), `counts`, `hardness`, `tiles`,
`placements`. Optional: `v` (the 40 ints, only if any non-zero), `s`,
`buffer_nonzero`.

- `music`: `{raw, action: none|stop|play, name, file}`. `raw` is the `music[]` value; N or
  (N-1000) plays `N.mid`; `file` is what PlayMidi would pick: `sound/N.ogg` if
  present, else `sound/N.mid`, else null. The engine code also falls through to
  play "-1.mid" for -1; this reports plain `stop`.
- `counts`: `placements, warps, with_hardness, vision_gated, with_script`.
- `hardness`: `image`, `owner_image`, `vision_variants` ({V: path}), `skipped_tiles`
  (tile IDs the engine refuses to write), `stamps` (rank-order list of
  `{placement, rect:[x0,y0,x1,y1) in 600x400 map coords or null, reason}` for
  vision 0), `pixel_counts` ({code: pixels}).

`tiles[]` (96, row-major 12x8): `id, index, col, row, x, y` (top-left pixel in
the 600x400 map), `num` (raw), `tileset` (= num//128+1), `cell` (= num%128),
`src {x,y,w,h}` (= (cell%12*50, cell//12*50, 50, 50) in `tiles/tsNN.bmp`),
`tileset_exists`, `src_in_bounds`, `althard`, `hardness_tile` (resolved id:
`althard` if > 0 else `index[num]`), `hardness_source`
(`althard|index|index_beyond_file|index_out_of_table`), `hardness_valid`
(0 <= id < 800), `property, more2, more3, more4`, and `buff` only if any of the
15 ints is non-zero.

`placements[]` (active only): `id, index, rank` (stamp/place order), then every
field of the 220-byte record: `x, y` (screen coords, x includes the 20 px side
bar; `map_x = x-20`, `map_y`), `seq, frame, type, size, active, rotation, special,
brain, script, hit, die, talk` (lower-cased), `speed, base_walk, base_idle,
base_attack, base_hit, timer, que, hard` (raw, INVERTED), `alt {left,top,right,bottom}`
(order inferred from the Proton `rtRect32`), `prop, warp_map, warp_x, warp_y, parm_seq,
base_die, gold, hitpoints, strength, defense, exp, sound, vision, nohit,
touch_damage, buff[5]`. Derived:

| field | meaning |
|---|---|
| `kind` | `type` 0 `background` (baked into the screen image), 1 `live`, 2 `hardness_only` |
| `drawn` | type 0 or 1 |
| `size_percent` | `size`, with 0 meaning 100 |
| `has_hardness` | `hard == 0` (the flag is inverted; any other value, e.g. 1 or 200, means none) |
| `is_warp` | `prop != 0` (shipped data only has 0 and 1; 93 are 1) |
| `warp_target_valid` | warps only: `warp_map` is a used screen |
| `vision_gated` | `vision != 0`: exists only when `&vision` equals it |
| `has_script` | script name longer than one character (the engine's test) |
| `pic` | picture the engine draws: `{seq, frame, image, width, height, origin, hardbox}` after SET_FRAME_FRAME aliasing, or null (seq 0, frame 0, missing) |
| `pic_resolved` | `pic != null` |
| `hardness_stamp` | `{x0,y0,x1,y1,kind: solid|warp}` clipped to the 600x400 map, only when `has_hardness` and `pic` resolve; independent of vision gating |

## `sequences.json`

Top level: `schema`, `ini_lines`, `sequence_count`, `misc` (`starting_dink`,
`playmidi`, `gfx_alttext_disable`), `redefined` ({seq: earlier definitions}),
`warnings`, `sequences[]`.

Sequence: `seq, path` (as written, `/` separators), `directory`, `prefix`,
`ini_line` (final definition), `ini_lines` (all), `load_now`, `keyword`
(BLACK/LEFTALIGN/NOTANIM/null), `flags {black, leftalign, notanim}`, `is_anim`
(engine `m_bIsAnim`: true for BLACK and for sequences whose 4th token is
anything else, false for LEFTALIGN and NOTANIM), `transparency`
(`white|black|none`; none for seqs 181-185, 190, 451 when LEFTALIGN/NOTANIM),
`default_delay_ms`, `ini_origin`, `ini_hardbox` (raw ini values, anim only),
`file_frame_count`, `frame_count` (includes alias-only slots), `frames[]`.

Frame: `frame` (1-based slot), `delay_ms` + `delay_source`
(`sequence_default|set_frame_delay:lineN|unset`), `special` + `is_hit_frame`
(`special == 1`), `pic {seq,frame}` (the picture drawn in this slot),
`image`, `source {kind: ff|loose, file, entry, bytes, offset?}`, `width`,
`height`, `origin {x,y}` + `origin_source`, `hardbox {left,top,right,bottom}` (relative
to the origin) + `hardbox_source`, `transparency`, `alias` (null, or `{seq,frame,line}`
when SET_FRAME_FRAME re-pointed the slot, or `{loop:true}`), `loop_to_start`
(SET_FRAME_FRAME with source -1), `empty` (slot copied from nothing).
`origin_source`/`hardbox_source` are `ini`, `default_from_frame1`,
`default_own_size`, `default_guess`, `mixed_ini_and_default` or
`set_sprite_info:lineN`.

Rules implemented (D:1798-1923, 2165-2625, 17555-17595): two passes (all
`load_sequence*` first, later definition of a number wins; then the other
commands in file order); anim origin = ini value if > 0 else
`(w - w/2 + w/6, h - h/4 - h/30)` from FRAME 1's size, applied to every frame; non-anim
sequences use each frame's own size; hardbox forced per axis when the ini
`right`/`bottom` is > 0, else `±w/4`, `±h/10` from the frame's own size;
SET_SPRITE_INFO overrides all six values of the picture currently in that slot
(so after an alias it edits the other sequence's picture); frame counts come from
consecutive `<prefix>NN.bmp` in `dir.ff` then loose files. Sizes are BMP pixel sizes
(the loader is in the Proton SDK; assumed to equal the surface size).

Colour key: matched on RGB (white 255,255,255; black 0,0,0), not palette index.
In the shipped art white is palette index 0 and black is index 255, but the 13
`tiles/sNN.bmp` BLACK sprites have their own palettes. Transparent pixels keep
their key colour in RGB.

## `summary.json`

Counts for screens (used, indoor, outdoor), placements (total, by kind, `prop`,
`hard` value, brain), warps, distinct placement and base scripts, max placements
per screen, vision-gated placements, music values, BMP census (archives,
`.ff` BMP entries, non-BMP `.ff` entries, loose BMPs, total, referenced,
unreferenced), sequences defined/redefined/warnings, `hard_dat` facts, unresolved
placement pictures, tiles with invalid hardness ids, and PNG counts.

## Known limitations

- Hardness is the load-time map only (see above); no script effects.
- Placement pictures come from `dink.ini` alone. Sequences a script loads at run
  time with `load_sequence` are not modelled (none are needed by the shipped map:
  the only unresolved placements are four seq 0 / frame 0 entries, none with hardness).
- Hardness tiles skipped by the engine (invalid id) would keep the previous
  screen's pixels in the real game; here they stay 0 and are listed. No shipped
  tile hits this (see below).
- Sprite hardbox stamping drops the engine's extra column 600 / row 400.
- `alt` rect field order, and BMP size = surface size, are inferred (Proton source absent).
- Only the base game's `.bmp` art is read; `.png` overrides and DMODs are ignored.
- Frame-image scaling by `size` is not applied to the PNGs (sizes are in the JSON).

## Facts found while verifying against the shipped files

- 3,572 `.ff` + loose entries, but three archives (`inside/stnwalls/snake`,
  `inter/text-box`, `lands/trees/treefire`) contain a self-referential `dir.ff`
  entry that is not a BMP; BMP frames = 3,569.
- `hard.dat`: 106 of the 5,248 present index entries are out of range, but no
  tile on any shipped screen uses one, and no tile number reaches the 2,752
  missing index entries (max tile num is 5211). Both traps are covered by
  synthetic tests only.
- Hardness blocks keep stray 1s in the unused `y == 50` column; ignored.
- Sequences 102, 104, 106, 108 are defined twice (sword-hit art at lines 65-68,
  then normal-hit art at lines 70-73, 5 frames instead of 6). The later one wins.
- `set_frame_frame 83 13 82 3` copies a frame that does not exist (seq 82 has
  2 frames), so slot 13 of sequence 83 is empty.
- `STARTING_DINK_MAP` in dink.ini is not handled by the HD engine's ini parser.
- 164 placements on 37 screens are vision-gated; 44 extra hardness variants are written.
- Placement `hard` takes the values 0 (2,722), 1 (3,122) and 200 (2).
