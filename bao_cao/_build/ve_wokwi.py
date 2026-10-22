# -*- coding: utf-8 -*-
"""Sinh dự án Wokwi (chỉ sơ đồ đấu dây, KHÔNG có code) từ bảng đấu dây day_noi.py.

Ra: SmartHome_BaoCao/so_do_day/wokwi/
  diagram.json            — dán vào dự án ESP32 mới trên wokwi.com
  <tên>.chip.json/.chip.c — linh kiện Wokwi không có (ACS712, adapter, công tắc từ, module còi,
                            cảm biến lửa, quạt): hộp xanh mang đúng tên chân, chip.c rỗng
  README.md               — cách mở + linh kiện nào thay cho linh kiện nào

Tọa độ chân lấy đúng theo mã nguồn Wokwi: @wokwi/elements 1.9.2 (pinInfo), wokwi-boards/mfrc522,
relay module và cách xếp chân custom chip (kiểu "breakout") lấy từ trình soạn thảo wokwi.com.
Đơn vị: px CSS (1 mm = 3,7795 px). Wokwi xoay linh kiện quanh tâm khung của nó.

Chạy:  python ve_wokwi.py [thư_mục_ra]
"""
import json
import math
import os
import sys

import day_noi as dn

OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/so_do_day/wokwi"
MM = 3.7795275591

# ---------------- Hình học linh kiện (chưa xoay): (rộng, cao, {chân: (x, y)}) ----------------
ESP_PINS = {
    "EN": 24, "VP": 34, "VN": 44, "D34": 53.1, "D35": 62.9, "D32": 72.2, "D33": 81.7, "D25": 91.3,
    "D26": 101, "D27": 110.8, "D14": 120, "D12": 130.4, "D13": 139.5, "GND.2": 149, "VIN": 158.5,
}
ESP_PINS_R = {
    "D23": 24, "D22": 34, "TX0": 44, "RX0": 53.1, "D21": 62.9, "D19": 72.2, "D18": 81.7, "D5": 91.3,
    "TX2": 101, "RX2": 110.8, "D4": 120, "D2": 130.4, "D15": 139.5, "GND.1": 149, "3V3": 158.5,
}
GEO = {
    "wokwi-esp32-devkit-v1": (28.2 * MM, 54.053 * MM,
                              {**{k: (5, v) for k, v in ESP_PINS.items()},
                               **{k: (101.3, v) for k, v in ESP_PINS_R.items()}}),
    "wokwi-gas-sensor": (36.232 * MM, 16.617 * MM,
                         {"AOUT": (137, 16.5), "DOUT": (137, 26.4), "GND": (137, 36.5), "VCC": (137, 46.2)}),
    "wokwi-photoresistor-sensor": (45.95 * MM, 16.267 * MM,
                                   {"VCC": (172, 16), "GND": (172, 26), "DO": (172, 35.8), "AO": (172, 45.5)}),
    "wokwi-pir-motion-sensor": (24 * MM, 24.448 * MM,
                                {"VCC": (36.178, 92), "OUT": (45.9175, 92), "GND": (55.6415, 92)}),
    "wokwi-dht22": (15.1 * MM, 30.885 * MM,
                    {"VCC": (15, 114.9), "SDA": (24.5, 114.9), "NC": (34.1, 114.9), "GND": (43.8, 114.9)}),
    "wokwi-servo": (45 * MM, 31.63 * MM, {"GND": (0, 50), "V+": (0, 59.5), "PWM": (0, 69)}),
    "wokwi-rgb-led": (42.129, 72.582, {"R": (8.5, 44), "COM": (18, 54), "G": (26.4, 44), "B": (35.7, 44)}),
    "wokwi-led": (40, 50, {"A": (15, 42), "C": (25, 42)}),  # attr flip="1": anode trái, cathode phải
    "wokwi-resistor": (15.645 * MM, 3 * MM, {"1": (0, 5.65), "2": (58.8, 5.65)}),
    "wokwi-relay-module": (128.001, 58.239, {"VCC": (0, 19), "GND": (0, 29), "IN": (0, 38.4),
                                             "NC": (114, 20.2), "COM": (114, 30), "NO": (114, 40)}),
    "board-mfrc522": (59.496 * MM, 39.964 * MM,
                      {k: (1.63 * MM, v * MM) for k, v in {
                          "SDA": 10.86, "SCK": 13.4, "MOSI": 15.94, "MISO": 18.48, "IRQ": 21.02,
                          "GND": 23.56, "RST": 26.1, "3.3V": 28.64}.items()}),
}

