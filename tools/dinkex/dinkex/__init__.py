"""dinkex: extract the original Dink Smallwood (1997) data into a neutral
intermediate representation (JSON + PNG) for the 3D remaster pipeline.

See README.md for the output schema.  Byte layouts are documented in
doc/remaster/bible/04-engine-and-file-formats.md section 1; engine behaviour
is cited as "D:<line>" against source/dink/dink.cpp.
"""

__version__ = "1.0.0"
SCHEMA_VERSION = 1

# Geometry constants (dink.h / dink.cpp)
SCREENS_X = 32
SCREENS_Y = 24
SCREEN_COUNT = SCREENS_X * SCREENS_Y      # 768; screens are numbered 1..768
PLAY_W = 600
PLAY_H = 400
TILE = 50
TILES_X = 12
TILES_Y = 8
TILES_PER_SCREEN = TILES_X * TILES_Y      # 96
TILES_PER_SET = 128                       # D:6774: set = num // 128 + 1
SPRITE_X_OFFSET = 20                      # sprite x includes the 20 px side bar
