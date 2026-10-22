# -*- coding: utf-8 -*-
"""Vẽ Hình 3.1 của báo cáo: kiến trúc 5 tầng IoT của hệ thống (Sensor/Actuator → Edge → Network →
Server → Application, đúng thứ tự trong barem). Cùng kiểu với ve_luu_do.py.

Chạy:  python ve_kien_truc.py [thư_mục_ra]   (mặc định /config/SmartHome_BaoCao/hinh_chuong_3)
"""
import sys

import ve_luu_do as base
from ve_luu_do import FONT, LABEL_FONT, STYLE, Chart

base.OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/hinh_chuong_3"
ROW_H = 9
X0, X1 = 21, 99  # vùng khối nội dung
HEAD_X, HEAD_W = 10, 17


def box(c, key, style, x, y, w, h, text, bold=False):
    face, edge = STYLE[style]
    c.ax.add_patch(base.FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.35",
                                       fc=face, ec=edge, lw=1.0, zorder=2))
    t = c.ax.text(x, y, text, ha="center", va="center", fontsize=FONT, color="#1A1A1A", zorder=3,
                  linespacing=1.25, fontweight="bold" if bold else "normal")
    c.texts.append((key, "box", x, y, w, h, t))
    c.nodes[key] = (x, y, w, h)


def row(c, name, style, y, head, items):
    box(c, name, style, HEAD_X, y, HEAD_W, ROW_H, head, bold=True)
    gap = 1.5
    w = (X1 - X0 - gap * (len(items) - 1)) / len(items)
    for i, text in enumerate(items):
        box(c, f"{name}{i}", style, X0 + w / 2 + i * (w + gap), y, w, ROW_H, text)


def link(c, lower, upper, text):
    """Cặp mũi tên giữa hai tầng (dữ liệu đi lên, lệnh đi xuống) + chú thích trong khoảng trống."""
    _, y_lo, _, h = c.nodes[lower]
    y_a, y_b = y_lo + h / 2, c.nodes[upper][1] - h / 2
    c.edge([(HEAD_X - 1.6, y_a), (HEAD_X - 1.6, y_b)])
    c.edge([(HEAD_X + 1.6, y_b), (HEAD_X + 1.6, y_a)])
    c.ax.text(X0, (y_a + y_b) / 2, text, fontsize=LABEL_FONT, color="#595959", style="italic",
              ha="left", va="center")


def main():
    c = Chart(66, bottom=-7)
    ys = {"app": 60, "srv": 46, "net": 32, "edge": 18, "dev": 4}
    row(c, "app", "dec", ys["app"], "Tầng ứng dụng\n(Application)", [
        "Dashboard Home Assistant\n5 trang · mặt bằng 2D · 3D",
        "App Home Assistant Companion\nthông báo · NFC · widget",
        "Trợ lý giọng nói Assist\ncâu lệnh tiếng Việt",
        "Giao diện web dự phòng\nchạy ngay trên ESP32",
    ])
    row(c, "srv", "proc", ys["srv"], "Tầng máy chủ\n(Server)", [
        "Mosquitto\nMQTT broker",
        "Home Assistant\nautomation · discovery · SQL",
        "Node-RED\nghi sự kiện · quản lý thẻ",
        "MariaDB\ncards · access_log · events",
    ])
    row(c, "net", "gray", ys["net"], "Tầng mạng\n(Network)", [
        "Wi-Fi 2,4 GHz (802.11 b/g/n)\nESP32 ở chế độ station",
        "Router · TCP/IP\nESP32 mở kết nối tới broker (cổng 1883)",
        "Giao thức MQTT\npublish/subscribe · QoS 0/1 · retained · Last Will",
    ])
    row(c, "edge", "start", ys["edge"], "Tầng thiết bị biên\n(Edge Device)", [
        "ESP32 DevKit V1 + firmware ESPHome\n"
        "Đọc và lọc tín hiệu cảm biến · chạy toàn bộ kịch bản an toàn ngay trên chip\n"
        "(cửa, cháy/gas, vắng nhà, đèn hiên, quạt hút) · gửi sự kiện và trạng thái, nhận lệnh",
    ])
    row(c, "dev", "log", ys["dev"], "Tầng cảm biến\nvà chấp hành", [
        "Đầu vào: RFID RC522 · công tắc từ MC-38 · PIR HC-SR501\n"
        "quang trở · DHT11 · cảm biến lửa · MQ-2 · ACS712-20A",
        "Đầu ra: servo 360° (cửa) · relay 4 kênh (đèn hiên,\n"
        "đèn phòng khách, đèn phòng ngủ, quạt hút) · còi · LED RGB",
    ])
    link(c, "dev", "edge", "GPIO · ADC1 · SPI · giao tiếp một dây · PWM (LEDC)")
    link(c, "edge", "net", "Wi-Fi")
    link(c, "net", "srv", "MQTT trên TCP/IP")
    link(c, "srv", "app", "giao diện web · thông báo đẩy · giọng nói")
    c.ax.text(50, -4.2,
              "Mũi tên ↑: dữ liệu và sự kiện đi lên · mũi tên ↓: lệnh điều khiển đi xuống.\n"
              "Kịch bản an toàn đặt ở tầng thiết bị biên nên vẫn chạy khi tầng mạng hoặc tầng máy chủ gặp sự cố; "
              "các tầng trên chỉ lo giám sát, điều khiển từ xa, thông báo và lưu lịch sử.",
              fontsize=LABEL_FONT, color="#595959", style="italic", ha="center", va="center")
    return c.save("Hinh_3.1_kien_truc_5_tang.png")


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
