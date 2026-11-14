#!/usr/bin/env python3
"""Write capture scripts (Scripts/PhotorealQA/run_capture.sh format) for a class-bound creature.

    python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/creatures/pillbug --name pillbug \\
        --play 527:300:250 --over 30:300:250 --over-low 106:300:200 --close 527:300:250 --kill 527:300:250 --crowd 715:300:200

Each <screen>:<mapx>:<mapy> is where the player stands. For every script a twin is written whose shots go to
<out>/before: run that one with the extra argument -dpcvars=dink.CreatureClassArt=0 (sprite cards). The scripts use
only console commands: nothing here changes the game.
"""
import argparse
import os

HEAD = """wait 22
dink.Goto 471 215 125
dink.View 10 5
wait 30
dink.Skip
wait 1
dink.Skip
wait 1
dink.Skip
wait 1
t.MaxFPS 0
r.VSync 0
dink.Fact lifemax 900
dink.Fact life 900
"""


def spot(text):
    screen, x, y = (int(v) for v in text.split(":"))
    return screen, x, y


def play(tag, screen, x, y, shots, gap):
    """Play camera: the player stands, the creatures of the screen do what their brains do."""
    lines = ["dink.Goto %d %d %d" % (screen, x, y), "wait 4", "dink.Player", "dink.CreatureClasses"]
    for i in range(shots):
        lines += ["shot <OUT>/%s_s%d_play_%02d.png" % (tag, screen, i), "wait %s" % gap]
    return lines


def close(tag, screen, x, y, shots, gap, distance):
    """The same camera pulled in, slowed down: several frames of one stride."""
    lines = ["dink.Goto %d %d %d" % (screen, x, y), "wait 4", "dink.CameraDistance %d" % distance, "wait 1", "dink.TimeDilation 0.25"]
    for i in range(shots):
        lines += ["shot <OUT>/%s_s%d_close_%02d.png" % (tag, screen, i), "wait %s" % gap]
    lines += ["dink.TimeDilation 1", "dink.CameraDistance 0", "dink.CreatureClasses"]
    return lines


def kill(tag, screen, x, y, blows):
    """The player hits whatever comes at him with a raised strength: the death and what it leaves."""
    lines = ["dink.Goto %d %d %d" % (screen, x, y), "wait 2", "dink.Fact strength 60", "dink.CameraDistance 260", "wait 1"]
    for i in range(blows):
        lines += ["dink.Attack", "wait 0.2", "shot <OUT>/%s_s%d_kill_%02d_hit.png" % (tag, screen, i), "wait 0.5",
                  "shot <OUT>/%s_s%d_kill_%02d_after.png" % (tag, screen, i), "wait 0.8"]
    lines += ["dink.CreatureClasses", "dink.CameraDistance 0", "dink.Fact strength 1"]
    return lines


def hurt(tag, screen, x, y, origins, camera):
    """Review blows on named placements (dink.Hurt) in slow motion, the camera re-aimed at the creature before every shot
    (dink.CalAnchorOrigin), because a duck covers eight metres a second. `origins` = id[,id...]; each is hurt twice (the
    duck: the head flies off and the body runs on; then the burst). Ten shots after each blow, about 0.06 s of game time apart."""
    lines = ["dink.Goto %d %d %d" % (screen, x, y), "wait 4", "dink.CreatureClasses", "dink.TimeDilation 0.1"]
    for n, origin in enumerate(origins.split(",")):
        for blow in (1, 2):
            lines += ["dink.CalAnchorOrigin %s" % origin, "dink.CalCam %s 1" % camera, "wait 0.3", "dink.Hurt %s 50" % origin]
            for i in range(10):
                lines += ["wait 0.6", "dink.CalAnchorOrigin %s" % origin, "dink.CalCam %s 1" % camera, "shot <OUT>/%s_s%d_hurt_%d_blow%d_%02d.png" % (tag, screen, n, blow, i)]
            lines += ["dink.CreatureClasses"]
        # where it happened, at normal speed a moment later: what is left on the ground
        lines += ["dink.TimeDilation 1", "wait 1.5", "shot <OUT>/%s_s%d_hurt_%d_left.png" % (tag, screen, n), "dink.TimeDilation 0.1"]
    lines += ["dink.TimeDilation 1", "dink.CalCam off"]
    return lines


