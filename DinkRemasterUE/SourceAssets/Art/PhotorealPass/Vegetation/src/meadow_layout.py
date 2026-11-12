"""Layout of the meadow grass atlas T_Veg_MeadowGrass (2048^2 px = 1.6 m x 1.6 m, 1.28 px per mm), shared by atlas_meadow.py and veg_meadow.py.
Every tile has its blade roots on the tile's bottom edge. Rects are (x0, y0, w, h) in metres from the atlas bottom-left."""
WORLD = 1.6
TILES = {
 # tall meadow grass, 0.4 x 0.6 m
 'T0': (0.0, 1.0, 0.4, 0.6), 'T1': (0.4, 1.0, 0.4, 0.6), 'T2': (0.8, 1.0, 0.4, 0.6), 'T3': (1.2, 1.0, 0.4, 0.6),
 'T4': (0.0, 0.4, 0.4, 0.6), 'T5': (0.4, 0.4, 0.4, 0.6), 'D0': (0.8, 0.4, 0.4, 0.6), 'D1': (1.2, 0.4, 0.4, 0.6),
 # grazed turf, 0.4 x 0.2 m
 'S0': (0.0, 0.2, 0.4, 0.2), 'S1': (0.4, 0.2, 0.4, 0.2), 'S2': (0.8, 0.2, 0.4, 0.2), 'S3': (1.2, 0.2, 0.4, 0.2),
 'SD0': (0.0, 0.0, 0.4, 0.2), 'SD1': (0.4, 0.0, 0.4, 0.2),
 # dead thatch lying flat (cards laid on the ground between the stems)
 'TH0': (0.8, 0.0, 0.4, 0.2), 'TH1': (1.2, 0.0, 0.4, 0.2),
}
def uv(name, pad=0.0015):
    x, y, w, h = TILES[name]
    return ((x + pad) / WORLD, (y + pad) / WORLD, (x + w - pad) / WORLD, (y + h - pad) / WORLD)
