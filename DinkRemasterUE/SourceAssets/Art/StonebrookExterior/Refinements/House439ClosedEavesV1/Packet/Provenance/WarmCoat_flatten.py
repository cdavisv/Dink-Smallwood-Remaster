from pathlib import Path

import numpy as np
from PIL import Image

folder = Path(__file__).resolve().parent
source = folder.parent / 'RoofFamilyMajorSuccessorV21'
size = (2048, 2048)

def read(path):
    return np.asarray(Image.open(path).convert('RGB').resize(size, Image.Resampling.BILINEAR), dtype=np.float32) / 255

photo = read(source / 'T_Shared_LaidWeatheredPhotoCoat2m_BC.png')
linear = np.where(photo <= .04045, photo/12.92, ((photo+.055)/1.055)**2.4)
warm = read(folder.parent / 'WholeRoofWarmTilesV1/T_WarmColor_Repeat.png') * 2
edges = read(folder.parent / 'WholeRoofBundleTileV1/T_BundleMultiplier_Repeat.png')
linear = np.clip(linear * warm * (.38 + .62*edges),0,1)
srgb = np.where(linear <= .0031308, linear*12.92, 1.055*linear**(1/2.4)-.055)
Image.fromarray(np.rint(srgb*255).astype(np.uint8)).save(folder/'T_WarmBundleCoat_BC.png')