# ---------------- Custom chip: tên file, tên hiện trên hộp, danh sách chân (chuỗi rỗng = lỗ trống) ----------------
# Kiểu "breakout" của Wokwi: nửa đầu danh sách ở cạnh TRÁI (trên → dưới), nửa sau ở cạnh PHẢI (dưới → lên).
CHIPS = {
    "adapter-5v": ("Adapter DC 5V", ["", "", "+", "-"]),                       # phải: − trên, + dưới
    "acs712": ("ACS712-20A", ["IP+", "IP-", "", "GND", "OUT", "VCC"]),        # trái: IP+, IP−; phải: VCC, OUT, GND
    "mc38": ("Công tắc từ MC-38", ["", "", "2", "1"]),                        # phải: 1 trên, 2 dưới
    "module-coi": ("Module còi (mức THẤP)", ["", "", "", "GND", "I/O", "VCC"]),
    "cam-bien-lua": ("Cảm biến lửa", ["VCC", "GND", "DO", "AO", "", "", "", ""]),  # cả 4 chân cạnh trái
    "quat-5v": ("Quạt hút 5V", ["+", "", "", "-"]),                           # + trái, − phải (cùng hàng)
}
CHIP_CUA = {"adapter-5v": "adapter", "acs712": "acs", "mc38": "cua", "module-coi": "coi",
            "cam-bien-lua": "lua", "quat-5v": "quat"}  # chip → linh kiện trong day_noi


def chip_geo(pins):
    """Như hàm iq/iK/iX/iZ trong trình soạn thảo Wokwi (bố cục breakout, không màn hình)."""
    half = max(math.ceil(len(pins) / 2), 2)
    w, h = 30.0, 2 * 1 + 2.54 * half
    pos = {}
    for i, name in enumerate(pins):
        if not name:
            continue
        x = w - 1.27 if i >= half else 1.27
        y = (h - 1 - 2.54 * (i - half + 1)) if i >= half else (1 + 2.54 * i)
        pos[name] = (x * MM, (y + 1.27) * MM)
    return (w * MM, h * MM, pos)


for _n, (_t, _p) in CHIPS.items():
    GEO["chip-" + _n] = chip_geo(_p)

# ---------------- Bố trí: id → (type, left, top, rotate, attrs) ----------------
XL = 380   # cạnh chân các module cột trái (sau khi xoay, chân hướng sang phải)
XR = 870   # cạnh chân các module cột phải (chân hướng sang trái)
RELAY_TOP = [640 + 75 * k for k in range(4)]

