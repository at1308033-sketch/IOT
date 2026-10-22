# -*- coding: utf-8 -*-
"""Vẽ lược đồ quan hệ (ERD) database "smarthome" trên MariaDB cho mục 3.3.2 của báo cáo.

Nguồn: smarthome/db/schema.sql (đã đối chiếu các câu INSERT/UPDATE trong Node-RED).
Cùng bảng màu với ve_luu_do.py; ký hiệu chân chim (crow's foot).

Chạy:  python ve_erd.py [thư_mục_ra]   (mặc định /config/SmartHome_BaoCao/hinh_3_3)
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

from ve_luu_do import ARROW, DPI, STYLE  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/hinh_3_3"
W, H = 100, 80  # 1 đơn vị = 0,1 inch, rộng 10 inch như các lưu đồ
FONT = 8
ROW, HEAD = 3.3, 4.6
KEY_COLOR = {"PK": "#C00000", "FK": "#1F5FA8", "UQ": "#7B3FA0"}
TYPE_COLOR = "#5A5A5A"

plt.rcParams["font.family"] = "DejaVu Sans"

CARDS = ("cards", "Thẻ RFID hợp lệ (danh sách gốc)", [
    ("PK", "id", "INT UNSIGNED, AUTO_INCREMENT"),
    ("UQ", "uid", "VARCHAR(32)"),
    ("", "holder_name", "VARCHAR(100)"),
    ("", "active", "TINYINT(1) = 1"),
    ("", "note", "VARCHAR(255) NULL"),
    ("", "created_at", "DATETIME"),
    ("", "updated_at", "DATETIME (tự cập nhật)"),
])
ACCESS = ("access_log", "Nhật ký quẹt thẻ / mở cửa", [
    ("PK", "id", "BIGINT UNSIGNED, AUTO_INCREMENT"),
    ("", "ts_device", "DATETIME NULL (giờ ESP32)"),
    ("", "ts_server", "DATETIME (giờ Node-RED)"),
    ("", "uid", "VARCHAR(32)"),
    ("FK", "card_id", "INT UNSIGNED NULL → cards.id"),
    ("", "holder_name", "VARCHAR(100) NULL"),
    ("", "result", "ENUM(granted, denied, lockout)"),
    ("", "method", "ENUM(rfid, remote, phone)"),
])
EVENTS = ("events", "Sự kiện cửa và báo động", [
    ("PK", "id", "BIGINT UNSIGNED, AUTO_INCREMENT"),
    ("", "ts_device", "DATETIME NULL"),
    ("", "ts_server", "DATETIME"),
    ("", "type", "VARCHAR(20): door | alarm"),
    ("", "kind", "VARCHAR(20): main | fire | gas | …"),
    ("", "state", "VARCHAR(20): open/closed | on/off"),
])
VIEW = ("v_access_log", "VIEW — lịch sử hiển thị trên HA", [
    ("", "id", "= access_log.id"),
    ("", "ts", "COALESCE(ts_device, ts_server)"),
    ("", "uid", "= access_log.uid"),
    ("", "who", "chủ thẻ / \"Mở từ xa\" / điện thoại"),
    ("", "result", "= access_log.result"),
    ("", "result_vi", "Hợp lệ / Sai thẻ / Khóa tạm"),
    ("", "method", "= access_log.method"),
])


def table(ax, x, top, w, spec, view=False):
    """Vẽ một bảng; trả về {tên cột: y tâm hàng} và đáy bảng."""
    name, desc, rows = spec
    face, edge = STYLE["gray"] if view else STYLE["proc"]
    h = HEAD + ROW * len(rows)
    ls = (0, (4, 2)) if view else "-"
    ax.add_patch(FancyBboxPatch((x, top - h), w, h, boxstyle="round,pad=0,rounding_size=0.6",
                                fc="white", ec=edge, lw=1.2, ls=ls, zorder=2))
    ax.add_patch(FancyBboxPatch((x, top - HEAD), w, HEAD, boxstyle="round,pad=0,rounding_size=0.6",
                                fc=face, ec=edge, lw=1.2, ls=ls, zorder=2))
    ax.add_patch(Rectangle((x + 0.15, top - HEAD), w - 0.3, 0.7, fc=face, ec="none", zorder=2))
    ax.plot([x, x + w], [top - HEAD, top - HEAD], color=edge, lw=1.0, ls=ls, zorder=3)
    ax.text(x + 1.2, top - HEAD / 2, name, fontsize=FONT + 1.5, fontweight="bold",
            ha="left", va="center", color="#1A1A1A", zorder=4)
    ax.text(x + w - 1.2, top - HEAD / 2, desc, fontsize=FONT - 0.8, style="italic",
            ha="right", va="center", color="#404040", zorder=4)
    ys = {}
    for i, (key, col, typ) in enumerate(rows):
        y = top - HEAD - ROW * (i + 0.5)
        ys[col] = y
        if key == "PK":
            ax.add_patch(Rectangle((x + 0.15, y - ROW / 2), w - 0.3, ROW, fc="#FFF7E6", ec="none", zorder=2))
        if i:
            ax.plot([x + 0.6, x + w - 0.6], [y + ROW / 2] * 2, color="#E3E3E3", lw=0.6, zorder=3)
        if key:
            ax.text(x + 1.2, y, key, fontsize=FONT - 1, fontweight="bold", color=KEY_COLOR[key],
                    ha="left", va="center", zorder=4)
        ax.text(x + 5.0, y, col, fontsize=FONT, fontweight="bold" if key == "PK" else "normal",
                ha="left", va="center", color="#1A1A1A", zorder=4)
        ax.text(x + w * 0.42, y, typ, fontsize=FONT - 0.6, color=TYPE_COLOR, family="DejaVu Sans Mono",
                ha="left", va="center", zorder=4)
    return ys, top - h


def crow(ax, x, y, d):
    """Đầu 'không hoặc nhiều' (o<) chạm mép bảng tại (x, y); d = hướng từ mép bảng ra đường nối (±1)."""
    for dy in (-1.1, 0, 1.1):
        ax.plot([x, x + d * 2.0], [y + dy, y], color=ARROW, lw=1.0, zorder=3)
    ax.add_patch(Circle((x + d * 3.3, y), 0.75, fc="white", ec=ARROW, lw=1.0, zorder=4))


def one_opt(ax, x, y, d):
    """Đầu 'không hoặc một' (|o) — card_id được phép NULL."""
    ax.plot([x + d * 1.4] * 2, [y - 1.1, y + 1.1], color=ARROW, lw=1.0, zorder=3)
    ax.add_patch(Circle((x + d * 3.0, y), 0.75, fc="white", ec=ARROW, lw=1.0, zorder=4))


def main():
    fig = plt.figure(figsize=(W / 10, H / 10))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    LX, RX, TW = 1.5, 59.5, 39  # cột trái, cột phải, bề rộng bảng
    yc, c_bottom = table(ax, LX, 77, TW, CARDS)
    ya, a_bottom = table(ax, RX, 77, TW, ACCESS)
    table(ax, LX, 38, TW, EVENTS)
    table(ax, RX, 36, TW, VIEW, view=True)

    # cards.id (0..1) ──── (0..n) access_log.card_id
    x0, x1, xm = LX + TW, RX, (LX + TW + RX) / 2
    y0, y1 = yc["id"], ya["card_id"]
    ax.plot([x0, xm, xm, x1], [y0, y0, y1, y1], color=ARROW, lw=1.0, zorder=1)
    one_opt(ax, x0, y0, d=1)
    crow(ax, x1, y1, d=-1)
    ax.text(xm - 0.8, (y0 + y1) / 2 + 2.6, "1 thẻ có\n0..n lượt quẹt", fontsize=FONT - 0.6,
            color="#C00000", fontweight="bold", ha="right", va="center")
    ax.text(xm + 0.8, (y0 + y1) / 2 - 2.6, "ON DELETE\nSET NULL", fontsize=FONT - 1.2,
            color="#595959", style="italic", ha="left", va="center")

    # Ghi chú cách Node-RED điền card_id/holder_name
    ax.text(LX + 0.4, c_bottom - 3.4,
            "Node-RED ghi access_log bằng LEFT JOIN cards ON uid: thẻ lạ → card_id = NULL;\n"
            "holder_name lưu tên tại lúc quẹt, xóa thẻ không làm mất lịch sử.",
            fontsize=FONT - 1, color="#404040", ha="left", va="center", linespacing=1.35)

    # access_log ⇢ v_access_log
    vx = RX + TW / 2
    ax.annotate("", xy=(vx, 36), xytext=(vx, a_bottom), zorder=1,
                arrowprops=dict(arrowstyle="-|>", color="#808080", lw=1.0, ls=(0, (4, 2)),
                                mutation_scale=9, shrinkA=0, shrinkB=0))
    ax.text(vx + 1.0, (a_bottom + 36) / 2, "SELECT … FROM access_log", fontsize=FONT - 1,
            color="#595959", style="italic", ha="left", va="center")

    # Chú thích ký hiệu + tài khoản truy cập
    ly = 4.0
    ax.text(LX + 0.4, ly, "PK", fontsize=FONT - 1, fontweight="bold", color=KEY_COLOR["PK"], va="center")
    ax.text(LX + 3.2, ly, "khóa chính", fontsize=FONT - 1, color="#404040", va="center")
    ax.text(LX + 12.4, ly, "FK", fontsize=FONT - 1, fontweight="bold", color=KEY_COLOR["FK"], va="center")
    ax.text(LX + 15.2, ly, "khóa ngoại", fontsize=FONT - 1, color="#404040", va="center")
    ax.text(LX + 24.4, ly, "UQ", fontsize=FONT - 1, fontweight="bold", color=KEY_COLOR["UQ"], va="center")
    ax.text(LX + 27.4, ly, "duy nhất", fontsize=FONT - 1, color="#404040", va="center")
    ax.text(LX + 0.4, ly + 3.4,
            "Tài khoản: smarthome_admin (tạo bảng) · nodered_rw (Node-RED ghi/đọc) · ha_ro (Home Assistant chỉ đọc)",
            fontsize=FONT - 1, color="#404040", ha="left", va="center")

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "ERD_MariaDB.png")
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)
    print("OK  " + path)


if __name__ == "__main__":
    main()
