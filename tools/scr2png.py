# scr2png.py: render Sonic R 352x224 menu/credit screens (157696 bytes after RNC unpack) to PNG.
# Layout: 22x14 VDP2 16x16 chars in row order, each char = 4 8x8 cells (TL TR BL BR), RGB555 big-endian.
# usage: py -3.13 -I scr2png.py <unpacked dir> <png dir>
import sys, os
from PIL import Image
def render(d):
    im = Image.new('RGB', (352, 224)); px = im.load()
    for t in range(308):
        tx, ty = t % 22, t // 22
        for c in range(4):
            for i in range(64):
                o = t * 512 + c * 128 + i * 2; v = int.from_bytes(d[o:o + 2], 'big')
                px[tx * 16 + (c & 1) * 8 + i % 8, ty * 16 + (c >> 1) * 8 + i // 8] = \
                    ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3)
    return im
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True); n = 0
for dp, _, fs in os.walk(src):
    for f in fs:
        p = os.path.join(dp, f)
        if os.path.getsize(p) == 157696:
            render(open(p, 'rb').read()).save(os.path.join(dst, f.replace('.', '_') + '.png')); n += 1
print('screens', n)
