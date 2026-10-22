# -*- coding: utf-8 -*-
"""Vẽ sơ đồ các luồng Node-RED (tab "Smarthome đồ án") cho mục 3.3.1 của báo cáo.

Nguồn: smarthome/nodered/flows.json (sinh từ tools/build_flows.py). Cùng kiểu với ve_luu_do.py.

Chạy:  python ve_nodered.py [thư_mục_ra]   (mặc định /config/SmartHome_BaoCao/hinh_3_3)
"""
import sys

import ve_luu_do as base
from ve_luu_do import LABEL_FONT, STYLE, Chart

base.OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/hinh_3_3"
COLS = [10, 29.5, 49, 68.5, 88]  # tâm 5 cột
BW, BH = 17, 7.5


def lane_title(c, y, text):
    c.ax.text(1, y, text, fontsize=8, fontweight="bold", color="#1A1A1A", ha="left", va="center")
    c.ax.plot([1, 99], [y - 2.2, y - 2.2], color="#D0D0D0", lw=0.6, zorder=0)


def right_to_left(c, a, b):
    (x0, y0), (x1, y1) = c.p(a, "right"), c.p(b, "left")
    if y0 == y1:
        c.edge([(x0, y0), (x1, y1)])
    else:
        xm = (x0 + x1) / 2
        c.edge([(x0, y0), (xm, y0), (xm, y1), (x1, y1)])


def main():
    c = Chart(76, bottom=-9)
    C1, C2, C3, C4, C5 = COLS

    lane_title(c, 72, "① Lịch sử truy cập → bảng access_log")
    y = 63
    c.node("acc_in", "start", C1, y, BW, BH, "MQTT in\nsmarthome/event/access\n(ESP32 →)")
    c.node("acc_fn", "proc", C2, y, BW, BH, "function\nChuẩn bị INSERT\n(LEFT JOIN cards)")
    c.node("acc_db", "log", C3, y, BW, BH, "mysql\nGhi access_log")
    c.node("catch", "gray", C4, y, BW, BH, "catch\nLỗi SQL / MQTT")
    c.node("debug", "gray", C5, y, BW, BH, "debug\nNhật ký")
    right_to_left(c, "acc_in", "acc_fn")
    right_to_left(c, "acc_fn", "acc_db")
    right_to_left(c, "catch", "debug")
    c.ax.text((C4 + C5) / 2, y - BH / 2 - 1.6, "bắt lỗi chung cho cả ba luồng", fontsize=LABEL_FONT,
              color="#595959", style="italic", ha="center", va="center")

    lane_title(c, 54, "② Trạng thái cửa và báo động → bảng events")
    c.node("door_in", "start", C1, 47.5, BW, BH, "MQTT in\nsmarthome/event/door\n(ESP32 →)")
    c.node("alarm_in", "start", C1, 38, BW, BH, "MQTT in\nsmarthome/event/alarm\n(ESP32 →)")
    c.node("ev_fn", "proc", C2, 42.75, BW, BH, "function\nChuẩn bị INSERT\ntype · kind · state")
    c.node("ev_db", "log", C3, 42.75, BW, BH, "mysql\nGhi events")
    right_to_left(c, "door_in", "ev_fn")
    right_to_left(c, "alarm_in", "ev_fn")
    right_to_left(c, "ev_fn", "ev_db")
    c.ax.text(C4 - BW / 2, 42.75,
              "kind: main (cửa) · fire · gas ·\nintrusion · door_stuck",
              fontsize=LABEL_FONT, color="#595959", style="italic", ha="left", va="center")

    lane_title(c, 31, "③ Quản lý thẻ → bảng cards → danh sách thẻ cho ESP32")
    ya, yb, yc = 23.5, 12, 0.5
    c.node("cmd_in", "start", C1, ya, BW, BH, "MQTT in\nsmarthome/cmd/cards\n(HA →)")
    c.node("cmd_fn", "proc", C2, ya, BW, BH, "function\nLệnh thẻ → SQL\nadd/enable/disable/delete")
    c.node("cards_db", "log", C3, ya, BW, BH, "mysql\nCập nhật cards")
    c.node("tick", "gray", C2, yb, BW, BH, "inject\nKhi khởi động\n+ mỗi 1 giờ")
    c.node("q_fn", "proc", C3, yb, BW, BH, "function\nTruy vấn thẻ hợp lệ\n(active = 1)")
    c.node("read_db", "log", C4, yb, BW, BH, "mysql\nĐọc cards")
    c.node("list_fn", "proc", C5, yb, BW, BH, "function\nDanh sách UID\n(\"-\" nếu rỗng)")
    c.node("out", "start", C5, yc, BW, BH, "MQTT out (retained)\nsmarthome/config/cards\n(→ ESP32)")
    right_to_left(c, "cmd_in", "cmd_fn")
    right_to_left(c, "cmd_fn", "cards_db")
    c.edge([c.p("cards_db", "bottom"), c.p("q_fn", "top")])
    right_to_left(c, "tick", "q_fn")
    right_to_left(c, "q_fn", "read_db")
    right_to_left(c, "read_db", "list_fn")
    c.edge([c.p("list_fn", "bottom"), c.p("out", "top")])

    # chú thích màu
    ly = -6
    items = [("start", "nút MQTT vào / ra"), ("proc", "function (JavaScript)"),
             ("log", "mysql (MariaDB)"), ("gray", "inject / catch / debug")]
    x = 2
    for kind, text in items:
        face, edge = STYLE[kind]
        c.ax.add_patch(base.FancyBboxPatch((x, ly - 1.2), 3.2, 2.4, boxstyle="round,pad=0,rounding_size=0.3",
                                           fc=face, ec=edge, lw=1.0))
        c.ax.text(x + 4.2, ly, text, fontsize=LABEL_FONT + 0.4, color="#404040", va="center")
        x += 24
    return c.save("NodeRED_luong_xu_ly.png")


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
