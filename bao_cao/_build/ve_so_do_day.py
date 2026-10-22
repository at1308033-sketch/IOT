# -*- coding: utf-8 -*-
"""Vẽ sơ đồ đấu dây mạch Smarthome từ day_noi.py → so_do_dau_day.svg + so_do_dau_day.png.

Bố cục: ESP32 DevKit V1 trên board mở rộng ở giữa; 3 đường bao quanh = hàng chân 5V / 3V3 / GND
của board (mỗi chấm = một dây riêng cắm vào hàng chân đó). Cảm biến bên trái, RGB/DHT11/lửa bên phải,
RC522 + servo + còi phía dưới, relay 4 kênh + tải góc dưới phải, nguồn adapter → ACS712 → jack ở trên.
Hình linh kiện: @wokwi/elements + wokwi-boards (assets/wokwi, MIT); ACS712, relay, còi, RGB, DHT11,
công tắc từ, adapter, board mở rộng, tải: tự vẽ. Mọi dây lấy từ day_noi.DAY — script báo lỗi nếu
có dây chưa được vẽ hoặc firmware lệch sơ đồ.

Chạy:  python ve_so_do_day.py [thư_mục_ra] [--khong-tieu-de]   (cần rsvg-convert)
"""
import json
import os
import re
import subprocess
import sys
from xml.sax.saxutils import escape

import day_noi as D

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "assets", "wokwi")
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = _args[0] if _args else "/config/SmartHome_BaoCao/so_do_day"
TIEU_DE = "--khong-tieu-de" not in sys.argv

W, H = 2400, 1790  # 1 đơn vị = 1/240 inch → hình rộng 10 inch như các lưu đồ
PNG_W = 3000  # 300 dpi
PX_MM = 3.7795  # px CSS / mm (đơn vị của pinInfo wokwi)
K_ESP, K_MOD, K_R = 2.6, 2.0, 1.4  # phóng to ESP32 / module / điện trở
S = K_MOD * PX_MM  # đơn vị / mm cho linh kiện tự vẽ
FONT = "DejaVu Sans"
HALO = "#FFFFFF"

# Ba đường bao (hàng chân nguồn board mở rộng): trái, phải, trên, dưới
XL = {"GND": 700, "5V": 716, "3V3": 732}
XR = {"GND": 1732, "5V": 1716, "3V3": 1700}
YT = {"GND": 330, "5V": 346, "3V3": 362}
YB = {"GND": 1200, "5V": 1184, "3V3": 1168}
NET_KIND = {"5V": "5v", "3V3": "3v3", "GND": "gnd"}


# ---------------- tiện ích SVG ----------------
def T(x, y, s, size=14, anchor="start", weight="normal", fill="#222", rot=None, italic=False):
    tf = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{fill}"{st}{tf}>{escape(s)}</text>')


def RECT(x, y, w, h, fill, stroke="none", rx=0, sw=1, extra=""):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def CIRC(cx, cy, r, fill, stroke="none", sw=1):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def LINE(pts, color, w, extra=""):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" '
            f'stroke-linecap="round" {extra}/>')


def header_pin(x, y, horizontal=True):
    """Một chân header: đế đen + chân vàng (x, y = tâm)."""
    return RECT(x - 8, y - 8, 16, 16, "#1A1A1A", rx=2) + RECT(x - 3.5, y - 3.5, 7, 7, "#D4AF37")


# ---------------- linh kiện ----------------
class Part:
    """Thân SVG (gốc tọa độ góc trên trái, kích thước w×h) + chân cục bộ; xoay 0/90/180/270 quanh góc."""

    def __init__(self, body, w, h, pins, x, y, rot=0, alias=None):
        self.body, self.w, self.h, self.pins = body, w, h, pins
        self.x, self.y, self.rot, self.alias = x, y, rot, alias or {}

    def at(self, lx, ly):
        x, y, w, h, r = self.x, self.y, self.w, self.h, self.rot
        return {0: (x + lx, y + ly), 90: (x + h - ly, y + lx), 180: (x + w - lx, y + h - ly),
                270: (x + ly, y + w - lx)}[r]

    def pin(self, name):
        return self.at(*self.pins[self.alias.get(name, name)])

    @property
    def box(self):
        bw, bh = (self.h, self.w) if self.rot in (90, 270) else (self.w, self.h)
        return self.x, self.y, bw, bh

    def svg(self):
        x, y, w, h, r = self.x, self.y, self.w, self.h, self.rot
        t = {0: f"translate({x:.1f},{y:.1f})", 90: f"translate({x + h:.1f},{y:.1f}) rotate(90)",
             180: f"translate({x + w:.1f},{y + h:.1f}) rotate(180)",
             270: f"translate({x:.1f},{y + w:.1f}) rotate(270)"}[r]
        return f'<g transform="{t}">{self.body}</g>'


_uid = [0]


