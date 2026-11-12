"""python3 -I compose_meadow.py : work/meadow_atlas_* -> Export/Textures/T_Veg_MeadowGrass_{BC,N,ORM,SSS}.png"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import compose_atlas
compose_atlas.compose('MeadowGrass', 'meadow_atlas', 1.6, None, 0.2, 10)
