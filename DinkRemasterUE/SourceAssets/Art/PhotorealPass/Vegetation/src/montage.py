"""montage.py out.png H file1 file2 ... : paste review renders side by side at height H (review convenience)."""
import sys
from PIL import Image
out, H = sys.argv[1], int(sys.argv[2]); ims = []
for f in sys.argv[3:]:
    try: im = Image.open(f).convert('RGB'); ims.append(im.resize((int(im.width * H / im.height), H), Image.LANCZOS))
    except Exception as e: print('missing', f)
c = Image.new('RGB', (sum(i.width for i in ims) + 4 * len(ims), H), (20, 20, 20)); x = 0
for i in ims: c.paste(i, (x, 0)); x += i.width + 4
c.save(out); print(c.size)
