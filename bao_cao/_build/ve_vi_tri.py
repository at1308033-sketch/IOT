# -*- coding: utf-8 -*-
"""Vẽ hình vị trí lắp đặt linh kiện trên mặt bằng mô hình nhà (không vẽ dây).

Hình học nhà và tọa độ thiết bị lấy từ /config/www/smarthome/3d/model3d.json (build_dashboard.py
xuất ra, đã áp vị trí người dùng kéo trên dashboard). 1 đơn vị = 1 mm mô hình.
Cửa chính tách 2 điểm: công tắc từ ở mép cửa, servo ở bản lề (theo doors[] trong model3d.json).
ESP32, board mở rộng, adapter, ACS712, relay không có tọa độ trong dữ liệu → khung "Khu mạch điều khiển".

Chạy:  python ve_vi_tri.py [thư_mục_ra] [--khong-tieu-de]   (mặc định /config/SmartHome_BaoCao/so_do_day)
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Arc, FancyBboxPatch, Rectangle  # noqa: E402

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = ARGS[0] if ARGS else "/config/SmartHome_BaoCao/so_do_day"
TIEU_DE = "--khong-tieu-de" not in sys.argv  # Word thường tự thêm chú thích hình → có thể bỏ tiêu đề
MODEL = "/config/www/smarthome/3d/model3d.json"

W_IN = 10  # rộng 10 inch như các hình báo cáo khác (ve_luu_do.py)
DPI = 220
X0, X1 = -25, 775  # khung vẽ theo mm mô hình: nhà 0–500, cột phải 525–775 cho khu điều khiển + chú thích
FONT = 7.2
WALL = "#7a7a7a"
NHAN = "#333333"
LOAI = {  # loại → (màu chấm, tên trong chú thích)
    "cb": ("#2A7AB8", "Cảm biến"),
    "ch": ("#E07B39", "Cơ cấu chấp hành"),
    "dk": ("#7B3FA0", "Mạch điều khiển và nguồn"),
}
# slug trong model3d.json → (nhãn, loại, (dx, dy) của nhãn so với chấm, căn ngang)
THIET_BI = {
    "porch": ("Đèn hiên", "ch", (0, -13), "center"),
    "rfid": ("RFID RC522", "cb", (0, -13), "center"),
    "ldr": ("Quang trở", "cb", (0, -13), "center"),
    "buzzer": ("Còi", "ch", (11, 0), "left"),
    "pir": ("PIR HC-SR501", "cb", (-11, 0), "right"),
    "living": ("Đèn phòng khách", "ch", (6, 16), "right"),
    "rgb": ("LED RGB ×2 (khách + ngủ, chung chân)", "ch", (0, -13), "center"),
    "gas": ("MQ-2 (khí gas)", "cb", (11, 0), "left"),
    "flame": ("Cảm biến lửa", "cb", (11, 0), "left"),
    "fan": ("Quạt hút", "ch", (11, 0), "left"),
    "dht": ("DHT11", "cb", (0, -13), "center"),
    "bedroom": ("Đèn ngủ", "ch", (0, -13), "center"),
}
KHU_DK = ["ESP32 DevKit V1 + board mở rộng", "Adapter 5 V", "ACS712-20A + cầu chia 1k/2k",
          "Module relay 4 kênh"]
# tên phòng → (nhãn, vị trí nhãn) — đặt tránh cung cửa đi
TEN_PHONG = {"PHÒNG KHÁCH": ("PHÒNG KHÁCH (kiêm sảnh)", (165, 92)), "BẾP": ("PHÒNG BẾP", (150, 210)),
             "PHÒNG NGỦ": ("PHÒNG NGỦ", (330, 210))}
NOI_THAT = {"tv": "TV", "sofa": "Sofa", "bed": "Giường", "stove": "Bếp nấu"}

plt.rcParams["font.family"] = "DejaVu Sans"


def cham(ax, x, y, loai):
    ax.plot(x, y, "o", ms=6.5, mfc=LOAI[loai][0], mec="white", mew=1.2, zorder=6)


def nhan(ax, x, y, text, ha="left", size=FONT, **kw):
    ax.text(x, y, text, ha=ha, va="center", fontsize=size, color=kw.pop("color", NHAN), zorder=7, **kw)


def ve():
    m = json.load(open(MODEL, encoding="utf-8"))
    house, devs = m["house"], m["devices"]
    y_top = -75 if TIEU_DE else -50
    y_bot = house["d"] + 22
    h_in = W_IN * (y_bot - y_top) / (X1 - X0)
    fig = plt.figure(figsize=(W_IN, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(X0, X1)
    ax.set_ylim(y_bot, y_top)  # trục y hướng xuống như mặt bằng SVG
    ax.set_aspect("equal")
    ax.axis("off")

    # Dải ngoài tường trước
    ax.add_patch(Rectangle((0, -42), house["w"], 42, fc="#f4f4f4", ec="none", zorder=0))
    nhan(ax, house["w"] - 4, -35, "NGOÀI TƯỜNG TRƯỚC", ha="right", size=7.5, color="#8a8a8a", fontweight="bold")
    # Phòng
    for r in m["rooms"]:
        ax.add_patch(Rectangle((r["x"], r["y"]), r["w"], r["d"], fc=r["color"], ec="none", zorder=0))
    for r in m["rooms"]:
        ten, (x, y) = TEN_PHONG[r["name"]]
        nhan(ax, x, y, ten, ha="center", size=8.5, color="#7a7a7a", fontweight="bold")
    # Nội thất (mờ, chỉ để định hướng)
    for f in m["furniture"]:
        ax.add_patch(Rectangle((f["x"], f["y"]), f["w"], f["d"], fc="white", ec="#b5b5b5", lw=0.8, zorder=1))
        if f["kind"] != "tv":
            nhan(ax, f["x"] + f["w"] / 2, f["y"] + f["d"] / 2, NOI_THAT[f["kind"]], ha="center",
                 size=7, color="#a5a5a5", style="italic")
    # Tường, cửa sổ, cửa đi
    for x1, y1, x2, y2 in m["walls"]:
        ax.plot([x1, x2], [y1, y2], color=WALL, lw=3.2, solid_capstyle="projecting", zorder=3)
    w = m["window"]
    ax.add_patch(Rectangle((w["x1"], -2.5), w["x2"] - w["x1"], 5, fc="white", ec=WALL, lw=0.8, zorder=3))
    ax.plot([w["x1"], w["x2"]], [0, 0], color="#7fb1d8", lw=1.2, zorder=4)
    for d in m["doors"]:
        r = d["x_hinge"] - d["x_free"]
        ax.plot([d["x_hinge"]] * 2, [d["y"], d["y"] + r], color=WALL, lw=1.4, zorder=3)
        ax.add_patch(Arc((d["x_hinge"], d["y"]), 2 * r, 2 * r, theta1=90, theta2=180, color="#a0a0a0",
                         lw=0.8, zorder=2))
    # Thiết bị có tọa độ
    for slug, (ten, loai, (dx, dy), ha) in THIET_BI.items():
        x, y = devs[slug]["x"], devs[slug]["y"]
        cham(ax, x, y, loai)
        nhan(ax, x + dx, y + dy, ten, ha=ha)
    # Cửa chính: công tắc từ ở mép cửa, servo ở bản lề
    cua = next(d for d in m["doors"] if d.get("main"))
    cham(ax, cua["x_free"] + 4, 9, "cb")
    nhan(ax, cua["x_free"] + 4, 21, "Công tắc từ (cửa chính)", ha="center",
         bbox=dict(boxstyle="square,pad=0.1", fc=m["rooms"][0]["color"], ec="none"))  # che cung cửa
    cham(ax, cua["x_hinge"] - 4, 9, "ch")
    nhan(ax, cua["x_hinge"] + 7, 9, "Servo cửa chính 360°", ha="left")

    # Khu mạch điều khiển (không có tọa độ trong dữ liệu)
    bx, by, bw = 528, 0, 240
    bh = 30 + 21 * len(KHU_DK) + 14
    ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0,rounding_size=6", fc="#f6f1fa",
                                ec=LOAI["dk"][0], lw=1.0, ls="--", zorder=1))
    nhan(ax, bx + 10, by + 15, "KHU MẠCH ĐIỀU KHIỂN", size=8, color=LOAI["dk"][0], fontweight="bold")
    for i, ten in enumerate(KHU_DK):
        yy = by + 38 + 21 * i
        cham(ax, bx + 16, yy, "dk")
        nhan(ax, bx + 27, yy, ten)
    nhan(ax, bx + 10, by + bh - 8, "Vị trí trên mô hình: chưa có trong dữ liệu", size=7, color="#8a8a8a",
         style="italic")
    # Chú thích
    ly = by + bh + 32
    nhan(ax, bx + 10, ly, "CHÚ THÍCH", size=8, color="#555555", fontweight="bold")
    for i, (mau, ten) in enumerate(LOAI.values()):
        ax.plot(bx + 16, ly + 20 + 19 * i, "o", ms=6.5, mfc=mau, mec="white", mew=1.2)
        nhan(ax, bx + 27, ly + 20 + 19 * i, ten)
    yk = ly + 20 + 19 * len(LOAI) + 6
    ax.plot([bx + 8, bx + 26], [yk, yk], color=WALL, lw=3.2, solid_capstyle="butt")
    nhan(ax, bx + 32, yk, "Tường · cung xám = cửa đi")
    ax.add_patch(Rectangle((bx + 8, yk + 17), 18, 5, fc="white", ec=WALL, lw=0.8))
    ax.plot([bx + 8, bx + 26], [yk + 19.5, yk + 19.5], color="#7fb1d8", lw=1.2)
    nhan(ax, bx + 32, yk + 19.5, "Cửa sổ")
    nhan(ax, bx + 10, yk + 40, "Mô hình 500 × 355 mm (tỉ lệ 1:20)", size=7, color="#8a8a8a")

    if TIEU_DE:
        nhan(ax, (X0 + X1) / 2, -62, "Vị trí lắp đặt linh kiện trên mô hình", ha="center", size=10,
             color="#222222", fontweight="bold")

    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(OUT, f"vi_tri_lap_dat.{ext}"), dpi=DPI, facecolor="white")
    print("Đã ghi", os.path.join(OUT, "vi_tri_lap_dat.png"))


if __name__ == "__main__":
    ve()
