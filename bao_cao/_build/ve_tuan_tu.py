# -*- coding: utf-8 -*-
"""Vẽ Hình 3.11 của báo cáo: sơ đồ tuần tự luồng dữ liệu end-to-end — quẹt thẻ sai → thông báo điện thoại
→ chủ nhà bấm "Mở cửa" → cửa mở → ghi lịch sử. Cùng kiểu với ve_luu_do.py.

Luồng lấy theo esphome/smarthome.yaml (rc522_spi.on_tag, smarthome/cmd/door), smarthome/ha_package.yaml
(smarthome_doan_wrong_card_notify, smarthome_doan_notify_open, smarthome_doan_refresh_sql) và
smarthome/nodered/flows.json.

Chạy:  python ve_tuan_tu.py [thư_mục_ra]   (mặc định /config/SmartHome_BaoCao/hinh_chuong_3)
"""
import sys

import ve_luu_do as base
from ve_luu_do import ARROW, LABEL, LABEL_FONT, Chart

base.OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/hinh_chuong_3"
LANES = [  # (khóa, nhãn, kiểu màu)
    ("dev", "Thẻ · RC522\ncòi · servo", "log"),
    ("esp", "ESP32", "start"),
    ("brk", "Broker\nMosquitto", "gray"),
    ("nr", "Node-RED", "proc"),
    ("db", "MariaDB", "proc"),
    ("ha", "Home Assistant", "proc"),
    ("ph", "Điện thoại\nchủ nhà", "dec"),
]
XS = [7, 21.5, 36, 50.5, 65, 79.5, 94]
STEP = 3.9
MSG_FONT = 6.4


def main():
    msgs = [
        ("phase", "① Có người quẹt thẻ không hợp lệ"),
        ("msg", "dev", "esp", "1. UID thẻ (SPI)"),
        ("note", "esp", "2. So khớp UID với danh sách thẻ trên ESP32 → không hợp lệ"),
        ("msg", "esp", "dev", "3. Còi bíp dài 1,5 s"),
        ("msg", "esp", "brk", "4. publish smarthome/event/access {result: denied} · QoS 1"),
        ("msg", "brk", "nr", "5. Chuyển tin (đã subscribe)"),
        ("msg", "nr", "db", "6. INSERT access_log"),
        ("msg", "brk", "ha", "7. Chuyển tin (smarthome/event/#)"),
        ("msg", "ha", "ph", "8. Thông báo + nút \"Mở cửa\""),
        ("msg", "ha", "db", "9. Cảm biến SQL đọc lại lịch sử"),
        ("phase", "② Chủ nhà bấm \"Mở cửa\" trên thông báo"),
        ("msg", "ph", "ha", "10. Sự kiện nút \"Mở cửa\""),
        ("msg", "ha", "brk", "11. publish smarthome/cmd/door {action: open} · QoS 1"),
        ("msg", "brk", "esp", "12. Chuyển lệnh (đã subscribe)"),
        ("msg", "esp", "dev", "13. Bíp ngắn · servo quay mở 700 ms"),
        ("msg", "esp", "brk", "14. publish event/access {granted, phone} và event/door {open}"),
        ("msg", "brk", "nr", "15. Chuyển tin"),
        ("msg", "nr", "db", "16. INSERT access_log, events"),
        ("msg", "esp", "dev", "17. Hết thời gian mở cửa (10 s) → servo quay đóng"),
    ]
    top = 4 + len(msgs) * STEP + 9
    c = Chart(top, bottom=-2)
    x_of = {}
    head_y = top - 4
    for (key, text, kind), x in zip(LANES, XS):
        face, edge = base.STYLE[kind]
        c.ax.add_patch(base.FancyBboxPatch((x - 6, head_y - 3), 12, 6, boxstyle="round,pad=0,rounding_size=0.35",
                                           fc=face, ec=edge, lw=1.0, zorder=2))
        t = c.ax.text(x, head_y, text, ha="center", va="center", fontsize=base.FONT, color="#1A1A1A", zorder=3,
                      linespacing=1.2, fontweight="bold")
        c.texts.append((key, "box", x, head_y, 12, 6, t))
        c.ax.plot([x, x], [head_y - 3, 0], color="#9A9A9A", lw=0.8, ls=(0, (4, 3)), zorder=0)
        x_of[key] = x

    y = head_y - 3 - STEP
    for m in msgs:
        if m[0] == "phase":
            c.ax.plot([1, 99], [y + 0.9, y + 0.9], color="#D0D0D0", lw=0.7, zorder=0)
            c.ax.text(1, y - 0.2, m[1], fontsize=7, fontweight="bold", color="#1A1A1A", ha="left", va="center",
                      bbox=dict(fc="white", ec="none", pad=1.2), zorder=4)
        elif m[0] == "note":
            x = x_of[m[1]]
            c.ax.text(x + 1.2, y, m[2], fontsize=MSG_FONT, color="#1A1A1A", ha="left", va="center", zorder=4,
                      bbox=dict(boxstyle="round,pad=0.35", fc=base.STYLE["gray"][0], ec=base.STYLE["gray"][1], lw=0.8))
        else:
            _, a, b, text = m
            xa, xb = x_of[a], x_of[b]
            c.ax.annotate("", xy=(xb, y), xytext=(xa, y), zorder=3,
                          arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=0.9, mutation_scale=8,
                                          shrinkA=0, shrinkB=0))
            c.ax.text(min(xa, xb) + 0.8, y + 0.45, text, fontsize=MSG_FONT, color="#1A1A1A", ha="left",
                      va="bottom", zorder=4,
                      bbox=dict(fc="white", ec="none", pad=0.6))
        y -= STEP

    c.ax.text(99, 0.8, "Bước 1–3 và 17 chạy ngay trên ESP32. Nếu quẹt thẻ hợp lệ, ESP32 tự mở cửa mà không cần máy chủ.", fontsize=LABEL_FONT,
              color=LABEL, style="italic", ha="right", va="center",
              bbox=dict(fc="white", ec="none", pad=0.6), zorder=4)
    return c.save("Hinh_3.11_luong_du_lieu.png")


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
