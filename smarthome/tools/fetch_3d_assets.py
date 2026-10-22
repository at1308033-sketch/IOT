#!/usr/bin/env python3
"""Tải texture/model CC0 (Poly Haven, 1k) cho thẻ 3D "nhà thật".

Chạy lại được (bỏ qua file đã đủ kích thước). JPG được nén lại (Pillow, 4:4:4); kích thước sau nén
ghi trong assets/.recompressed.json để lần chạy sau không tải lại. Ghi manifest.json + LICENSE.md, in tổng dung lượng.
repeat_mm = kích thước thật của một ô vân (mm) / 20 (tỉ lệ 1:20 của mô hình).
size_mm = [rộng, sâu, cao] mục tiêu của đồ nội thất (mm mô hình, 1:20).
"""
import json
import sys
import urllib.request
from pathlib import Path

API = "https://api.polyhaven.com/files/"
OUT = Path("/config/www/smarthome/3d/assets")
MAX_BYTES = 15 * 1024 * 1024

# key -> (id Poly Haven, repeat_mm)   [kích thước thật: ghi chú bên phải]
TEXTURES = {
    "floor_wood": ("laminate_floor_02", 85),         # 1700 mm
    "floor_tile_kitchen": ("interior_tiles", 95),    # 1900 mm
    "wall_plaster": ("white_plaster_02", 50),        # 1000 mm
    "wall_exterior": ("white_stucco", 100),          # 1998 mm
    "paving": ("rectangular_paving", 100),           # 2000 mm
    "grass": ("leafy_grass", 100),                   # 2000 mm
    "countertop": ("marble_01", 75),                 # 1500 mm
    "fabric_bed": ("rough_linen", 14),               # 271 mm
}
# key -> (id Poly Haven, size_mm [rộng, sâu, cao] = kích thước thật / 20)
MODELS = {
    "sofa": ("sofa_02", [90, 41, 35]),                      # 1807 x 818 x 709
    "coffee_table": ("modern_coffee_table_01", [60, 30, 20]),  # 1200 x 600 x 390
    "armchair": ("modern_arm_chair_01", [41, 49, 51]),      # 820 x 987 x 1023
    "nightstand": ("painted_wooden_nightstand", [25, 25, 31]),  # 505 x 509 x 616
    "shelf": ("wooden_display_shelves_01", [54, 19, 78]),   # 1078 x 372 x 1556
    "plant": ("potted_plant_02", [35, 33, 42]),             # 701 x 657 x 841
}
TEX_MAPS = {"diff": "Diffuse", "nor": "nor_gl", "arm": "arm"}


def _open(url, timeout):
    # Poly Haven chặn User-Agent mặc định của urllib
    req = urllib.request.Request(url, headers={"User-Agent": "smarthome-doan/1.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url):
    with _open(url, 60) as r:
        return json.load(r)


QUALITY = 85      # nén lại JPEG để tổng dung lượng <= 15 MB
QUALITY_DATA = 90  # arm/nor
STAMP = OUT / ".recompressed.json"   # rel -> kích thước sau khi nén (để chạy lại không tải lại)


def recompress(data, quality):
    """Nén lại JPEG (giữ độ phân giải 1k); chỉ dùng nếu nhỏ hơn bản gốc."""
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).convert("RGB").save(
        buf, "JPEG", quality=quality, optimize=True, progressive=True,
        subsampling=0)  # 4:4:4: không làm mờ kênh màu của bản đồ dữ liệu (arm/nor)
    return buf.getvalue() if buf.tell() < len(data) else data


def download(url, dest, size):
    """Tải nếu thiếu hoặc sai kích thước (JPG được nén lại và ghi nhớ kích thước mới)."""
    stamp = json.loads(STAMP.read_text()) if STAMP.is_file() else {}
    rel = str(dest.relative_to(OUT))
    if dest.is_file() and dest.stat().st_size in (size, stamp.get(rel)):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _open(url, 120) as r:
        data = r.read()
    if len(data) != size:
        raise RuntimeError(f"sai kích thước: {dest}")
    if dest.suffix == ".jpg":
        # diffuse nén mạnh hơn; arm/nor giữ chất lượng cao
        data = recompress(data, QUALITY if "_diff_" in dest.name else QUALITY_DATA)
        stamp[rel] = len(data)
        STAMP.write_text(json.dumps(stamp, indent=1))
    dest.write_bytes(data)
    print("tải", rel)


def main():
    manifest = {"textures": {}, "models": {}, "source": "Poly Haven", "license": "CC0",
                "ids": {}}
    for key, (aid, repeat) in TEXTURES.items():
        files = get_json(API + aid)
        entry = {}
        for short, name in TEX_MAPS.items():
            f = files[name]["1k"]["jpg"]
            rel = f"textures/{aid}_{short}_1k.jpg"
            download(f["url"], OUT / rel, f["size"])
            entry[short] = rel
        entry["repeat_mm"] = repeat
        manifest["textures"][key] = entry
        manifest["ids"][key] = aid
    for key, (aid, size) in MODELS.items():
        g = get_json(API + aid)["gltf"]["1k"]["gltf"]
        base = OUT / "models" / aid
        download(g["url"], base / f"{aid}_1k.gltf", g["size"])
        for rel, f in g["include"].items():
            download(f["url"], base / rel, f["size"])
        manifest["models"][key] = {"gltf": f"models/{aid}/{aid}_1k.gltf", "size_mm": size}
        manifest["ids"][key] = aid
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lines = ["# Giấy phép tài nguyên 3D", "",
             "Tất cả texture và model dưới đây lấy từ [Poly Haven](https://polyhaven.com), "
             "giấy phép **CC0** (public domain, dùng tự do, không cần ghi nguồn).", ""]
    for key, aid in manifest["ids"].items():
        lines.append(f"- `{aid}` ({key}): https://polyhaven.com/a/{aid} - CC0")
    (OUT / "LICENSE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"Tổng dung lượng: {total / 1048576:.2f} MB")
    if total > MAX_BYTES:
        sys.exit("vượt 15 MB")


if __name__ == "__main__":
    main()
