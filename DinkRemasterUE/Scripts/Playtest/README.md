# Rendered desktop playtests

`../playtest_desktop.py` controls an already-open `DinkRemaster` game viewport on this development machine's Hyprland desktop. It uses the installed `hyprctl`, `wtype` and `grim`; no desktop configuration is modified. Run outside a filesystem/desktop sandbox, with the normal desktop session environment.

```bash
~/UnrealEngine/UE_5.8.4/Engine/Binaries/Linux/UnrealEditor "$PWD/DinkRemaster.uproject" /Game/Dink/_Generated/Maps/L_Greybox_World -game -windowed -ResX=1280 -ResY=720 -nosplash -abslog=/tmp/dink-remaster-playtest.log
```

In another terminal:

```bash
python3 Scripts/playtest_desktop.py normalize
python3 Scripts/playtest_desktop.py capture Saved/Playtest/evidence/house.png
python3 Scripts/playtest_desktop.py console 'dink.Player'
python3 Scripts/playtest_desktop.py console 'dink.View 90 -18'
python3 Scripts/playtest_desktop.py key space
python3 Scripts/playtest_desktop.py hold w 0.25
```

The opening conversation freezes movement until it finishes; Space skips each line. Complete it before the walking route. The `dink.Player` command prints whether movement is still frozen, map and world coordinates, capsule radius, and camera orientation. `dink.View` sets only camera yaw/pitch. Neither command moves the player. `dink.Origin S001_P26` prints a placement’s live coordinates (useful for locating wandering NPCs before testing E).

```bash
python3 Scripts/playtest_desktop.py route Scripts/Playtest/house_exit_art.json --out Saved/Playtest/evidence/house-exit-keyboard.json
python3 Scripts/playtest_desktop.py route Scripts/Playtest/yard_camera.json --out Saved/Playtest/evidence/yard-walk-keyboard.json
python3 Scripts/playtest_desktop.py console 'dink.View -90 -8'
python3 Scripts/playtest_desktop.py capture Saved/Playtest/evidence/outside.png
python3 Scripts/playtest_desktop.py route Scripts/Playtest/house_return_art.json --out Saved/Playtest/evidence/house-return-keyboard.json
```

Routes move with real held W keys through Enhanced Input and CharacterMovement, using normal acceleration, capsule sweeps, and door overlaps. They adjust camera yaw to aim at the next waypoint and query the real pawn after each short movement. They never teleport. Each JSON result records every observed position, expected destination, and PASS/FAIL. Input stops if the Dink viewport loses focus or if a waypoint is blocked. Do not use the keyboard/mouse during a route. A route requires the game log supplied by `--log` (default `/tmp/dink-remaster-playtest.log`). A fresh game starts at the first route; the return route begins just outside the front door.

`house_exit_art.json` follows the east aisle around the authored 3D furniture. The original `house_exit.json` deliberately crosses the narrow table/bed corner before the door. This catches the original 42 cm capsule problem that the old teleport-into-warp test missed. The return route walks away from the destination first and then enters the exterior door, catching synchronous overlap recursion during teleport. `house_return_art.json` aligns to the authored cottage opening at map339,293; the original `house_return.json` targets the original greybox door at345,282. Use the original fixtures when launching with authored art disabled.