def art(name, k, patch=None, pins_mm=None):
    """Hình wokwi (assets/wokwi/<name>.svg) phóng k lần; id được thêm tiền tố để không trùng."""
    s = open(os.path.join(ART, name + ".svg"), encoding="utf-8").read()
    s = re.sub(r"<\?xml[^>]*\?>|<!--.*?-->", "", s, flags=re.S)
    m = re.search(r"<svg\b[^>]*>", s)
    root = m.group(0)
    wmm = float(re.search(r'\bwidth="([\d.]+)mm"', root).group(1))
    hmm = float(re.search(r'\bheight="([\d.]+)mm"', root).group(1))
    vb = re.search(r'viewBox="([^"]+)"', root).group(1)
    ns = " ".join(re.findall(r'xmlns(?::\w+)?="[^"]*"', root))
    inner = s[m.end():s.rfind("</svg>")]
    _uid[0] += 1
    p = f"w{_uid[0]}-"
    inner = re.sub(r'\bid="([^"]+)"', lambda q: f'id="{p}{q.group(1)}"', inner)
    inner = re.sub(r"url\(#([^)]+)\)", lambda q: f"url(#{p}{q.group(1)})", inner)
    inner = re.sub(r'href="#([^"]+)"', lambda q: f'href="#{p}{q.group(1)}"', inner)
    inner = inner.replace("<clippath", "<clipPath").replace("</clippath>", "</clipPath>")
    if patch:
        inner = patch(inner)
    w, h = wmm * PX_MM * k, hmm * PX_MM * k
    body = f'<svg x="0" y="0" width="{w:.2f}" height="{h:.2f}" viewBox="{vb}" {ns}>{inner}</svg>'
    if pins_mm:
        pins = {n: (a * PX_MM * k, b * PX_MM * k) for n, (a, b) in pins_mm.items()}
    else:
        pins = {q["name"]: (q["x"] * k, q["y"] * k)
                for q in json.load(open(os.path.join(ART, name + ".pins.json")))}
    return body, w, h, pins


def adapter():
    w, h = 200, 130
    b = [RECT(-26, 38, 30, 14, "#9E9E9E", rx=2), RECT(-26, 78, 30, 14, "#9E9E9E", rx=2),
         RECT(0, 0, w, h, "#2B2B2B", rx=16), RECT(10, 10, w - 20, h - 20, "none", "#555", rx=10, sw=2),
         T(w / 2, 58, "ADAPTER", 20, "middle", "bold", "#FFF"), T(w / 2, 86, "DC 5 V", 18, "middle", fill="#FFD54F")]
    return "".join(b), w, h, {"+": (w, 80), "-": (60, 0)}


def acs712():
    w, h = 31 * S, 13 * S
    b = [RECT(0, 0, w, h, "#C0392B", rx=6), CIRC(w - 46, 14, 5, "#FFF"), CIRC(w - 46, h - 14, 5, "#FFF"),
         RECT(0, 6, 62, h - 12, "#1F6FB2", rx=3),
         CIRC(30, 30, 11, "#CFD8DC", "#607D8B", 2), CIRC(30, 70, 11, "#CFD8DC", "#607D8B", 2),
         LINE([(24, 30), (36, 30)], "#455A64", 3), LINE([(24, 70), (36, 70)], "#455A64", 3),
         T(68, 34, "IP−", 13, fill="#FFF", weight="bold"), T(68, 74, "IP+", 13, fill="#FFF", weight="bold"),
         RECT(104, 32, 42, 34, "#111", rx=2), T(125, 53, "712", 11, "middle", fill="#BBB"),
         T(124, 92, "ACS712-20A", 11, "middle", fill="#FFF")]
    pins = {"IP-": (0, 30), "IP+": (0, 70)}
    for i, n in enumerate(["VCC", "OUT", "GND"]):
        y = 30 + i * 19.2
        b += [header_pin(w - 8, y), T(w - 20, y + 4.5, n, 11, "end", fill="#FFF")]
        pins[n] = (w, y)
    return "".join(b), w, h, pins


def reed():
    w, h = 27 * S, 130
    b = [RECT(0, 0, w, 44, "#F5F5F5", "#9E9E9E", rx=6, sw=2), T(w / 2, 28, "nam châm (gắn cánh cửa)", 13, "middle", fill="#555"),
         LINE([(8, 50), (w - 8, 50)], "#BDBDBD", 2, 'stroke-dasharray="6 5"'),
         RECT(0, 56, w, 56, "#FAFAFA", "#9E9E9E", rx=6, sw=2), T(w / 2, 82, "MC-38", 17, "middle", "bold", "#444"),
         T(w / 2, 102, "(gắn khung cửa)", 12, "middle", fill="#777")]
    return "".join(b), w, h, {"1": (w, 72), "2": (w, 100)}


