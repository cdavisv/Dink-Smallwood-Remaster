"""The clip library: name -> clip dict (poses, fps, loop, speed, stride, events, family)."""
import clips_locomotion
import clips_attacks
import clips_people
import clips_mannerisms


def build(rig, only=None):
    makers = {}
    makers.update(clips_locomotion.makers(rig))
    makers.update(clips_attacks.makers(rig))
    makers.update(clips_people.makers(rig))
    makers.update(clips_mannerisms.makers(rig))
    # Preview_* clips are review strips of other clips: built only when asked for by name.
    return {name: maker() for name, maker in makers.items() if (name in only if only else not name.startswith('Preview_'))}
