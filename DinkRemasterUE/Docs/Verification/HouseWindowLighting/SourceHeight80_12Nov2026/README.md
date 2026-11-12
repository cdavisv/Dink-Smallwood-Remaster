# Window light source height 130 cm -> 80 cm: room before and after (12 Nov 2026)

Owner decision (12 Nov 2026, "Yes, shorten them"): the six window rect lights of Dink's house go from 80 x 130 cm
to 80 x 80 cm. Reason: with the 130 cm source, thin bright lines showed on the head of any character standing backlit
near a window (cause and bisect: `Docs/Verification/HeroDefectFixes_9Nov2026/Round3_12Nov2026/`).

**What changed.** `SourceAssets/Art/Stonebrook/LightingV1/lighting.json` `daylight.source_height_cm` 130 -> 80, then
`python3 Scripts/house_lighting.py --apply`, which rewrote only the six `source_height_cm` values of the
`Daylight_*Wall_*` rows in `Content/Dink/Data/Art/stonebrook.json` (12 changed lines, nothing else). Width (80 cm),
170 lm, 5000 K, radius 1000 cm, position 30 cm outside the wall, the two practical points, sun, sky and exposure are
unchanged. `Scripts/tests/test_house_lighting.py` pins the new size.

**How the frames were taken.** Work copy of master 2fd03cba (`Saved/HeroFix2Work`), the real game (`-game`, 1280x720)
on the private display (`Scripts/private_qa_session.py`, Xvfb :189, RX 6800), driven with
`Scripts/playtest_desktop.py --private-display :189`. The game was started once with the 130 cm data and once with the
80 cm data; in each run `getall RectLightComponent SourceHeight` read back six lights at 130 / 80, and the same script
placed Dink with `dink.Goto`, set `dink.View` and `fov`, waited two seconds and captured. Positions read back equal in
both runs (the two walked poses differ by under 1 map unit). Nothing was retouched; sheets are whole frames scaled to
960x540 with a label strip, and the head sheet is a plain crop of `HighResShot 3840x2160`. Mother walks about on her
own, so she is in different places (or out of frame) between the two runs.

| File | What it shows |
|---|---|
| `room_wide_130_vs_80.png` | Four views from the room's start point (map 314,161; yaw 0/90/180/270, pitch -15, fov 90). |
| `room_walls_130_vs_80.png` | Three closer views: two window walls (map 200,230 yaw 180 and 430,230 yaw 0; fov 75) and the fireplace side (map 310,150 yaw 270). |
| `poses_130_vs_80.png` | The 11 Nov lit pose by the window (map ~149,162) and the backlit pose (map ~185,160; fov 36). |
| `backlit_head_130_vs_80.png` | 4K crop of the backlit head. Before: bright lines on the scalp, forehead, cheek, nose and collar. After: gone. |

**What I see.**
- Backlit head: the lines on the scalp, forehead, cheek and collar are gone at 80 cm. One short faint mark remains
  beside the nostril (it is far smaller than before; visible only in the 4K crop).
- Room: the pools of window light on the floor are where they were. The pools on the walls opposite the windows are a
  little shorter top to bottom with slightly firmer edges. Nothing went dark and nothing new lit up.
- Overall brightness: mean luma of each whole frame (0-255) at 130 / 80 cm: 46.4/46.8, 39.7/40.5, 43.0/43.4, 44.5/44.4
  (wide views); 59.7/59.5, 53.9/53.8, 40.9/40.3 (closer views); 46.9/47.6, 39.5/39.5 (poses). All within 1 level.

**Not checked.** Frame rate, the packaged build, and the house seen from outside through the windows.