def buzzer():
    w, h = 15 * S, 25 * S
    b = [RECT(0, 0, w, h, "#1E2A47", rx=5), CIRC(w / 2, 118, 44, "#111", "#333", 3), CIRC(w / 2, 118, 8, "#333"),
         T(w / 2 + 26, 88, "+", 16, "middle", "bold", "#EEE"), RECT(18, 40, 20, 14, "#111", rx=2),
         T(w / 2, h - 10, "BUZZER", 11, "middle", fill="#DDD")]
    pins = {}
    for i, n in enumerate(["VCC", "I/O", "GND"]):
        x = 34 + i * 22
        b += [header_pin(x, 8), T(x + 4, 22, n, 10, "end", fill="#FFF", rot=-90)]
        pins[n] = (x, 0)
    return "".join(b), w, h, pins


def rgb_module():
    w, h = 150, 108
    g = f"rg{_uid[0]}"
    _uid[0] += 1
    b = [f'<defs><radialGradient id="{g}" cx="40%" cy="35%" r="65%"><stop offset="0" stop-color="#FFFFFF"/>'
         f'<stop offset="0.45" stop-color="#F8BBD0"/><stop offset="0.75" stop-color="#B3E5FC"/>'
         f'<stop offset="1" stop-color="#C8E6C9"/></radialGradient></defs>',
         RECT(0, 0, w, h, "#212121", rx=6), CIRC(w - 50, h / 2, 34, f"url(#{g})", "#9E9E9E", 2),
         T(w - 50, h / 2 + 5, "RGB", 13, "middle", "bold", "#555")]
    pins = {}
    for i, n in enumerate(["R", "G", "B", "-"]):
        y = 25 + i * 19.2
        b += [header_pin(8, y), T(22, y + 4.5, "−" if n == "-" else n, 11, fill="#FFF")]
        pins[n] = (0, y)
    return "".join(b), w, h, pins


def dht11():
    w, h = 190, 128
    b = [RECT(0, 0, w, h, "#1565C0", rx=6), RECT(70, 6, 104, 116, "#4FA3E0", "#1E6BB8", rx=6, sw=2)]
    for r in range(5):
        for c in range(4):
            b.append(RECT(84 + c * 21, 18 + r * 20, 12, 10, "#2D7FC4", rx=2))
    b.append(T(122, 140 - 12, "", 1))
    pins = {}
    for i, n in enumerate(["VCC", "DATA", "GND"]):
        y = 35 + i * 19.2
        b += [header_pin(8, y), T(22, y + 4.5, n, 11, fill="#FFF")]
        pins[n] = (0, y)
    b.append(T(42, h - 10, "DHT11", 12, "middle", "bold", "#FFF"))
    return "".join(b), w, h, pins


def relay4():
    """Module relay 4 kênh xoay đứng: header trên (VCC IN4 IN3 IN2 IN1 GND), cầu vít bên phải."""
    w, h = 300, 450
    b = [RECT(0, 0, w, h, "#1D4E9E", rx=8), CIRC(14, h - 14, 6, "#FFF"), CIRC(w - 14, h - 14, 6, "#FFF")]
    pins = {}
    for i, n in enumerate(["VCC", "IN4", "IN3", "IN2", "IN1", "GND"]):
        x = 20 + i * 22
        b += [header_pin(x, 9), T(x + 4, 24, n, 10, "end", fill="#FFF", rot=-90)]
        pins[n] = (x, 0)
    b += [RECT(168, 2, 54, 16, "#1A1A1A", rx=2), RECT(172, 4, 28, 12, "#F4D03F", rx=2),
          T(195, 34, "JD-VCC", 10, "middle", fill="#DDD")]
    for k in range(4):
        top = 20 + k * 105
        b += [RECT(40, top + 22, 150, 72, "#2F6FD6", "#174A9C", rx=4, sw=2),
              T(115, top + 54, "SRD-05VDC", 12, "middle", "bold", "#FFF"),
              T(115, top + 72, "SL-C", 11, "middle", fill="#E3F2FD"),
              CIRC(22, top + 58, 6, "#E53935"), T(22, top + 82, f"K{k + 1}", 12, "middle", "bold", "#FFF"),
              RECT(w - 52, top + 6, 52, 90, "#2E8B57", "#1E6B40", rx=3, sw=2)]
        for j, n in enumerate(["NO", "COM", "NC"]):
            y = top + 20 + j * 30
            b += [CIRC(w - 26, y, 10, "#CFD8DC", "#607D8B", 2), LINE([(w - 32, y), (w - 20, y)], "#455A64", 3),
                  T(w - 62, y + 4.5, n, 10, "end", fill="#FFF")]
            pins[f"{n}{k + 1}"] = (w - 26, y) if n == "COM" else (w, y)
    return "".join(b), w, h, pins


