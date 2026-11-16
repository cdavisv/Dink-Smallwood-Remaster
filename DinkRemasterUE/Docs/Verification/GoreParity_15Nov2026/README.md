# Gore at the 1997 level: evidence (15 Nov 2026)

PR `fix/gore-story-parity`; audit in `doc/remaster/GORE_STORY_PARITY.md`. All frames are from the running editor game
(offscreen capture, `Scripts/PhotorealQA/run_capture.sh`) in a private project copy = master + this branch, world generated
on 15 Nov 2026. "Before" is the same build with the new layers switched off by their console variables
(`dink.HitBlood 0`, `dink.CorpseCards 0`, `dink.DeathFall 0`, `dink.DecalFromCard 0`), which is what master draws.
Fights were made with the review command `dink.GoreHurt <origin> <damage>` (the DinkC `hurt`, so random_blood and the
kill run their real paths) and with `dink.Attack`.

## Sheets and what I see

- `death_before_after.jpg` (SCR_527, `dink.Fact life 0`; `dinfo.c` `die` sets `sp_seq(1, 436)`). Before: 0.6, 1.6
  and 5.1 s after the death Dink stands upright among the pillbugs. After: at 0.6 s he is crumpling, at 1.6 s and 5.1 s
  he lies on the ground, the pillbugs over him. Not the 1997 animation (a ragdoll from the hero's physics asset), but he
  lies dead as 1997's sequence 436 ends. Odd detail: in the 0.6 s frame his head shows red (not investigated).
- `corpse_card_slayer.jpg` (SCR_028, slayer S028_P03 killed). Left: the live slayer (a card). Middle: after the kill
  the 1997 death picture 645 stands on a card where it died: the red body in its pool. Right: the picture itself.
  Before this PR the live card vanished and nothing was left.
- `hit_blood_bonca.jpg` (SCR_029, `dink.GoreHurt S029_P04 6`). Before the hit: bare ground. 0.2 s after: a red splat
  on the ground by the bonca, about 1 m across, beside the 1997 spurt 188/4 whose red part is 0.98 x 0.43 m at the same
  scale. Last: a pillbug fight on SCR_527 (the pillbug corpse's own pool covers the hit blood there). In this capture
  the three killed boncas left NO corpse card in view: the ground trace started 4 m up and hit the dead tree's crown
  (fixed afterwards: the trace starts 1 m up; the fix is built into the PR but was NOT captured again).

## Log lines that show each layer firing (capture after2)

`DINK CORPSE CARD: sprite 5 picture 557 on screen 29`, `sprite 8 picture 551`, `sprite 4 picture 557`, `sprite 4 picture
645 on screen 28`; `DINK DEATH: the hero falls (sprite picture 436)`; `DINK ENV: 3 ground decals on screen 533`.

## Not checked

- The final state of the PR (the review fixes: Dink's fall taken over from PR #145 with re-attach, collision filter,
  drift fallback and the 190 cm pool; the explosion 164 card; the creature check made while alive; the hurt-sound draw)
  was NOT built or run: the Unreal lock was held by other streams. The frames above are from the state before it.
- The probe was not run on any state with the random draws (A25/F5); the re-baseline is planned with PR #141.
- Burn holes: only the after state of SCR_533 was captured (a dark scorch decal near the house steps); no matched before.
- Packaged build, dragons' and people's corpse cards, slimes' splatter cards, the explosion 164 card.
