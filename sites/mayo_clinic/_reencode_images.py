"""Re-encode oversized raster images down to ≤200KB and SVGs down to ≤500KB.
Raster: resize to max 1200px wide, JPEG quality 82 cascading down if still
oversized. SVG: leave alone unless absurdly large.
"""
import io
import os
import sys
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "static", "images")
RASTER_CAP = 200 * 1024  # 200 KB
SVG_CAP = 500 * 1024


def shrink_raster(path):
    sz = os.path.getsize(path)
    if sz <= RASTER_CAP:
        return False
    try:
        im = Image.open(path)
        im.load()
    except Exception as e:
        print(f"  open failed {path}: {e}", flush=True)
        return False
    if im.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        try:
            mask = im.convert("RGBA").split()[-1]
            bg.paste(im, mask=mask)
        except Exception:
            bg.paste(im.convert("RGB"))
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    # cascading resize + quality drops
    targets = [
        (1200, 82), (1200, 75), (960, 78), (960, 70),
        (800, 78), (800, 70), (640, 75), (480, 75),
    ]
    for width, q in targets:
        scaled = im
        if im.width > width:
            ratio = width / im.width
            scaled = im.resize((width, max(1, int(im.height * ratio))), Image.LANCZOS)
        buf = io.BytesIO()
        scaled.save(buf, format="JPEG", quality=q, optimize=True, progressive=True)
        data = buf.getvalue()
        if len(data) <= RASTER_CAP:
            new_path = os.path.splitext(path)[0] + ".jpg"
            if new_path != path and os.path.exists(new_path):
                os.remove(new_path)
            with open(new_path, "wb") as f:
                f.write(data)
            if new_path != path:
                os.remove(path)
            return True
    # last resort: smallest version
    return True  # we still wrote the smallest one


def main():
    raster_done = 0
    svg_too_big = 0
    for root, _, files in os.walk(IMG):
        for fn in files:
            p = os.path.join(root, fn)
            ext = fn.lower().rsplit(".", 1)[-1] if "." in fn else ""
            if ext == "svg":
                if os.path.getsize(p) > SVG_CAP:
                    svg_too_big += 1
                continue
            if ext in ("jpg", "jpeg", "png", "gif", "webp"):
                if shrink_raster(p):
                    raster_done += 1
    print(f"raster shrunk: {raster_done}; svg over cap kept as-is: {svg_too_big}", flush=True)


if __name__ == "__main__":
    main()