def tai(ten, quat=False):
    w, h = 182, 80
    b = [RECT(0, 0, w, h, "#FFFDE7" if not quat else "#E3F2FD", "#BDBDBD", rx=8, sw=2)]
    if quat:
        cx, cy = 40, 40
        b.append(CIRC(cx, cy, 26, "#FFF", "#1565C0", 3))
        for a in (0, 120, 240):
            b.append(f'<ellipse cx="{cx}" cy="{cy - 13}" rx="7" ry="13" fill="#64B5F6" transform="rotate({a} {cx} {cy})"/>')
        b.append(CIRC(cx, cy, 5, "#1565C0"))
    else:
        b += [CIRC(40, 34, 20, "#FFEB3B", "#F9A825", 3), RECT(31, 52, 18, 14, "#9E9E9E", rx=2)]
    lines = ten.split("\n")
    for i, s in enumerate(lines):
        b.append(T(76, 34 + i * 18 - (len(lines) - 1) * 9 + 6, s, 13, weight="bold" if i == 0 else "normal", fill="#333"))
    return "".join(b), w, h, {"+": (0, 30), "-": (w, 30)}


def board():
    w, h = 430, 670
    b = [RECT(0, 0, w, h, "#232526", "#111", rx=12, sw=2)]
    for cx, cy in ((16, 16), (w - 16, h - 16), (16, h - 16)):
        b.append(CIRC(cx, cy, 8, "#555", "#888", 2))
    b += [RECT(80, 70, 20, 440, "#111", rx=3), RECT(330, 70, 20, 440, "#111", rx=3),
          RECT(130, 12, 130, 30, "#111", rx=3)]
    for i, n in enumerate(["5V", "3V3", "GND"]):
        x = 155 + i * 40
        b += [RECT(x - 7, 18, 14, 14, "#D4AF37"), T(x, 56, n, 12, "middle", "bold", "#FFF")]
    b += [T(w / 2, h - 30, "BOARD MỞ RỘNG ESP32 30P", 14, "middle", "bold", "#EEE"),
          T(w / 2, h - 12, "cấp VIN/GND cho ESP32 · ra hàng chân nguồn", 11, "middle", fill="#BBB")]
    return "".join(b), w, h, {"5V": (155, 25), "3V3": (195, 25), "GND": (235, 25)}


def jack():
    w, h = 70, 58
    b = [RECT(0, 6, w, h - 6, "#111", rx=6), CIRC(w / 2, 32, 16, "#333", "#666", 2), CIRC(w / 2, 32, 5, "#BDBDBD")]
    return "".join(b), w, h, {"JACK+": (20, 0), "JACK-": (50, 0)}


# ---------------- đặt linh kiện ----------------
def r2k(svg):
    return svg.replace('fill="#8F4814"', 'fill="#FB0000"')  # 2 kΩ: đỏ-đen-đỏ


P = {}
P["board"] = Part(*board(), 985, 440)
P["jack"] = Part(*jack(), 1320, 440)
P["esp"] = Part(*art("esp32-devkit-v1", K_ESP), 1062, 520)
P["adapter"] = Part(*adapter(), 60, 60)
P["acs"] = Part(*acs712(), 374, 70)
P["r1"] = Part(*art("resistor", K_R), 640, 119.2 - 5.65 * K_R)
P["r2"] = Part(*art("resistor", K_R, patch=r2k), 930, 119.2 - 5.65 * K_R)
P["mq2"] = Part(*art("gas-sensor", K_MOD), 366, 380, alias={"AO": "AOUT", "DO": "DOUT"})
P["cua"] = Part(*reed(), 436, 518)
P["r3"] = Part(*art("resistor", K_R), 736, 620 - (3 * PX_MM * K_R - 5.65 * K_R), rot=180)
P["pir"] = Part(*art("pir-motion-sensor", K_MOD), 456, 670, rot=270)
P["ldr"] = Part(*art("photoresistor-sensor", K_MOD), 292, 880)
P["rc522"] = Part(*art("mfrc522", K_MOD, pins_mm={
    "SDA": (1.63, 10.86), "SCK": (1.63, 13.4), "MOSI": (1.63, 15.94), "MISO": (1.63, 18.48),
    "IRQ": (1.63, 21.02), "GND": (1.63, 23.56), "RST": (1.63, 26.1), "3.3V": (1.63, 28.64)}), 760, 1290, rot=90)
P["servo"] = Part(*art("servo", K_MOD), 1090, 1290, rot=90)
P["coi"] = Part(*buzzer(), 1320, 1290)
P["rgb1"] = Part(*rgb_module(), 1760, 360)
P["rgb2"] = Part(*rgb_module(), 1760, 500)
P["dht"] = Part(*dht11(), 1760, 680)
P["lua"] = Part(*art("flame-sensor", K_MOD), 1800, 860, rot=180, alias={"AO": "AOUT", "DO": "DOUT"})
P["relay"] = Part(*relay4(), 1780, 1300)
for k, (pid, ten) in enumerate([("den_hien", "Đèn hiên\nLED 5 V"), ("den_khach", "Đèn phòng\nkhách 5 V"),
                                ("den_ngu", "Đèn phòng\nngủ 5 V"), ("quat", "Quạt hút\nphòng ngủ 5 V")]):
    P[pid] = Part(*tai(ten, quat=pid == "quat"), 2160, 1310 + k * 105)


def pin(ref):
    p, c = D.tach(ref)
    if p == "board":
        return P["jack" if c.startswith("JACK") else "board"].pin(c)
    return P[p].pin(c)