PARTS = {
    "esp": ("wokwi-esp32-devkit-v1", 620, 300, 0, {}),
    # Cột trái
    "adapter": ("chip-adapter-5v", 127.4, 20.4, 0, {}),
    "acs": ("chip-acs712", XL - 108.59, 30, 0, {}),
    "r1": ("wokwi-resistor", 420, 48.18 - 5.65, 0, {"value": "1000"}),
    "r2": ("wokwi-resistor", 500 - 29.59, 60 + 23.9, 90, {"value": "2000"}),
    "mq2": ("wokwi-gas-sensor", XL - 137, 140, 0, {}),
    "cua": ("chip-mc38", XL - 108.59, 225, 0, {}),
    "r3": ("wokwi-resistor", 425 - 0.33, 215 - 5.69, 180, {"value": "1000"}),
    "pir": ("wokwi-pir-motion-sensor", XL - 91.16, 290, 270, {}),
    "ldr": ("wokwi-photoresistor-sensor", XL - 172, 405, 0, {}),
    "rc522": ("board-mfrc522", XL - 218.71, 490, 180, {}),
    "servo": ("wokwi-servo", XL - 170.08, 668, 180, {}),
    "coi": ("chip-module-coi", XL - 108.59, 815, 0, {}),
    # Cột phải
    "rgb1": ("wokwi-rgb-led", XR - 13.35, 190, 90, {"common": "cathode"}),
    "rgb2": ("wokwi-rgb-led", XR - 13.35, 255, 90, {"common": "cathode"}),
    "dht": ("wokwi-dht22", XR + 28.0, 420, 90, {"temperature": "28", "humidity": "65"}),
    "lua": ("chip-cam-bien-lua", XR - 4.8, 535, 0, {}),
    **{f"relay{k + 1}": ("wokwi-relay-module", XR, RELAY_TOP[k], 0, {"transistor": "pnp"}) for k in range(4)},
    # Tải: LED flip → chân A bên trái, C bên phải cùng hàng với NO
    "den_hien": ("wokwi-led", 1010, RELAY_TOP[0] - 2, 0, {"color": "yellow", "flip": "1"}),
    "den_khach": ("wokwi-led", 1010, RELAY_TOP[1] - 2, 0, {"color": "white", "flip": "1"}),
    "den_ngu": ("wokwi-led", 1010, RELAY_TOP[2] - 2, 0, {"color": "orange", "flip": "1"}),
    "quat": ("chip-quat-5v", 1010 - 4.8 + 4, RELAY_TOP[3] + 40 - 8.58, 0, {}),
}

# Nhãn chữ (wokwi-text): (x, y, chữ)
NHAN = [
    (20, -40, "Smarthome — sơ đồ đấu dây (chỉ dây, không có code)"),
    (130, 72, "Adapter 5V → ACS712 (IP+ → IP−)"),
    (420, 20, "Chia áp 1k/2k → IO36"),
    (230, 120, "MQ-2 (AO → IO39)"),
    (230, 205, "Công tắc từ cửa + trở kéo 1k"),
    (200, 275, "PIR HC-SR501 (dây 5V riêng)"),
    (200, 388, "Module quang trở"),
    (160, 476, "RFID RC522 (3V3)"),
    (210, 650, "Servo cửa 360°"),
    (230, 860, "Còi kích mức thấp"),
    (900, 262, "2 module LED RGB (song song)"),
    (930, 430, "DHT22 = DHT11"),
    (990, 540, "Cảm biến lửa (DO → IO18)"),
    (870, 590, "4 relay đơn = module relay 4 kênh (mức THẤP)"),
    (1060, 650, "Đèn hiên"), (1060, 725, "Đèn phòng khách"),
    (1060, 800, "Đèn phòng ngủ"), (1015, 930, "Quạt hút"),
    (100, 1045, "Chân VIN của ESP32 đóng vai jack DC board mở rộng: dây tím = đường nguồn chính qua ACS712"),
]


def pin_xy(pid, pin):
    """Tọa độ tuyệt đối của chân sau khi xoay quanh tâm khung linh kiện."""
    typ, left, top, rot, _ = PARTS[pid]
    w, h, pins = GEO[typ]
    x, y = pins[pin]
    cx, cy = w / 2, h / 2
    a = math.radians(rot)
    dx, dy = x - cx, y - cy
    rx = dx * math.cos(a) - dy * math.sin(a)
    ry = dx * math.sin(a) + dy * math.cos(a)
    return (round(left + cx + rx, 2), round(top + cy + ry, 2))


