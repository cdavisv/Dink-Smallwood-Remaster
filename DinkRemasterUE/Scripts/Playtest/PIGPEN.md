# Screen407 before/after playtest

Use only the private Xvfb backend. Preserve the user's desktop game and focus. These fixtures require a fresh nonsaved game with the original feed sack present and `pig_story=0`; they never write a save or set the quest fact.

```bash
python3 Scripts/private_qa_session.py start
# Finish the opening dialogue with private Space inputs until dink.Player reports move_ignored=0.
python3 Scripts/playtest_desktop.py --private-display :189 key space
python3 Scripts/playtest_desktop.py --private-display :189 console 'dink.Player'
python3 Scripts/playtest_desktop.py --private-display :189 route Scripts/Playtest/pig_feed_pickup_house.json --out Saved/Playtest/evidence/pigpen-before/feed-pickup-walk.json
python3 Scripts/playtest_desktop.py --private-display :189 console 'dink.Arm item-pig'
python3 Scripts/playtest_desktop.py --private-display :189 route Scripts/Playtest/house_exit_art.json --out Saved/Playtest/evidence/pigpen-before/house-exit-keyboard.json
python3 Scripts/playtest_desktop.py --private-display :189 route Scripts/Playtest/yard_to_pigpen_west_gate.json --out Saved/Playtest/evidence/pigpen-before/yard-to-pigpen-west-gate.json
python3 Scripts/Playtest/pigpen_feed_scene.py --out Saved/Playtest/evidence/pigpen-before
python3 Scripts/private_qa_session.py stop-game
```

The pickup route uses actual W movement from the house start to the authored feed sack. The next route exits the house. The courtyard route goes east around the cottage, north into407, west along the outside southern corridor, north toward the original west opening, then east through the gate to300,250. There are no teleport fixtures in this chain. Each route checks the actual screen, floor height, frozen-input state and capsule movement after held keys.

The scene fixture requires the feed to be armed, presses real F, and advances the original dialogue with Space until `pig_story=1`. It checks that both `item-pig.use` and `s1-bul` ran, and that normal movement is restored. It never calls those procedures directly, creates the bully itself or mutates quest facts. Before/after script dumps, exact coordinates, screenshots and the original log accompany the result.

The first before-art run passed every route and the full Milder feeding scene. Evidence is under `Saved/Playtest/evidence/pigpen-before`. `pigpen-clean-before.png` records the old oversized fence cards. `dynamic-sprite-properties.log` identifies Milder as `DinkScriptSpriteActor_1`: original pseq341/pframe1, base_walk400, speed2, size100, brain0 and generic Marker. The loaded implementation renders a30×30×60cm cylinder rather than a readable humanoid; this is distinct from the oversized static fence cards.

Reuse the same routes after the coordinated art import, in a fresh private session and a separate `pigpen-after` output directory. The exact source gate/cutscene contract is in `SourceAssets/Art/PigPen/layout_checks.json`. A source-only layout diagram or Blender preview cannot substitute for this rendered keyboard check. Do not rebuild while the user is actively playing the known host session; ask the coordinating agent to resolve it instead of closing that window.
