# -*- coding: utf-8 -*-
"""Vẽ Hình 2.2 của báo cáo: mô hình publish/subscribe MQTT trong hệ thống. Cùng kiểu với ve_luu_do.py.

Chủ đề lấy theo esphome/smarthome.yaml, smarthome/ha_package.yaml và smarthome/nodered/flows.json.

Chạy:  python ve_pub_sub.py [thư_mục_ra]   (mặc định /config/SmartHome_BaoCao/hinh_chuong_2)
"""
import sys

import ve_luu_do as base
from ve_luu_do import LABEL, LABEL_FONT, Chart

base.OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/hinh_chuong_2"
TOPIC_FONT = 6.2
BW = 14
X_ESP, X_BROKER, X_CLIENT = 8, 50, 92


def link(c, frm, to, y, role, topics):
    """Mũi tên ngang giữa hai khối; danh sách chủ đề phía trên, vai trò (publish/nhận) phía dưới."""
    x_l, x_r = c.nodes[frm][0], c.nodes[to][0]
    x0 = x_l + BW / 2 if x_l < x_r else x_l - BW / 2
    x1 = x_r - BW / 2 if x_l < x_r else x_r + BW / 2
    c.edge([(x0, y), (x1, y)])
    left = min(x0, x1)
    t = c.ax.text(left + 1, y + 0.7, "\n".join(topics), fontsize=TOPIC_FONT, color="#1A1A1A",
                  ha="left", va="bottom", linespacing=1.3)
    c.ax.text(left + 1, y - 0.7, role, fontsize=LABEL_FONT, color=LABEL, fontweight="bold",
              ha="left", va="top")
    c.topic_texts.append((t, left, max(x0, x1)))


def topics_fit(c):
    c.fig.canvas.draw()
    inv = c.ax.transData.inverted()
    ok = True
    for t, x_min, x_max in c.topic_texts:
        bb = t.get_window_extent()
        (x0, _), (x1, _) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        if x0 < x_min or x1 > x_max - 0.5:
            print(f"CHỮ TRÀN khoảng trống: {t.get_text().splitlines()[0]} ({x0:.1f}–{x1:.1f}, cho phép {x_min}–{x_max})")
            ok = False
    return ok


def main():
    c = Chart(58, bottom=-5)
    c.topic_texts = []
    c.node("esp", "proc", X_ESP, 30, BW, 48, "ESP32\n(ESPHome)\n\nclient MQTT")
    c.node("broker", "log", X_BROKER, 30, BW, 48,
           "MQTT broker\nMosquitto\n\nadd-on trên\nmáy chủ\nHome Assistant\n\ncổng 1883")
    c.node("ha", "proc", X_CLIENT, 43, BW, 22, "Home Assistant\n\nclient MQTT")
    c.node("nr", "proc", X_CLIENT, 17, BW, 22, "Node-RED\n(ghi MariaDB)\n\nclient MQTT")

    link(c, "esp", "broker", 40, "ESP32 publish", [
        "smarthome/event/access, door, alarm",
        "smarthome-doan/…/state  (trạng thái)",
        "homeassistant/…/config  (discovery)",
        "smarthome-doan/status  (online/offline)",
    ])
    link(c, "broker", "esp", 16, "ESP32 nhận (đã subscribe)", [
        "smarthome/config/cards  (thẻ hợp lệ)",
        "smarthome/cmd/door  (điện thoại)",
        "smarthome-doan/…/command (lệnh từ HA)",
    ])
    link(c, "ha", "broker", 47, "Home Assistant publish", [
        "smarthome-doan/…/command (bật/tắt, mở cửa)",
        "smarthome/cmd/door  (điện thoại)",
        "smarthome/cmd/cards  (thêm/khóa/xóa thẻ)",
    ])
    link(c, "broker", "ha", 35, "Home Assistant nhận (đã subscribe)", [
        "homeassistant/…/config",
        "smarthome-doan/…/state, smarthome-doan/status",
        "smarthome/event/#  (thông báo, làm mới lịch sử)",
    ])
    link(c, "nr", "broker", 23, "Node-RED publish", [
        "smarthome/config/cards  (retained)",
    ])
    link(c, "broker", "nr", 10, "Node-RED nhận (đã subscribe)", [
        "smarthome/event/access, door, alarm",
        "smarthome/cmd/cards",
    ])

    c.ax.text(50, -2.2,
              "Lệnh, danh sách thẻ và sự kiện dùng QoS 1 · trạng thái cảm biến dùng QoS 0 · "
              "danh sách thẻ và gói discovery có cờ retain · "
              "smarthome-doan/status là Last Will (broker tự gửi \"offline\" khi ESP32 mất kết nối)",
              fontsize=LABEL_FONT, color="#595959", style="italic", ha="center", va="center", wrap=True)
    ok = topics_fit(c)
    return c.save("Hinh_2.2_pub_sub.png") and ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
