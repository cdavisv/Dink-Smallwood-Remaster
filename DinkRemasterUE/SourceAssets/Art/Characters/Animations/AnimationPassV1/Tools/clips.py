"""The clip library: name -> clip dict (poses, fps, loop, speed, stride, events, family)."""
import clips_locomotion
import clips_attacks


def build(rig, only=None):
    makers = {}
    makers.update(clips_locomotion.makers(rig))
    makers.update(clips_attacks.makers(rig))
    return {name: maker() for name, maker in makers.items() if not only or name in only}