# ---------------- Đổi tham chiếu day_noi → chân Wokwi ----------------
DOI_CHAN = {
    "mq2": {"AO": "AOUT", "DO": "DOUT"},
    "dht": {"DATA": "SDA"},
    "rgb1": {"-": "COM"}, "rgb2": {"-": "COM"},
    "den_hien": {"+": "A", "-": "C"}, "den_khach": {"+": "A", "-": "C"}, "den_ngu": {"+": "A", "-": "C"},
}
BEN_TRAI = {"adapter", "acs", "r1", "r2", "mq2", "cua", "r3", "pir", "ldr", "rc522", "servo", "coi"}


def wokwi_refs(ref, other):
    """Một đầu dây day_noi → danh sách chân Wokwi (relay:VCC/GND tỏa ra 4 relay)."""
    part, pin = dn.tach(ref)
    if part == "board":
        if pin in ("5V", "JACK+"):
            return ["esp:VIN"]
        if pin == "3V3":
            return ["esp:3V3"]
        # GND: module bên trái về GND.2 (cạnh trái), bên phải về GND.1
        return ["esp:GND.2" if dn.tach(other)[0] in BEN_TRAI else "esp:GND.1"]
    if part == "relay":
        if pin in ("VCC", "GND"):
            return [f"relay{k}:{pin}" for k in range(1, 5)]
        return [f"relay{pin[-1]}:{pin[:-1]}"]
    return [f"{part}:{DOI_CHAN.get(part, {}).get(pin, pin)}"]


# ---------------- Đường dây ----------------
# Làn dọc. Trái: trục GND 392, 5V 402, 3V3 412; làn tín hiệu 590, 582, … ; trục đứng lên chân nguồn 600/608/616.
# Phải: làn tín hiệu 735, 743, …; trục 3V3 825, 5V 835, GND 845.
L_GND, L_5V, L_3V3 = 392, 402, 412
R_3V3, R_5V, R_GND = 825, 835, 845
X_COM = 1006      # làn nối cầu COM 4 relay (ngay ngoài mép phải relay, x = 998)
# Đường nguồn chạy dưới đáy sơ đồ (y): GND trái, 5V trái, nguồn chính, 3V3, 5V phải, GND phải
Y_GND_L, Y_5V_L, Y_TAI, Y_3V3, Y_5V_R, Y_GND_R = 880, 890, 960, 1010, 1020, 1030
X_GND_TAI = 1185  # làn GND của đèn/quạt (bên phải tải và nhãn)
LANE_L = [590 - 8 * i for i in range(10)]
LANE_R = [735 + 8 * i for i in range(10)]

# Tín hiệu trái: làn theo hình chữ V (dây đi xuống: dây trên gần ESP; dây đi lên: dây dưới gần ESP) → không cắt nhau
LANE_TIN_HIEU = {
    "VP": LANE_L[0], "VN": LANE_L[1], "D34": LANE_L[2], "D35": LANE_L[3],
    "D13": LANE_L[0], "D12": LANE_L[1], "D27": LANE_L[2], "D26": LANE_L[3], "D25": LANE_L[4],
    "D33": LANE_L[5], "D32": LANE_L[6],
    "D23": LANE_R[0], "D22": LANE_R[1], "D21": LANE_R[2],
    "D4": LANE_R[0], "RX2": LANE_R[1], "TX2": LANE_R[2], "D5": LANE_R[3], "D18": LANE_R[4], "D19": LANE_R[5],
}


def duong(src, dst, via):
    """Điểm gấp từ chân src tới chân dst: via = [("x", giá trị) | ("y", giá trị)], đoạn cuối Wokwi tự nối."""
    pts = [src]
    x, y = src
    for axis, v in via:
        if axis == "x":
            x = v
        else:
            y = v
        pts.append((x, y))
    pts.append(dst)
    return pts