# ---------------- đường đi của từng dây ----------------
# Dây tín hiệu: "lane" = x đường dọc bên trong vòng nguồn; bên phải relay có thêm "jog" = y đoạn ngang.
LANE = {"mq2:AO": 860, "cua:1": 820, "pir:OUT": 780, "ldr:AO": 800,
        "rgb1:R": 1380, "rgb1:G": 1405, "rgb1:B": 1430, "dht:DATA": 1650, "lua:DO": 1610}
RELAY = {"relay:IN1": (1215, 1555), "relay:IN2": (1230, 1530), "relay:IN3": (1245, 1505), "relay:IN4": (1260, 1480)}
BOTTOM = {"servo:PWM": (1145, 1000), "coi:I/O": (1130, 1030)}  # (jog y, lane x)
RING_SIDE = {"acs": "T", "mq2": "L", "cua": "L", "pir": "L", "ldr": "L", "rc522": "B", "servo": "B",
             "coi": "B", "rgb1": "R", "rgb2": "R", "dht": "R", "lua": "R", "r3": "L"}
GND_BUS_Y, GND_BUS_X, FEED_Y = 1200, 2372, 1150


def ring_stub(p, net, side):
    x, y = p
    if side == "L":
        return [p, (XL[net], y)]
    if side == "R":
        return [p, (XR[net], y)]
    if side == "T":
        return [p, (x, YT[net])]
    return [p, (x, YB[net])]


def route(a, b):
    """→ (danh sách điểm, các điểm cần chấm nối)."""
    pa, pb = pin(a), pin(b)
    part_a, chan_a = D.tach(a)
    # (điểm, có chấm ở cuối không)
    special = {
        ("acs:VCC", "board:5V"): ([pa, (1090, pa[1]), (1090, YT["5V"])], True),
        ("acs:GND", "board:GND"): ([pa, (720, pa[1]), (720, YT["GND"])], True),
        ("acs:OUT", "r1:1"): ([pa, pb], False),
        ("r1:2", "esp:VP"): ([pa, (900, pa[1]), (900, pb[1]), pb], False),
        ("r2:1", "r1:2"): ([pa, (900, pa[1])], True),
        ("r2:2", "board:GND"): ([pa, (1040, pa[1]), (1040, YT["GND"])], True),
        ("adapter:+", "acs:IP+"): ([pa, (pb[0], pa[1])], False),
        ("acs:IP-", "board:JACK+"): ([pa, (340, pa[1]), (340, 46), (pb[0], 46), pb], False),
        ("adapter:-", "board:JACK-"): ([pa, (pa[0], 22), (pb[0], 22), pb], False),
        ("r3:1", "esp:D34"): ([pa, (LANE["cua:1"], pa[1])], True),
        ("relay:VCC", "board:5V"): ([pa, (pa[0], 1280), (1460, 1280), (1460, YB["5V"])], True),
        ("relay:GND", "board:GND"): ([pa, (pa[0], GND_BUS_Y)], True),
        ("relay:COM1", "board:5V"): ([pa, (2032, pa[1]), (2032, FEED_Y), (XR["5V"], FEED_Y)], True),
    }
    if (a, b) in special:
        pts, dot = special[(a, b)]
        return pts, [pts[-1]] if dot else []
    if a.startswith("relay:COM"):  # nối cầu COM: vòng qua thân relay
        return [pa, (2032, pa[1]), (2032, pb[1]), pb], []
    if a.startswith("relay:NO"):
        return [pa, pb], []
    if part_a in ("den_hien", "den_khach", "den_ngu", "quat"):
        return [pa, (GND_BUS_X, pa[1])], [(GND_BUS_X, pa[1])]
    pb_part, pb_chan = D.tach(b)
    if pb_part == "board":  # dây nguồn → đường bao
        pts = ring_stub(pa, pb_chan, RING_SIDE[part_a])
        return pts, [pts[-1]]
    if part_a == "rgb2":  # song song: chấm vào đường dọc của RGB phòng khách
        lane = LANE["rgb1:" + chan_a]
        return [pa, (lane, pa[1])], [(lane, pa[1])]
    if a in RELAY:
        jog, lane = RELAY[a]
        return [pa, (pa[0], jog), (lane, jog), (lane, pb[1]), pb], []
    if a in BOTTOM:
        jog, lane = BOTTOM[a]
        return [pa, (pa[0], jog), (lane, jog), (lane, pb[1]), pb], []
    if part_a == "rc522":
        return [pa, (pa[0], pb[1]), pb], []
    if a in LANE:
        lane = LANE[a]
        return [pa, (lane, pa[1]), (lane, pb[1]), pb], []
    raise SystemExit(f"Chưa có đường cho dây {a} → {b}")


WIDTH = {"tai": 9, "tai_relay": 6}


def mang_dien():
    """Gom các chân cùng điện thế (union-find trên DAY) → {ref: tên mạng}."""
    cha = {}

    def goc(x):
        cha.setdefault(x, x)
        while cha[x] != x:
            x = cha[x]
        return x

    for a, b, _, _ in D.DAY:
        cha[goc(a)] = goc(b)
    return {r: goc(r) for r in cha}


