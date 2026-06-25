"""Regenerate the companion mascot PNGs from the source art.

Dev-only tool (needs Pillow). The runtime stays Pillow-free — it just loads the
PNGs this writes. Run after editing the source `mascot.png`:

    python scripts/regen_mascot.py            # overwrite horus/assets/*.png
    python scripts/regen_mascot.py /tmp/out   # write elsewhere to preview

What it does:
  * defringe — peel the near-white halo the alpha key left around the silhouette,
    preserving interior whites (hat, eye, belly) since those aren't edge pixels.
  * keep only sizeable connected blobs — drops keying specks/artifacts.
  * idle_1/idle_2 — lift the green wing a few px over the body for a gentle flap
    (no tearing: the vacated strip just shows the body that was behind the wing).
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "horus" / "assets"

# Wing bounding box (source px) + the lift heights for the two flap frames.
WING_BOX = (240, 410, 600, 780)
WING_LIFTS = (7, 14)


def _load(name: str) -> Image.Image:
    return Image.open(ASSETS / f"{name}.png").convert("RGBA")


def defringe(im: Image.Image, passes: int = 3, light: int = 170) -> Image.Image:
    """Remove light opaque pixels touching transparency, `passes` times."""
    w, h = im.size
    for _ in range(passes):
        px = im.load()
        kill = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a == 0 or min(r, g, b) < light:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < w and 0 <= ny < h) or px[nx, ny][3] == 0:
                        kill.append((x, y))
                        break
        for x, y in kill:
            px[x, y] = (0, 0, 0, 0)
    return im


def keep_big(im: Image.Image, minsize: int = 1000) -> Image.Image:
    """Drop connected opaque blobs smaller than `minsize` pixels."""
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 0 and not seen[y][x]:
                q = deque([(x, y)])
                seen[y][x] = True
                cells = []
                while q:
                    cx, cy = q.popleft()
                    cells.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and px[nx, ny][3] > 0:
                            seen[ny][nx] = True
                            q.append((nx, ny))
                if len(cells) < minsize:
                    for cx, cy in cells:
                        px[cx, cy] = (0, 0, 0, 0)
    return im


def clean(im: Image.Image) -> Image.Image:
    return keep_big(defringe(im))


def lift_wing(base: Image.Image, lift: int) -> Image.Image:
    """Composite the green wing pixels, raised by `lift` px, over a copy of base.

    Vacated pixels keep the body the wing was sitting on, so nothing tears.
    """
    out = base.copy()
    src = base.load()
    dst = out.load()
    x0, y0, x1, y1 = WING_BOX
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = src[x, y]
            # green wing pixel: green dominates and is reasonably saturated
            if a > 0 and g > 90 and g >= r + 20 and g >= b + 20:
                ty = y - lift
                if ty >= 0:
                    dst[x, ty] = (r, g, b, a)
    return out


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    opaque = lambda im: sum(im.getchannel("A").histogram()[1:])
    raw_opaque = opaque(_load("mascot"))
    base = clean(_load("mascot"))
    flap = lift_wing(base, WING_LIFTS[1])

    # self-check: defringe trimmed pixels, and the wing actually moved.
    assert opaque(base) < raw_opaque, "defringe removed nothing"
    assert flap.tobytes() != base.tobytes(), "wing did not move"

    base.save(out_dir / "mascot.png")
    base.save(out_dir / "mascot_idle_0.png")
    clean(_load("mascot_blink")).save(out_dir / "mascot_blink.png")
    lift_wing(base, WING_LIFTS[0]).save(out_dir / "mascot_idle_1.png")
    flap.save(out_dir / "mascot_idle_2.png")
    print(f"wrote 5 frames to {out_dir}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ASSETS
    main(target)