The viewport normalizer uses the current Lua dispatcher API, not the old Hyprland dispatcher syntax: [official Hyprland dispatcher guide](https://wiki.hypr.land/configuring/core/dispatchers/). It floats only the selected game window at 1280×720. Captures crop the current game window's actual compositor rectangle after a short settling delay, so screenshots show the running game and HUD.

Headless C++ tests remain the primary regression checks (`Scripts/test.sh`). Desktop routes complement them by exercising real rendered input. Art comparison and dialogue/combat screenshots should accompany the route logs in the git-ignored `Saved/Playtest/evidence` directory.

## Rendered interaction regression checks

`Scripts/playtest_interactions.py` checks the physical-art interaction adaptation with actual F/E/W input. A fixture teleport sets each exact test location and a short real W movement aligns the pawn's body; the expected furniture or pickup procedures are never called directly. This is separate from the no-teleport walking routes above.

```bash
python3 Scripts/playtest_interactions.py --phase after --out Saved/Playtest/evidence/interactions-after
python3 Scripts/playtest_interactions.py --only props --out Saved/Playtest/evidence/prop-interactions-after
```

Run the complete set in a fresh, nonsaved game after the opening dialogue finishes. The pie and feed sack must still be present. The pickup checks temporarily set life to5 and restore it to10; they collect the test items and deliberately leave the session disposable. No save is written. `--only props` runs seven furniture cases without requiring fresh pickups. Individual furniture case IDs can be comma-separated with `--only`; pickup cases run together with `--only pickups`.

The table cases use map370,231 facing west (out of fist reach),350,231 facing west (near enough), and350,231 facing east (facing away). Bed cases use280,287 (far) and245,287 (near). The old pixel boxes incorrectly accepted the far table and bed; a rendered pre-fix run recorded three expected failures. The actual authored table near edge is about169cm from the far fixture and82cm from the near fixture. The bed's visible edge is about249cm from its far fixture.

The tool compares each target script's cumulative executed-line counter before and after the input, so an old `hit` label in the debug dump cannot make a case appear to pass. F cases also require the armed fists' `use` counter to advance, proving that the attack input reached the game. This remains observable when a wandering NPC's bark clears the furniture's floating text. Exact player coordinates, before/after dumps, assertions, and screenshots are saved with every case.

Pickup checks reject feed collection at map423,130, then walk close enough to its mesh. They continue through the removed sack’s former space to check that no invisible collider remains and that the item was granted only once. The pie test starts at302,170 and takes short W steps toward the table: the old trigger collected it aroundy180 even though the visible pie is aty223, on the table at90cm. The corrected test expects no health gain there and a gain after walking to the north chair at about302,194.4. That chair physically prevents a closer centreline approach. Elevated pickups use an85cm hand reach beyond the body and a shoulder-height occlusion ray; ground pickups retain30cm. A full-height wall still blocks the elevated hand ray. The first rendered run caught this reach mismatch (11/12 passed); after the fix the private GPU-rendered run passed12/12, recorded in `Saved/Playtest/evidence/interactions-after-private-final/results.json`.


## Private rendered QA without desktop focus

The isolated backend uses a private Xvfb display `:189`, XTest keyboard events, the actual RX6800 Vulkan renderer and framebuffer PNG readback. It never sends input to the user's Wayland desktop. Its Xauthority cookie and the portable official Arch Xvfb binary live only under `/tmp/dink-qa-tools`; TCP is disabled. The controller stages the binary from the official HTTPS package endpoint if missing, records its SHA256, and changes no system packages or desktop configuration. Existing `libX11`, `libXtst`, Pillow, `curl` and `bsdtar` are required on this development machine.

From the project directory, outside the restricted filesystem/process sandbox:

```bash
python3 Scripts/private_qa_session.py start
python3 Scripts/private_qa_session.py inspect
python3 Scripts/playtest_desktop.py --private-display :189 console 'dink.Player'
python3 Scripts/playtest_desktop.py --private-display :189 key space
python3 Scripts/playtest_desktop.py --private-display :189 capture Saved/Playtest/evidence/private-house.png
python3 Scripts/playtest_interactions.py --private-display :189 --out Saved/Playtest/evidence/interactions-after-private
python3 Scripts/private_qa_session.py stop-game
python3 Scripts/private_qa_session.py stop-display
```

Wait until `inspect` reports the game window before sending inputs. Finish opening dialogue with Space until `dink.Player` reports `move_ignored=0`. The same walking routes work with `--private-display :189` before the route subcommand. The backend defaults to `/tmp/dink-qa-private.log`; an alternate controller `--log` must also be supplied explicitly to the test command. Use the controller's default log when stopping with `stop-game`, which validates the private log prefix and X11 arguments before closing that one PID. Stop the private game before a shared C++ build; leave Xvfb running for the next launch. `start` refuses to reuse an unverified display and does not create a second game when one is present.

The launch uses `SDL_VIDEODRIVER=x11`, `-sdlvideodriver=x11`, and `MESA_VK_WSI_DEBUG=sw`. This permits the GPU-rendered normal X11 swapchain with Xvfb's software presentation. `-RenderOffscreen` is deliberately absent: UE5.8 forces SDL's dummy video driver for that flag and removes the real window needed by XTest. The initial readback was visually inspected as a fully rendered 3D house, and the game log identifies RADV/RX6800. These are rendered input tests, separate from `-nullrhi` automation.

Interaction screenshots may use fixture teleports; walking route JSONs retain real W-only traversal. Results explicitly record `private Xvfb:189/XTest` so these events cannot be confused with input on the host desktop. `stop-game` was verified to close only the selected private Dink PID while leaving the host game and compositor untouched.


For a wandering NPC fixture, console setup takes real time and the NPC may move away before E/F is pressed. A temporary `pause` was verified to hold the actual mother's map location; establish a clear, non-door fixture while paused, then resume before the real input. `slomo` does not reliably freeze GameInstance narrative brains and must not be used as the fixture pause. Avoid the south doorway trigger and let the NPC reach a clear aisle before attempting talk. Exact `dink.Origin` observations and script line-counter receipts should accompany character screenshots. Runtime lighting comparisons can use engine `set <full LightComponent object path> Intensity <value>` and `Temperature <kelvin>`; verify the resulting properties with `getall PointLightComponent Intensity` and `Temperature`, then restore original values. These comparisons require no source or map mutation.


The private controller is silent by default. `python3 Scripts/private_qa_session.py start --audio` omits `-nosound` for actual mixer/output verification. Audio uses the machine's normal sound device even though the private game window and input remain isolated. The launch receipt records `audio_enabled`; restarting is required to change it. A silent fixture run proves script audio requests only, not audible playback.


For isolated audio capture, create a temporary session-only PulseAudio null sink, start the game with `start --audio --pulse-sink dink_qa_private`, and record only `dink_qa_private.monitor` with `parec`/`parecord`. This sets the SDL PulseAudio driver and `PULSE_SINK` for that one process. Verify its sink input PID/output before accepting a recording. Do not change the machine's default sink, move other applications, or persist sound-server configuration. Stop the game and unload only the module ID returned by your own `pactl load-module` when done.


After creating that private sink and starting the audio-enabled game, finish the opening dialogue, then run `python3 Scripts/playtest_audio.py --out Saved/Playtest/evidence/audio-private-final`. It verifies the controller's game PID against PulseAudio stream metadata and routes only that PID's streams into the requested private sink if SDL selected an explicit host device. SDL may ignore `PULSE_SINK` when enumerating the default device, so environment variables alone are insufficient proof of isolation. The tool rechecks routing, records approximately six seconds of48kHz stereo PCM (50ms recorder buffer), verifies nonzero music before the attacks, and drives two real F inputs. Receipts retain actual `dink.Audio`/`LogDinkPlayback` output and the original fists procedure counters. Rejected punch9 remains silent; the approved swing8 still plays. This validates actual mixed samples beyond the classic cue journal. The initial game may select approved story music after the house track because the original opening script requests it.

The final verified audio sample is `Saved/Playtest/evidence/audio-private-final/home-music-and-real-fists.wav` (5.95s, peak30433, RMS1857). Final character/door receipts are under `dink-private-model`; the completed NPC body-sweep observation is under `npc-collision-final`. The desktop handoff receipt is `final-host/launch.json`, with a clean game-window screenshot and normal audio enabled. The final host launch used startup console arguments and restored the previously focused app; no keyboard events were sent to the desktop during that launch.

A complete disposable audio run uses a task-specific module ID:

```bash
dink_qa_module=$(pactl load-module module-null-sink sink_name=dink_qa_private sink_properties=device.description=Dink_QA_Private rate=48000 channels=2)
python3 Scripts/private_qa_session.py start --audio --pulse-sink dink_qa_private
# Wait for the window and finish opening dialogue inside the private game.
python3 Scripts/playtest_audio.py --out Saved/Playtest/evidence/audio-private-final
python3 Scripts/private_qa_session.py stop-game
pactl unload-module "$dink_qa_module"
python3 Scripts/private_qa_session.py stop-display
```

Do not reuse a pre-existing sink with that name unless its module receipt is yours. Module IDs come from `load-module` or `pactl list short modules`; this PipeWire version's JSON module listing omits the numeric index. The final QA run verified and removed module536870916 and its own Xvfb/game PIDs only.