def kiem_tra_chong(doan, chan):
    """doan: [(p, q, mạng)], chan: [(điểm, mạng)]. Lỗi nếu 2 mạng khác nhau đi chồng một đoạn,
    hoặc một dây đi qua chân của mạng khác."""
    loi = []

    def tren(pt, p, q, tol=3):
        (x, y), (x1, y1), (x2, y2) = pt, p, q
        if abs(x1 - x2) < 0.5:
            return abs(x - x1) <= tol and min(y1, y2) - tol <= y <= max(y1, y2) + tol
        return abs(y - y1) <= tol and min(x1, x2) - tol <= x <= max(x1, x2) + tol

    for i, (p1, q1, n1) in enumerate(doan):
        h1 = abs(p1[1] - q1[1]) < 0.5
        for p2, q2, n2 in doan[i + 1:]:
            if n1 == n2 or h1 != (abs(p2[1] - q2[1]) < 0.5):
                continue
            a, b = (1, 0) if h1 else (0, 1)  # a = trục cố định, b = trục chạy
            if abs(p1[a] - p2[a]) > 6:
                continue
            lo = max(min(p1[b], q1[b]), min(p2[b], q2[b]))
            hi = min(max(p1[b], q1[b]), max(p2[b], q2[b]))
            if hi - lo > 2:
                loi.append(f"Chồng dây {n1} / {n2} tại {p1}–{q1}")
    for pt, n in chan:
        for p, q, m in doan:
            if m != n and tren(pt, p, q):
                loi.append(f"Dây {m} đi qua chân {n} tại {pt}")
    return loi


def ve():
    loi = D.kiem_tra()
    if loi:
        raise SystemExit("Sơ đồ lệch firmware:\n  " + "\n  ".join(loi))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">', RECT(0, 0, W, H, "#FFFFFF")]
    # 1. linh kiện nền
    for pid in ("board", "jack", "esp"):
        out.append(P[pid].svg())
    # 2. đường bao nguồn + nhánh GND/5V cho tải bên phải
    ring = []
    for net in ("GND", "5V", "3V3"):
        c = D.MAU[NET_KIND[net]]
        x0, x1, y0, y1 = XL[net], XR[net], YT[net], YB[net]
        ring.append(LINE([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], c, 6))
    ring.append(LINE([(XR["GND"], GND_BUS_Y), (GND_BUS_X, GND_BUS_Y), (GND_BUS_X, 1700)], D.MAU["gnd"], 6))
    out += ring
    dots = []
    # nhánh từ hàng chân board lên đường bao
    for net in ("5V", "3V3", "GND"):
        p = P["board"].pin(net)
        out.append(LINE([p, (p[0], YT[net])], HALO, 12))
        out.append(LINE([p, (p[0], YT[net])], D.MAU[NET_KIND[net]], 6))
        dots.append(((p[0], YT[net]), D.MAU[NET_KIND[net]]))
        dots.append((p, D.MAU[NET_KIND[net]]))
    # 3. linh kiện
    for pid, part in P.items():
        if pid not in ("board", "jack", "esp"):
            out.append(part.svg())
    # 4. dây: dây sau đè dây trước, viền trắng tạo khe ở chỗ cắt nhau (không nối)
    da_ve = 0
    order = sorted(D.DAY, key=lambda d: 0 if d[2] in ("5v", "3v3", "gnd", "tai", "tai_relay") else 1)
    net = mang_dien()
    doan, chan = [], []
    for nm in ("GND", "5V", "3V3"):
        x0, x1, y0, y1 = XL[nm], XR[nm], YT[nm], YB[nm]
        ring_pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        doan += [(ring_pts[i], ring_pts[i + 1], net["board:" + nm]) for i in range(4)]
        bp = P["board"].pin(nm)
        doan.append((bp, (bp[0], YT[nm]), net["board:" + nm]))
    doan += [((XR["GND"], GND_BUS_Y), (GND_BUS_X, GND_BUS_Y), net["board:GND"]),
             ((GND_BUS_X, GND_BUS_Y), (GND_BUS_X, 1700), net["board:GND"])]
    for a, b, loai, _ in order:
        pts, nodes = route(a, b)
        doan += [(pts[i], pts[i + 1], net[a]) for i in range(len(pts) - 1)]
        chan += [(pin(a), net[a]), (pin(b), net[b])]
        w = WIDTH.get(loai, 4.5)
        out.append(LINE(pts, HALO, w + 6))
        out.append(LINE(pts, D.MAU[loai], w))
        for n in nodes:
            dots.append((n, D.MAU[loai]))
        da_ve += 1
    assert da_ve == len(D.DAY)
    loi = kiem_tra_chong(doan, chan)
    if loi:
        raise SystemExit("Hình có dây chồng/đi qua chân khác mạng:\n  " + "\n  ".join(loi))
    # nút chia áp / kéo lên / song song
    for n, c in dots:
        out.append(CIRC(n[0], n[1], 7.5, c, "#FFF", 1.5))
    # 5. nhãn chân ESP32 (đè lên chữ in nhỏ của board)
    esp = P["esp"]
    used = set(D.chan_esp_dung())
    for side, names in (("L", D.ESP_TRAI), ("R", D.ESP_PHAI)):
        for n in names:
            key = n if n != "GND" else ("GND.2" if side == "L" else "GND.1")
            x, y = esp.pin(key)
            g = D.GPIO.get(n)
            if n in used:
                s, col = f"{n} · IO{g}", "#111"
            elif n in ("GND", "VIN", "3V3"):
                s, col = n, "#777"
            else:
                s, col = f"{n} · trống", "#999"
            tw = len(s) * (8.1 if n in used else 7.3) + 8
            bx = x + 12 if side == "L" else x - 12 - tw
            out.append(RECT(bx, y - 9, tw, 18, "#FFFFFF", rx=3, extra='opacity="0.93"'))
            out.append(T(bx + 4, y + 4.5, s, 12.5, weight="bold" if n in used else "normal", fill=col))
    # 6. nhãn chân module (chân trống đánh dấu ×)
    for pid, part in P.items():
        meta = D.LINH_KIEN.get(pid)
        if not meta or pid in ("esp", "board"):
            continue
        for c in meta.get("trong", []):
            x, y = part.pin(c)
            out += [LINE([(x - 6, y - 6), (x + 6, y + 6)], "#C62828", 3), LINE([(x - 6, y + 6), (x + 6, y - 6)], "#C62828", 3)]
    out += nhan_module()
    out += chu_thich()
    out.append("</svg>")
    return "\n".join(out)