def chi_dan(pts):
    """Điểm gấp → lệnh h/v của Wokwi (bỏ đoạn cuối: Wokwi tự nối thẳng tới chân đích)."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        if abs(x1 - x0) > 0.01:
            out.append(f"h{round(x1 - x0, 2):g}")
        if abs(y1 - y0) > 0.01:
            out.append(f"v{round(y1 - y0, 2):g}")
    return out


def tuyen(a, b):
    """Chọn nguồn (đầu có tọa độ chắc chắn: ESP32 không xoay) và đường đi cho dây a → b (ref Wokwi)."""
    pa, pina = a.split(":")
    pb, pinb = b.split(":")
    if (pb == "esp" and pa != "esp") or (pa, pb) == ("r2", "r1"):
        a, b, pa, pina, pb, pinb = b, a, pb, pinb, pa, pina
    return a, b, _tuyen(pa, pina, pb, pinb)


def _tuyen(pa, pina, pb, pinb):
    s, d = pin_xy(pa, pina), pin_xy(pb, pinb)
    if pa == "esp":
        pin = pina
        if pin in ("GND.2",):
            if pb == "adapter":   # âm adapter: vòng dưới cột trái, lên trên cùng, vào chân − từ bên phải
                return duong(s, d, [("x", 600), ("y", Y_GND_L), ("x", 110), ("y", 8), ("x", 248), ("y", d[1])])
            if pb == "r2":
                return duong(s, d, [("x", 600), ("y", Y_GND_L), ("x", L_GND), ("y", 132), ("x", d[0])])
            return duong(s, d, [("x", 600), ("y", Y_GND_L), ("x", L_GND), ("y", d[1])])
        if pin == "VIN":
            if (pb, pinb) == ("acs", "IP-"):   # đường nguồn chính IP− → jack board (= VIN)
                return duong(s, d, [("x", 616), ("y", Y_TAI), ("x", 100), ("y", 5), ("x", 255), ("y", d[1])])
            if pb.startswith("relay") and pinb == "COM":   # 5 V cho tải: theo trục 5V, vượt trên relay 1 vào COM1
                return duong(s, d, [("x", 608), ("y", Y_5V_R), ("x", R_5V), ("y", 625), ("x", X_COM), ("y", d[1])])
            if pb.startswith("relay"):
                return duong(s, d, [("x", 608), ("y", Y_5V_R), ("x", R_5V), ("y", d[1])])
            return duong(s, d, [("x", 608), ("y", Y_5V_L), ("x", L_5V), ("y", d[1])])
        if pin == "3V3":
            # 3V3 ở góc dưới phải ESP32: xuống dưới hết các làn tín hiệu rồi mới rẽ
            if pb in BEN_TRAI:
                return duong(s, d, [("x", 728), ("y", Y_3V3), ("x", L_3V3), ("y", d[1])])
            return duong(s, d, [("x", 728), ("y", Y_3V3), ("x", R_3V3), ("y", d[1])])
        if pin == "GND.1":
            if pb in ("den_hien", "den_khach", "den_ngu", "quat"):
                return duong(s, d, [("x", 732), ("y", Y_GND_R), ("x", X_GND_TAI), ("y", d[1])])
            return duong(s, d, [("x", 732), ("y", Y_GND_R), ("x", R_GND), ("y", d[1])])
        # Tín hiệu (cả trở kéo lên r3 đi chung làn với dây cửa)
        return duong(s, d, [("x", LANE_TIN_HIEU[pin]), ("y", d[1])])
    # Dây giữa hai linh kiện
    if pa == "adapter" or pb == "adapter":   # adapter + → ACS IP+: cùng hàng
        return [s, d]
    if {pa, pb} == {"acs", "r1"}:
        return [s, d]
    if (pa, pb) == ("r1", "r2"):          # điểm giữa cầu chia → trở 2k thẳng đứng
        return duong(s, d, [("x", d[0])])
    if pa.startswith("rgb"):                  # rgb2 song song rgb1: đi chung làn của dây rgb1 về ESP
        esp_pin = {"R": "D23", "G": "D22", "B": "D21"}[pina]
        return duong(s, d, [("x", LANE_TIN_HIEU[esp_pin]), ("y", d[1])])
    if pa.startswith("relay") and pina == "COM":   # nối cầu COM
        return duong(s, d, [("x", X_COM), ("y", d[1])])
    if pa.startswith("relay") and pina == "NO":
        return [s, d]
    raise ValueError(f"Chưa có đường cho {pa}:{pina} → {pb}:{pinb}")


def ket_noi():
    """Danh sách [nguồn, đích, màu, chỉ dẫn] + điểm gấp (để kiểm tra/xem trước)."""
    conns, paths, nguon = [], [], []
    for a, b, loai, _ in dn.DAY:
        ra, rb = wokwi_refs(a, b), wokwi_refs(b, a)
        for x in ra:
            for y in rb:
                # rgb2 → rgb1: nguồn là rgb1 (đầu nối về ESP)
                if x.startswith("rgb2") and y.startswith("rgb1"):
                    x, y = y, x
                s_ref, d_ref, pts = tuyen(x, y)
                conns.append([s_ref, d_ref, dn.MAU[loai], chi_dan(pts)])
                paths.append(dict(src=s_ref, dst=d_ref, loai=loai, pts=pts))
                nguon.append((a, b))
    return conns, paths, nguon


def net_of(paths):
    """Gán mỗi dây vào một lưới điện (union-find trên chân) để đếm chỗ cắt giữa các lưới khác nhau."""
    parent = {}

    def f(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in paths:
        parent[f(p["src"])] = f(p["dst"])
    return [f(p["src"]) for p in paths]


def cho_cat(paths):
    """Đếm chỗ hai đoạn dây thuộc hai lưới khác nhau cắt nhau / chồng lên nhau."""
    nets = net_of(paths)
    segs = []
    for i, p in enumerate(paths):
        for (x0, y0), (x1, y1) in zip(p["pts"], p["pts"][1:]):
            segs.append((i, nets[i], min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    cat, chong = [], []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a, b = segs[i], segs[j]
            if a[1] == b[1]:
                continue
            ax0, ay0, ax1, ay1 = a[2:]
            bx0, by0, bx1, by1 = b[2:]
            a_h, b_h = ay0 == ay1, by0 == by1
            if a_h != b_h:   # một ngang một dọc
                h, v = (a, b) if a_h else (b, a)
                if h[2] < v[2] < h[4] and v[3] < h[3] < v[5]:
                    cat.append((round(v[2], 1), round(h[3], 1), frozenset((h[1], v[1]))))
            elif a_h and abs(ay0 - by0) < 3 and min(ax1, bx1) - max(ax0, bx0) > 1:
                chong.append((paths[a[0]]["src"] + "→" + paths[a[0]]["dst"], paths[b[0]]["src"] + "→" + paths[b[0]]["dst"]))
            elif not a_h and not b_h and abs(ax0 - bx0) < 3 and min(ay1, by1) - max(ay0, by0) > 1:
                chong.append((paths[a[0]]["src"] + "→" + paths[a[0]]["dst"], paths[b[0]]["src"] + "→" + paths[b[0]]["dst"]))
    return sorted(set(cat), key=lambda c: (c[1], c[0])), chong


def kiem_tra_wokwi(conns, nguon):
    loi = []
    # Mỗi dây day_noi sinh ít nhất một kết nối
    da_co = set(nguon)
    for a, b, _, _ in dn.DAY:
        if (a, b) not in da_co:
            loi.append(f"Dây {a} → {b} không sinh kết nối")
    # Mọi chân tham chiếu có trong danh sách chân của linh kiện
    for s, d, _, _ in conns:
        for r in (s, d):
            pid, pin = r.split(":")
            if pid not in PARTS:
                loi.append(f"Linh kiện lạ: {r}")
            elif pin not in GEO[PARTS[pid][0]][2]:
                loi.append(f"Chân không có: {r}")
    return loi


def chip_files(out):
    for name, (title, pins) in CHIPS.items():
        with open(os.path.join(out, f"{name}.chip.json"), "w", encoding="utf-8") as f:
            json.dump({"name": title, "author": "Smarthome đồ án", "pins": pins, "controls": []},
                      f, ensure_ascii=False, indent=2)
            f.write("\n")
        with open(os.path.join(out, f"{name}.chip.c"), "w", encoding="utf-8") as f:
            f.write(f"// {title}: chỉ để vẽ sơ đồ đấu dây, không mô phỏng chức năng\n"
                    '#include "wokwi-api.h"\n\nvoid chip_init(void) {}\n')

README = """# Sơ đồ đấu dây Smarthome trên Wokwi

