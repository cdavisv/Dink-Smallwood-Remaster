# Playtest controls, item screen and dialogue box (14 Nov 2026)

Owner playtest feedback: left click should attack, the game needs a real item screen, and speech still used the
old floating text. Code and UI only (DinkNarrative plugin). Story timing, skips, blocking, menu indices and saves are
unchanged. Bug list row A11.

## Captures

All captures come from the rendered game (`-game`, Vulkan) on the private Xvfb display `:189` at 1280 x 720,
driven by `Scripts/playtest_desktop.py --private-display :189` (keys and console) and an XTest click helper. A new
game was started at SCR_001 (Dink's house). Audio used SDL's `dummy` driver, so nothing reached a sound device and
the voice lines still ran in the game (log below).

| Sheet | What it shows |
|---|---|
| `dialogue_box.jpg` | Top left: Dink's line "What kind of a man was father?" (blocking, with the continue hint). Top right: Mother's answer with her name plate. Bottom left: a non-blocking line ("I picked up a nut!", no hint). Bottom right: Dink's opening line "What, now?". |
| `choice_menu.jpg` | Mother's talk menu (five options, number badges, key hints), first row and then the second row highlighted after one Down. |
| `inventory_screen.jpg` | Left: the item screen after `2` quick-armed the nut (Nut armed, cursor on it, stats, key hints). Right: cursor moved left onto the magic panel and Fireball armed with F (Spell: Fireball, magic charge bar). |
| `first_render_white_panels.jpg` | The defect found on the first render of this branch: every panel was drawn opaque white (light text on white). Cause: `FSlateDrawElement::MakeBox` does not read the brush's tint, so the fill colour has to be passed as the element tint. Fixed in this branch; the other sheets are after the fix. |

What I looked at: every text in these sheets is readable; nothing is clipped. The box sits inside the bottom of the
screen, long and short lines wrap inside it, the name plate does not cover the text, and the continue hint and its
chevron no longer touch (a second fix after the first look). The item screen's grid, labels, stats and key hints are
all inside its panel. The panel is translucent, so the scene shows faintly through it.

1080p: the layout is in Slate units for a 1920 x 1080 reference and the project's DPI curve scales it (1080p = 1.0,
720p = 0.67). At 1080p every element is the same layout 1.5 times larger in pixels: the box's body font is 21 (Slate
size), so its line height is about 19 px at 720p and about 28 px at 1080p. I captured at 720p only, because the private display is 1280 x 720. A native 1080p
capture was not taken.

## Voice in step with the box

`UDinkAudioSubsystem` (voice playback, PR #124) and the box both follow `UDinkStorySubsystem::GetActiveTexts()`.
This branch adds two things:
- `OnLineSkipped` stops the skipped line's recording in the same frame. Log from the captured run, Enter pressed on
  Mother's conversation:
  `Playing voice s1-h1-m.talk.004 ... / Voice of text 19 stopped: line skipped / Playing voice s1-h1-m.talk.005 ...`
- A line that times out while its recording is still playing (about 400 of the 2,088 recordings are longer than their
  text) stays in the box without the continue hint until the recording ends or another line takes the box.
  `UDinkAudioSubsystem::IsVoiceTailPlaying` decides this, and the test `Dink.Audio.VoiceLinesFollowTheirTexts` covers
  the rule. The story's text list and timing are not touched.

The inventory screen pauses the world, which also pauses the recording, along with the story clock.

## Tests

- Final, after rebasing on master 283cd155 (PR #125's gamepad bindings and Esc/M button scripts, which this branch's input
  processor now reads): `Scripts/test.sh` (`Dink`) 283/283 passed in 879 s, `Dink.Input.*` included; all twenty probe md5s equal
  to the table again.
- Earlier, private copy master 79597061 + this branch:
- `Scripts/test.sh` (filter `Dink`): 278/278 passed in 953 s, including `Dink.Gameplay.Controls.{LeftClickAttacks,
  PigFeedingByInput, InventoryRules}`, `Dink.Narrative.Presentation.{NamesTables, LineShownHook}` and
  `Dink.Audio.VoiceLinesFollowTheirTexts`.
- Probe: all twenty `Dink.Gameplay.Probe` chapter md5s equal to the table in `Plugins/DinkParity/Docs/packaged_probe.md`
  (Ch1 b4ad88c02c ... Ch20 84f33687af).
- `python3 -m unittest discover -s Scripts/tests`: 880 OK. `export_presentation_data.py --check`: up to date.

Built after the full suite: the white-panel fix and the hint gap. Both touch only `DinkNarrativeOverlay.cpp` painting,
which no test reads.

## Follow-up of 15 Nov 2026 (review of PR #128)

Three review findings, fixed on master 0bf319c9 (with #126 and #130):

- **Left click attacked from anywhere in the application.** Slate hands the input pre-processor every click, including clicks on editor panels in PIE and the click that focuses the window, and the processor never consumes a click. Now a click counts as game input only when two things hold (`FDinkNarrativeInputProcessor::AcceptsClick`):
  - it lands on the game viewport, or the viewport holds the mouse capture;
  - the viewport already had focus in the active window at the previous frame. Slate ticks the pre-processor after each frame's input, so that is the state before the click.

  The mouse wheel now acts only over the viewport. Test `Dink.Gameplay.Controls.ClickNeedsFocusedViewport`.
- **Owner-requested deviations, documented and kept.** These come from the owner's playtest request of 14 Nov ("number-key quick-arm"), and the 1997 game has none of them (it arms only with the attack button, dink.cpp:16473):
  - keys 1-9 and 0 quick-arm item slots 1-10;
  - Space and left click arm on the item screen;
  - I opens the item screen beside Enter.

  They are documented in `DinkNarrativeInput.h`, in bug row A11 and in AGENTS.md.
- **Bug list A11 was listed twice.** The two rows are merged into one.

`followup_15nov_dialogue_item_screen.jpg` shows the rendered game on the private display `:189` (1280 x 720, SDL dummy audio) after the follow-up:
- top left: Mother's line in the box, with its voice playing;
- top right: after Enter, Dink's "What, now?". The log shows `Voice of text 19 stopped: line skipped` and then the next recording starts;
- bottom left: the item screen opened with I on SCR_438;
- bottom right: the item screen closed with I.

Enter opened and closed the item screen too (cues 18 and 17 in the log).

Left click, with XTest button events:
- with the game window focused: one `attack with item-fst`;
- after the X input focus moved to the root window (another window has focus): no attack;
- focus back: one attack.

The XTest pointer move to the window centre also turns the camera (mouse look). That is expected.

Not seen on screen: a click on an editor panel in PIE (there is no editor on the private display; the rule is unit-tested), and a WM focusing click (Xvfb has no window manager).

Tests on 0bf319c9 + this branch, private copy, world regenerated: `Scripts/test.sh "Dink.Input+Dink.Gameplay.Controls+Dink.Narrative.Presentation+Dink.Audio+Dink.Gameplay.Probe"` passed 42/42. The twenty probe md5s are equal to the 14 Nov 2026 table in `packaged_probe.md`.

## Not checked

- A native 1080p capture, as explained above.
- The voice tail hold seen on screen. The dummy audio device plays recordings, but I did not capture a frame during a tail.
- Bubbles over other speakers' heads and the `_xy` caption cards. Neither occurred in the captured scenes.
- Gamepad (still unbound, bug A4) and left-click attack in the rendered game. The click path is covered by
  `LeftClickAttacks`.