def over(tag, screen, x, y, shots, gap, camera):
    """A fixed camera above and south of the player's spot, as the 1997 screen was seen: every creature of the screen in
    one picture wherever its brain has taken it. `camera` = x y z tx ty tz hfov (cm from the spot, world axes)."""
    lines = ["dink.Goto %d %d %d" % (screen, x, y), "wait 4", "dink.CalAnchor", "dink.CalCam %s 1" % camera, "wait 0.5", "dink.CreatureClasses"]
    for i in range(shots):
        lines += ["shot <OUT>/%s_s%d_over_%02d.png" % (tag, screen, i), "wait %s" % gap]
    lines += ["dink.CalCam off"]
    return lines


def crowd(tag, screen, x, y):
    lines = ["dink.Goto %d %d %d" % (screen, x, y), "wait 6", "fps %s_s%d_settle" % (tag, screen), "wait 10",
             "fps %s_s%d_crowd" % (tag, screen), "shot <OUT>/%s_s%d_crowd.png" % (tag, screen), "wait 1", "dink.CreatureClasses"]
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output folder, project relative (under Saved/)")
    ap.add_argument("--name", required=True)
    ap.add_argument("--play", action="append", default=[], type=spot)
    ap.add_argument("--close", action="append", default=[], type=spot)
    ap.add_argument("--kill", action="append", default=[], type=spot)
    ap.add_argument("--crowd", action="append", default=[], type=spot)
    ap.add_argument("--hurt", action="append", default=[], help="<screen>:<mapx>:<mapy>:<origin>[,<origin>...]: review blows (dink.Hurt) on placements")
    ap.add_argument("--hurt-camera", default="0 330 190 0 0 25 55")
    ap.add_argument("--over", action="append", default=[], type=spot, help="fixed camera above the spot (whole screen)")
    ap.add_argument("--over-low", action="append", default=[], type=spot, help="the same under a ceiling (interiors)")
    ap.add_argument("--over-camera", default="0 1700 1250 0 -350 0 75")
    ap.add_argument("--over-low-camera", default="0 900 330 0 -500 40 85")
    ap.add_argument("--over-shots", type=int, default=3)
    ap.add_argument("--shots", type=int, default=6)
    ap.add_argument("--gap", default="0.25")
    ap.add_argument("--close-distance", type=int, default=170)
    ap.add_argument("--blows", type=int, default=6)
    args = ap.parse_args()
    project = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    out = os.path.join(project, args.out)
    os.makedirs(out, exist_ok=True)
    body = []
    for s in args.play:
        body += play(args.name, *s, args.shots, args.gap)
    for s in args.over:
        body += over(args.name, *s, args.over_shots, "0.5", args.over_camera)
    for s in args.over_low:
        body += over(args.name, *s, args.over_shots, "0.5", args.over_low_camera)
    for s in args.hurt:
        screen, x, y, origins = s.split(":")
        body += hurt(args.name, int(screen), int(x), int(y), origins, args.hurt_camera)
    for s in args.close:
        body += close(args.name, *s, args.shots, args.gap, args.close_distance)
    for s in args.kill:
        body += kill(args.name, *s, args.blows)
    for s in args.crowd:
        body += crowd(args.name, *s)
    for variant in ("after", "before"):
        folder = "<PROJECT>/%s/%s" % (args.out.rstrip("/"), variant)
        text = HEAD + "\n".join(body).replace("<OUT>", folder) + "\nwait 1\nquit\n"
        path = os.path.join(out, "%s_%s.txt" % (args.name, variant))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(path)


if __name__ == "__main__":
    main()