def nhan_module():
    """Tên linh kiện, ghi chú ngắn, tên chân cho các module dùng hình wokwi."""
    L = []

    def name(x, y, s, sub=None, anchor="start", size=17):
        L.append(T(x, y, s, size, anchor, "bold", "#1A1A1A"))
        for i, t in enumerate(sub or []):
            L.append(T(x, y + 19 + i * 17, t, 13, anchor, fill="#555"))

    name(160, 222, "Adapter DC 5 V", anchor="middle")
    name(491, 196, "ACS712-20A", ["đo dòng tổng, nuôi 5 V"], anchor="middle")
    L.append(T(681, 162, "1 kΩ", 13, "middle", "bold", "#333"))
    L.append(T(971, 150, "2 kΩ", 13, "middle", "bold", "#333"))
    L.append(T(810, 186, "cầu chia áp", 12.5, "middle", fill=D.MAU["analog"], italic=True))
    L.append(T(810, 203, "IO36 = OUT × 2/3", 12.5, "middle", fill=D.MAU["analog"], italic=True))
    L.append(T(860, 39, "dòng tải đi qua ACS712 →", 12.5, "middle", fill=D.MAU["tai"], italic=True))
    name(352, 420, "MQ-2 (khí gas)", ["nuôi 5 V", "AO → IO39"], anchor="end")
    name(422, 590, "Công tắc từ cửa", ["đóng (có nam châm)", "= nối GND = LOW"], anchor="end")
    L.append(T(772, 607, "1 kΩ kéo lên", 12, "middle", "bold", "#333"))
    name(442, 740, "PIR HC-SR501", ["dây 5 V riêng, không", "chung dây relay/servo"], anchor="end")
    name(278, 925, "Module quang trở", ["nuôi 3V3", "AO → IO32"], anchor="end")
    name(910, 1765, "RFID RC522", None, anchor="middle")
    L.append(T(910, 1784, "chỉ cấp 3V3 · RST nối 3V3", 13, "middle", fill="#555"))
    name(1210, 1655, "Servo cửa 360°", ["IO12 (strapping):", "rút dây tín hiệu", "khi nạp USB lần đầu"], anchor="middle")
    name(1376, 1508, "Còi", ["kích mức THẤP", "nuôi 5 V"], anchor="middle")
    name(1925, 382, "LED RGB phòng khách", ["module có sẵn trở"])
    name(1925, 522, "LED RGB phòng ngủ", ["mắc song song, chung", "3 chân màu"])
    name(1965, 700, "DHT11", ["nuôi 3V3"])
    name(1800, 1012, "Cảm biến lửa", ["nuôi 3V3 · DO thấp = có lửa"])
    name(1930, 1772, "Relay 4 kênh (kích mức THẤP)", None, anchor="middle")
    L.append(T(2251, 1770, "Tải 5 V", 15, "middle", "bold", "#333"))
    # tên chân của module dùng hình wokwi (chữ in trên hình gốc quá nhỏ)
    for pid in ("mq2", "pir", "ldr", "lua", "rc522", "servo"):
        for c in D.LINH_KIEN[pid]["chan"]:
            x, y = P[pid].pin(c)
            if pid in ("rc522", "servo"):
                L.append(T(x - 5, y - 6, c, 10.5, weight="bold", fill="#333", rot=-90))
            elif pid == "lua":
                L.append(T(x - 6, y - 4, c, 10.5, "end", "bold", "#333"))
            else:
                L.append(T(x + 6, y - 4, c, 10.5, weight="bold", fill="#333"))
    # nhãn đường bao
    for net in ("GND", "5V", "3V3"):
        c = D.MAU[NET_KIND[net]]
        L.append(T(XL["GND"] - 8, YT[net] + 4.5, net, 12, "end", "bold", c))
        L.append(T(XL["GND"] - 8, YB[net] + 4.5, net, 12, "end", "bold", c))
    L.append(T(1600, YT["GND"] - 18, "hàng chân nguồn board mở rộng", 12, "middle", fill="#555", italic=True))
    L.append(T(2290, GND_BUS_Y - 8, "GND cho tải", 12, "middle", fill="#222", italic=True))
    L.append(T(1860, FEED_Y - 8, "5 V cho tải → COM1", 12, "middle", fill=D.MAU["5v"], italic=True))
    return L


