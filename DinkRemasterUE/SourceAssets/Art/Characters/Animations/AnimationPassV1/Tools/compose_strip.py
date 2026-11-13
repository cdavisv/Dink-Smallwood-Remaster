"""Tile rendered frames into one contact strip (run with the system python: needs Pillow)."""
import json, sys
from PIL import Image, ImageDraw
spec = json.load(open(sys.argv[1]))
per_row = 9
blocks = []
for row in spec['rows']:
    tiles = [(Image.open(p).convert('RGB'), label) for p, label in row]
    for start in range(0, len(tiles), per_row):
        blocks.append(tiles[start:start + per_row])
# Interleave: side rows then front rows per chunk
half = len(blocks) // 2
order = []
for i in range(half):
    order += [blocks[i], blocks[half + i]]
width = max(sum(t.width for t, _ in b) for b in order)
height = sum(b[0][0].height for b in order) + 22
sheet = Image.new('RGB', (width, height), (24, 24, 28))
draw = ImageDraw.Draw(sheet)
draw.text((6, 5), spec['title'], fill=(255, 255, 255))
y = 22
for b in order:
    x = 0
    for tile, label in b:
        sheet.paste(tile, (x, y))
        draw.text((x + 4, y + 3), label, fill=(255, 255, 0))
        x += tile.width
    y += b[0][0].height
sheet.save(spec['out'])