Đây **chỉ là sơ đồ đấu dây** để xem và chụp hình. Dự án **không có code**, nên bấm ▶ Run cũng
không có linh kiện nào hoạt động. Mọi dây sinh tự động từ `bao_cao/_build/day_noi.py`, tức là
cùng một bảng đấu dây với hình chính `../so_do_dau_day.png`, và khớp chân với `esphome/smarthome.yaml`.

`xem_truoc.png` là ảnh xem trước dựng lại ngay trên máy (cùng hình linh kiện của Wokwi), để biết
trước sơ đồ trông thế nào khi mở trên wokwi.com.

## Mở trên wokwi.com

1. Vào https://wokwi.com → **New Project** → chọn **ESP32** (mẫu Arduino nào cũng được).
2. Mở tab **diagram.json**, xóa hết nội dung cũ, dán toàn bộ nội dung file `diagram.json` ở đây.
3. Thêm __SO_CHIP__ linh kiện tự tạo (custom chip). Bấm mũi tên ▾ cạnh các tab file → **New file…**,
   đặt **đúng tên file** như dưới đây rồi dán nội dung tương ứng. Mỗi chip có 2 file `.chip.json` và
   `.chip.c`. Nếu menu có **Upload file(s)…** thì chọn một lần cả 12 file cho nhanh.
