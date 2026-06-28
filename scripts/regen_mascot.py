"""Regenerate the companion mascot + icon PNGs from the source art.

Dev-only tool (needs Pillow). The runtime stays Pillow-free — it just loads the
PNGs/ICO this writes. Run after dropping new source art into `horus/assets/`:

    python scripts/regen_mascot.py            # overwrite horus/assets/*
    python scripts/regen_mascot.py /tmp/out   # write elsewhere to preview

Preferred runtime source is `mascot_without_background.png`, keyed into a real
transparent foreground from its baked checkerboard preview. `background_egypt.png`
is packaged separately so Linux can layer a static card behind the animated bird;
Windows can keep the transparent foreground-only mascot by default.

Legacy fallback sources are the pixel-art `mascot.png` (full body) and `icon.png`
(head/bust), exported on a **solid white background** (with a thin dark line along
the top edge). That fallback pipeline turns them into clean transparent-background
art:

  * floodfill the white background from the borders → transparent. Seeded from the
    edges, so *interior* whites (belly, eye, the white face) survive — only the
    background-connected white is removed.
  * clear the thin dark line the export left along the top edge.
  * defringe — peel the light anti-aliased halo left around the silhouette.
  * autocrop to the content + a small pad, so the bird fills the small mascot window.

The mascot's idle frames are currently identical to the base (the companion bobs the
foreground layer; the old wing-flap was retired with the previous art). Drop a
distinct blink/wing variant here and wire it in if a richer idle is wanted later.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "horus" / "assets"


def _load(name: str) -> Image.Image:
    return Image.open(ASSETS / f"{name}.png").convert("RGBA")


def floodfill_bg(im: Image.Image, thresh: int = 45) -> Image.Image:
    """Knock out the white background, flooding inward from the borders so that
    interior whites (not connected to an edge) are preserved."""
    w, h = im.size
    seeds = [
        (0, h - 1), (w - 1, h - 1), (w // 2, h - 1), (w // 4, h - 1), (3 * w // 4, h - 1),
        (0, h // 2), (w - 1, h // 2),
    ]
    for seed in seeds:
        try:
            ImageDraw.floodfill(im, seed, (0, 0, 0, 0), thresh=thresh)
        except (ValueError, IndexError):
            pass
    return im


def _is_checker_bg(px: tuple[int, int, int, int]) -> bool:
    r, g, b, a = px
    # The source "transparent" export has a baked checkerboard in neutral grays
    # around 189..241. Intentional mascot whites are 254..255 and must survive.
    return a > 0 and max(r, g, b) - min(r, g, b) <= 10 and 175 <= min(r, g, b) <= 245


def key_checkerboard_bg(im: Image.Image) -> Image.Image:
    """Remove the baked checkerboard-preview pixels from the source export."""
    im = im.copy()
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if _is_checker_bg(px[x, y]):
                px[x, y] = (0, 0, 0, 0)
    return im


def clear_dark_edges(im: Image.Image, rows: int = 4, dark: int = 80) -> Image.Image:
    """Drop the thin dark line the export left along the top edge (dark pixels only,
    so a colored crown is untouched)."""
    px = im.load()
    w, h = im.size
    for y in range(min(rows, h)):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and max(r, g, b) < dark:
                px[x, y] = (0, 0, 0, 0)
    return im


def defringe(im: Image.Image, passes: int = 2, light: int = 205) -> Image.Image:
    """Peel light opaque pixels touching transparency (the anti-aliased halo)."""
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


def autocrop(im: Image.Image, pad: int = 6) -> Image.Image:
    """Crop to the opaque content plus a small transparent pad."""
    bbox = im.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        im = im.crop((max(0, left - pad), max(0, top - pad),
                      min(im.width, right + pad), min(im.height, bottom + pad)))
    return im


def keep_largest_opaque_component(im: Image.Image) -> Image.Image:
    """Drop tiny detached specks left by keying a screenshot-style source."""
    im = im.copy()
    px = im.load()
    w, h = im.size
    seen: set[tuple[int, int]] = set()
    largest: set[tuple[int, int]] = set()
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or px[x, y][3] == 0:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            component: set[tuple[int, int]] = set()
            while stack:
                cx, cy = stack.pop()
                component.add((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and px[nx, ny][3] > 0:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            if len(component) > len(largest):
                largest = component

    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 0 and (x, y) not in largest:
                px[x, y] = (0, 0, 0, 0)
    return im


def square_pad(im: Image.Image) -> Image.Image:
    """Center the art on a transparent square canvas (for a well-proportioned .ico)."""
    side = max(im.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return canvas


def prepare(name: str) -> Image.Image:
    return autocrop(defringe(clear_dark_edges(floodfill_bg(_load(name)))))


def prepare_foreground_mascot() -> Image.Image:
    mascot = autocrop(keep_largest_opaque_component(key_checkerboard_bg(_load("mascot_without_background"))), pad=6)
    if (ASSETS / "background_egypt.png").is_file():
        background = _load("background_egypt")
        target_h = int(background.height * 0.63)
        target_w = int(mascot.width * (target_h / mascot.height))
        mascot = mascot.resize((target_w, target_h), Image.Resampling.NEAREST)
    assert mascot.getpixel((0, 0))[3] == 0, "foreground mascot should have transparent corners"
    return mascot


def prepare_layered_mascot() -> Image.Image:
    mascot = autocrop(key_checkerboard_bg(_load("mascot_without_background")), pad=0)
    background = _load("background_egypt")
    target_h = int(background.height * 0.91)
    target_w = int(mascot.width * (target_h / mascot.height))
    mascot = mascot.resize((target_w, target_h), Image.Resampling.NEAREST)
    canvas = background.copy()
    x = (background.width - mascot.width) // 2
    y = background.height - mascot.height - int(background.height * 0.035)
    canvas.alpha_composite(mascot, (x, y))
    return canvas


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sampled_opaque = lambda im: sum(
        1 for y in range(0, im.height, 5) for x in range(0, im.width, 5) if im.getpixel((x, y))[3] > 0
    )

    if (ASSETS / "mascot_without_background.png").is_file():
        mascot = prepare_foreground_mascot()
        assert sampled_opaque(mascot) > 500, "the foreground silhouette was eaten"
    else:
        mascot = prepare("mascot")
        # self-check: background gone (corners transparent) and the bird survived.
        assert mascot.getpixel((0, 0))[3] == 0, "top-left corner is not transparent"
        assert mascot.getpixel((0, mascot.height - 1))[3] == 0, "bottom-left corner is not transparent"
        assert sampled_opaque(mascot) > 500, "the silhouette was eaten"

    mascot.save(out_dir / "mascot.png")
    for frame in ("mascot_idle_0", "mascot_idle_1", "mascot_idle_2", "mascot_blink"):
        mascot.save(out_dir / f"{frame}.png")

    icon = prepare("icon")
    assert icon.getpixel((0, 0))[3] == 0, "icon corner is not transparent"
    icon.save(out_dir / "icon.png")
    square_pad(icon).save(
        out_dir / "icon.ico", format="ICO",
        sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)],
    )

    print(f"wrote mascot (+4 frames), icon.png, icon.ico to {out_dir}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ASSETS
    main(target)