def chu_thich():
    L = []
    x0, y0 = 40, 1075
    L.append(RECT(x0, y0, 610, 690, "#FAFAFA", "#D0D0D0", rx=10, sw=2))
    L.append(T(x0 + 20, y0 + 34, "Chú thích", 19, weight="bold"))
    keys = ["tai", "5v", "3v3", "gnd", "tai_relay", "analog", "vao", "spi", "pwm", "relay", "rgb_r", "rgb_g", "rgb_b"]
    for i, k in enumerate(keys):
        col, row = i // 7, i % 7
        x, y = x0 + 20 + col * 300, y0 + 66 + row * 30
        L.append(LINE([(x, y), (x + 46, y)], D.MAU[k], WIDTH.get(k, 4.5) if k != "tai" else 8))
        L.append(T(x + 56, y + 5, D.CHU_THICH[k][1], 13.5))
    y = y0 + 66 + 7 * 30 + 6
    L.append(CIRC(x0 + 30, y, 7.5, "#444", "#FFF", 1.5))
    L.append(T(x0 + 56, y + 5, "Chấm tròn = điểm nối", 13))
    y += 30
    L.append(LINE([(x0 + 14, y), (x0 + 46, y)], "#444", 4.5))
    L.append(LINE([(x0 + 30, y - 14), (x0 + 30, y + 14)], HALO, 10))
    L.append(LINE([(x0 + 30, y - 14), (x0 + 30, y + 14)], "#888", 4.5))
    L.append(T(x0 + 56, y + 5, "Dây cắt nhau không có chấm = KHÔNG nối", 13))
    y += 30
    L += [LINE([(x0 + 24, y - 6), (x0 + 36, y + 6)], "#C62828", 3), LINE([(x0 + 24, y + 6), (x0 + 36, y - 6)], "#C62828", 3),
          T(x0 + 56, y + 5, "Chân để trống", 13)]
    y += 40
    L.append(T(x0 + 20, y, "Lưu ý lắp đặt", 15, weight="bold"))
    notes = [
        "• Nguồn: adapter 5 V → ACS712 (IP+ → IP−) → jack DC board",
        "  mở rộng; dòng của mọi tải và ESP32 đều đi qua ACS712.",
        "• Module 3V3: RC522, DHT11, cảm biến lửa, quang trở,",
        "  trở kéo lên IO34. Module 5 V: relay, servo, còi, MQ-2,",
        "  ACS712, PIR (dây riêng).",
        "• IO34/35/36/39 chỉ đọc, không có trở kéo nội.",
        "• Relay và còi kích mức THẤP; khởi động là TẮT hết.",
        "• Mỗi chấm trên đường bao = 1 dây riêng cắm vào hàng",
        "  chân 5V/3V3/GND của board mở rộng.",
        "• Chân ESP32 để trống: EN, TX0, RX0, D14, D2, D15.",
    ]
    for i, s in enumerate(notes):
        L.append(T(x0 + 20, y + 26 + i * 21, s, 13))
    if TIEU_DE:
        L.append(T(2380, 60, "SƠ ĐỒ ĐẤU DÂY MẠCH SMARTHOME", 32, "end", "bold", "#1A1A1A"))
        L.append(T(2380, 92, "ESP32 DevKit V1 (30 chân) trên board mở rộng", 16, "end", fill="#444"))
        L.append(T(2380, 116, "20 chân GPIO khớp esphome/smarthome.yaml (kiểm tra tự động)", 14, "end", fill="#666", italic=True))
    return L


if __name__ == "__main__":
    svg = ve()
    os.makedirs(OUT, exist_ok=True)
    f_svg = os.path.join(OUT, "so_do_dau_day.svg")
    with open(f_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    f_png = os.path.join(OUT, "so_do_dau_day.png")
    subprocess.run(["rsvg-convert", "-w", str(PNG_W), "-b", "white", f_svg, "-o", f_png], check=True)
    print(f_svg, f_png, sep="\n")