__DS_CHIP__
4. Bấm **Save** (cần đăng nhập) để có link chia sẻ. Hộp nào hiện chữ "Missing chip" là do
   thiếu file `.chip.json` hoặc tên file gõ sai.

## Linh kiện nào thay cho linh kiện nào

| Mạch thật | Trên Wokwi | Ghi chú |
|---|---|---|
| Board mở rộng ESP32 30P + jack DC | Chân **VIN** của ESP32 | Wokwi không có board mở rộng và không có nguồn ngoài. Dây tím (adapter → ACS712 IP+ → IP− → VIN) chính là đường nguồn chính vào jack board |
| Hàng chân 5V / 3V3 / GND của board | Chân VIN / 3V3 / GND.1, GND.2 của ESP32 | Các dây cùng lưới đi chung một làn nên trông như một thanh nguồn. Thực tế mỗi dây cắm vào một chân trên hàng nguồn của board |
| DHT11 (module xanh) | DHT22 (`wokwi-dht22`) | Cùng cách nối: VCC, DATA (= chân SDA), GND |
| Module relay 4 kênh kích mức THẤP | 4 relay đơn (`wokwi-relay-module`, `transistor: pnp`) | relay1…4 = IN1…IN4. VCC/GND chung của module được vẽ thành 4 dây. COM nối cầu bên phải như dây cầu trên module thật |
| 2 module LED RGB (có sẵn trở) | 2 `wokwi-rgb-led` cathode chung | Mắc song song: R, G, B của LED phòng ngủ nối vào R, G, B của LED phòng khách |
| Đèn 5 V (hiên, khách, ngủ) | `wokwi-led` | Chỉ để thể hiện tải nối NO → (+), (−) → GND |
| Adapter 5 V, ACS712-20A, công tắc từ MC-38, module còi 3 chân, cảm biến lửa 4 chân, quạt 5 V | Custom chip (hộp xanh) | Wokwi không có các linh kiện này (cảm biến lửa có trong thư viện hình nhưng trình soạn thảo không nhận). Hộp mang **đúng tên chân** của module thật, chip.c để trống |
| Trở 1 kΩ / 2 kΩ (chia áp IO36), 1 kΩ (kéo lên IO34) | `wokwi-resistor` | Đúng giá trị |

PIR dùng **dây 5 V riêng** (từng đi chung dây với relay/servo thì PIR bị kẹt ON). Trên Wokwi
đó vẫn là một dây riêng từ PIR tới VIN, chỉ chạy chồng lên làn đỏ.

## Màu dây (giống hình chính)

__MAU__

## Sinh lại / kiểm tra

```
cd /config/bao_cao/_build
python3 ve_wokwi.py            # kiểm tra day_noi khớp firmware rồi sinh lại thư mục này
python3 xem_truoc_wokwi.py     # ảnh xem trước (cần Python có playwright + chromium)
wokwi-cli lint SmartHome_BaoCao/so_do_day/wokwi   # 0 lỗi; 2 dòng info: esp32-devkit-v1 và mfrc522 là part "undocumented"
```
"""


def readme(out):
    ds = []
    for name, (title, pins) in CHIPS.items():
        chan = ", ".join(dn.LINH_KIEN[CHIP_CUA[name]]["chan"])
        ds.append(f"   - `{name}.chip.json` + `{name}.chip.c` — {title} (chân: {chan})")
    mau = "\n".join(f"- `{dn.MAU[k]}` {ten}: {y}" for k, (ten, y) in dn.CHU_THICH.items())
    text = (README.replace("__SO_CHIP__", str(len(CHIPS))).replace("__DS_CHIP__", "\n".join(ds))
            .replace("__MAU__", mau))
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write(text)



def main():
    loi = dn.kiem_tra()
    if loi:
        for l in loi:
            print("LỖI day_noi:", l)
        sys.exit(1)
    conns, paths, nguon = ket_noi()
    loi = kiem_tra_wokwi(conns, nguon)
    for p in paths:
        (x0, y0), (x1, y1) = p["pts"][-2], p["pts"][-1]
        if abs(x1 - x0) > 0.05 and abs(y1 - y0) > 0.05:
            loi.append(f"Đoạn cuối chéo: {p['src']} → {p['dst']} ({x0},{y0})→({x1},{y1})")
    if loi:
        for l in loi:
            print("LỖI:", l)
        sys.exit(1)
    parts = []
    for pid, (typ, left, top, rot, attrs) in PARTS.items():
        item = {"type": typ, "id": pid, "top": round(top, 2), "left": round(left, 2)}
        if rot:
            item["rotate"] = rot
        item["attrs"] = attrs
        parts.append(item)
    for i, (x, y, text) in enumerate(NHAN):
        parts.append({"type": "wokwi-text", "id": f"nhan{i + 1}", "top": y, "left": x,
                      "attrs": {"text": text, "fontSize": "11" if i else "16"}})
    diagram = {"version": 1, "author": "Smarthome đồ án", "editor": "wokwi",
               "parts": parts, "connections": conns, "dependencies": {}}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "diagram.json"), "w", encoding="utf-8") as f:
        json.dump(diagram, f, ensure_ascii=False, indent=2)
        f.write("\n")
    chip_files(OUT)
    readme(OUT)
    cat, chong = cho_cat(paths)
    print(f"OK — {len(parts)} linh kiện/nhãn, {len(conns)} dây; {len(cat)} chỗ cắt khác lưới, "
          f"{len(chong)} chỗ chồng khác lưới")
    for c in chong:
        print("  CHỒNG:", c)
    return cat, chong


if __name__ == "__main__":
    main()
