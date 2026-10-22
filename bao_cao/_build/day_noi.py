# -*- coding: utf-8 -*-
"""Bảng đấu dây DUY NHẤT của mạch Smarthome (linh kiện, chân, từng sợi dây).

Mọi sơ đồ (ve_so_do_day.py → PNG/SVG, ve_wokwi.py → diagram.json, bảng đấu dây) sinh từ đây.
`kiem_tra()` đọc esphome/smarthome.yaml và báo lỗi nếu GPIO nào trong bảng khác firmware.

Chạy:  python day_noi.py      (chỉ kiểm tra, in "OK" khi khớp)
"""
import re
import sys

import yaml

YAML = "/config/esphome/smarthome.yaml"

# ---------------- ESP32 DevKit V1 30 chân (chữ in trên board, trên → dưới, cổng USB ở dưới) ----------------
ESP_TRAI = ["EN", "VP", "VN", "D34", "D35", "D32", "D33", "D25", "D26", "D27", "D14", "D12", "D13", "GND", "VIN"]
ESP_PHAI = ["D23", "D22", "TX0", "RX0", "D21", "D19", "D18", "D5", "TX2", "RX2", "D4", "D2", "D15", "GND", "3V3"]
GPIO = {  # chữ in → số GPIO
    "VP": 36, "VN": 39, "D34": 34, "D35": 35, "D32": 32, "D33": 33, "D25": 25, "D26": 26, "D27": 27,
    "D14": 14, "D12": 12, "D13": 13, "D23": 23, "D22": 22, "TX0": 1, "RX0": 3, "D21": 21, "D19": 19,
    "D18": 18, "D5": 5, "TX2": 17, "RX2": 16, "D4": 4, "D2": 2, "D15": 15,
}

# ---------------- Linh kiện: id → tên, chân theo đúng thứ tự trên module, nguồn nuôi ----------------
# "trong" = chân để trống (không nối). Thứ tự chân là loại module phổ biến; tên chân luôn ghi trên hình.
LINH_KIEN = {
    "esp": dict(ten="ESP32 DevKit V1 (DOIT, 30 chân)", chan=ESP_TRAI + ESP_PHAI),
    "board": dict(ten="Board mở rộng ESP32 30P", chan=["JACK+", "JACK-", "5V", "3V3", "GND"],
                  ghi_chu="ESP32 cắm trên board; board cấp VIN/GND cho ESP32 và ra hàng chân 5V, 3V3, GND"),
    "adapter": dict(ten="Adapter DC 5 V", chan=["+", "-"]),
    "acs": dict(ten="ACS712-20A (100 mV/A)", chan=["VCC", "OUT", "GND", "IP+", "IP-"], nguon="5V"),
    "r1": dict(ten="Trở 1 kΩ (chia áp ACS712)", chan=["1", "2"]),
    "r2": dict(ten="Trở 2 kΩ (chia áp ACS712)", chan=["1", "2"]),
    "mq2": dict(ten="MQ-2 (khí gas)", chan=["VCC", "GND", "DO", "AO"], nguon="5V", trong=["DO"]),
    "cua": dict(ten="Công tắc từ cửa (MC-38)", chan=["1", "2"]),
    "r3": dict(ten="Trở 1 kΩ (kéo lên IO34)", chan=["1", "2"]),
    "pir": dict(ten="PIR HC-SR501", chan=["VCC", "OUT", "GND"], nguon="5V"),
    "ldr": dict(ten="Module quang trở", chan=["VCC", "GND", "DO", "AO"], nguon="3V3", trong=["DO"]),
    "rc522": dict(ten="RFID RC522", chan=["SDA", "SCK", "MOSI", "MISO", "IRQ", "GND", "RST", "3.3V"],
                  nguon="3V3", trong=["IRQ"]),
    "servo": dict(ten="Servo cửa 360°", chan=["GND", "V+", "PWM"], nguon="5V",
                  ghi_chu="Dây nâu GND · đỏ 5 V · cam tín hiệu"),
    "coi": dict(ten="Module còi (kích mức THẤP)", chan=["VCC", "I/O", "GND"], nguon="5V"),
    "rgb1": dict(ten="Module LED RGB (phòng khách)", chan=["R", "G", "B", "-"]),
    "rgb2": dict(ten="Module LED RGB (phòng ngủ)", chan=["R", "G", "B", "-"]),
    "dht": dict(ten="DHT11 (module xanh)", chan=["VCC", "DATA", "GND"], nguon="3V3"),
    "lua": dict(ten="Cảm biến lửa", chan=["VCC", "GND", "DO", "AO"], nguon="3V3", trong=["AO"]),
    "relay": dict(ten="Module relay 4 kênh (kích mức THẤP)",
                  chan=["GND", "IN1", "IN2", "IN3", "IN4", "VCC",
                        "NO1", "COM1", "NC1", "NO2", "COM2", "NC2", "NO3", "COM3", "NC3", "NO4", "COM4", "NC4"],
                  nguon="5V", trong=["NC1", "NC2", "NC3", "NC4"]),
    "den_hien": dict(ten="Đèn hiên 5 V", chan=["+", "-"]),
    "den_khach": dict(ten="Đèn phòng khách 5 V", chan=["+", "-"]),
    "den_ngu": dict(ten="Đèn phòng ngủ 5 V", chan=["+", "-"]),
    "quat": dict(ten="Quạt hút phòng ngủ 5 V", chan=["+", "-"]),
}

# ---------------- Loại dây → màu (dùng chung cho mọi hình) ----------------
MAU = {
    "tai": "#7B3FA0",    # đường dòng tải: adapter → ACS712 → jack board (tím, dây to)
    "5v": "#D62728",
    "3v3": "#F28C28",
    "gnd": "#222222",
    "analog": "#1F9E89",  # VP/VN/D32 (ADC1)
    "vao": "#2A7AB8",     # ngõ vào số: cửa, PIR, lửa, DHT
    "spi": "#2CA02C",     # RC522
    "pwm": "#B8860B",     # servo, còi
    "rgb_r": "#E8453C", "rgb_g": "#34A853", "rgb_b": "#4169E1",
    "relay": "#8C564B",
    "tai_relay": "#D62728",  # 5 V qua COM/NO tới tải
}
# Tên màu + ý nghĩa cho chú thích hình và bảng đấu dây
CHU_THICH = {
    "tai": ("tím, dây to", "Đường nguồn chính qua ACS712"),
    "5v": ("đỏ", "5 V"),
    "3v3": ("cam", "3V3"),
    "gnd": ("đen", "GND"),
    "analog": ("xanh ngọc", "Tín hiệu analog (ADC1)"),
    "vao": ("xanh dương", "Ngõ vào số"),
    "spi": ("xanh lá", "SPI RC522"),
    "pwm": ("vàng đồng", "Servo, còi"),
    "rgb_r": ("đỏ", "LED RGB kênh R"),
    "rgb_g": ("xanh lá", "LED RGB kênh G"),
    "rgb_b": ("xanh dương", "LED RGB kênh B"),
    "relay": ("nâu", "Điều khiển relay"),
    "tai_relay": ("đỏ, dây to", "5 V cấp cho tải qua relay"),
}

# ---------------- Từng sợi dây: (từ, tới, loại, ghi chú) ----------------
# "board:5V"/"board:3V3"/"board:GND" = hàng chân nguồn trên board mở rộng (cắm chung nhiều dây).
DAY = [
    # Đường nguồn chính: dòng mọi tải (kể cả ESP32) chạy qua ACS712
    ("adapter:+", "acs:IP+", "tai", "Dây nguồn chính, nối vít IP+"),
    ("acs:IP-", "board:JACK+", "tai", "Ra vít IP− vào jack DC (+) board mở rộng"),
    ("adapter:-", "board:JACK-", "gnd", "Âm adapter vào jack DC (−)"),
    # ACS712: cầu chia 1k/2k → IO36 nhận 2/3 điện áp OUT (OUT tối đa 5 V → 3,33 V)
    ("acs:VCC", "board:5V", "5v", ""),
    ("acs:GND", "board:GND", "gnd", ""),
    ("acs:OUT", "r1:1", "analog", "OUT qua trở 1 kΩ"),
    ("r1:2", "esp:VP", "analog", "IO36 (ADC1) — điểm giữa cầu chia"),
    ("r2:1", "r1:2", "analog", "Trở 2 kΩ từ điểm giữa xuống GND"),
    ("r2:2", "board:GND", "gnd", ""),
    # MQ-2: AO thẳng vào IO39, DO bỏ trống
    ("mq2:VCC", "board:5V", "5v", "Nuôi 5 V (sợi đốt)"),
    ("mq2:GND", "board:GND", "gnd", ""),
    ("mq2:AO", "esp:VN", "analog", "IO39 (ADC1); DO bỏ trống"),
    # Công tắc từ cửa: kéo lên 1k → 3V3, đóng (có nam châm) = nối GND = LOW
    ("cua:1", "esp:D34", "vao", "IO34 (chỉ vào, không có pull-up nội)"),
    ("cua:2", "board:GND", "gnd", ""),
    ("r3:1", "esp:D34", "vao", "Trở kéo lên 1 kΩ"),
    ("r3:2", "board:3V3", "3v3", ""),
    # PIR: dây 5 V RIÊNG (dùng chung dây với relay/servo làm PIR kẹt ON — 18/10)
    ("pir:VCC", "board:5V", "5v", "Dây 5 V riêng, không đi chung dây relay/servo"),
    ("pir:OUT", "esp:D35", "vao", "IO35 (chỉ vào)"),
    ("pir:GND", "board:GND", "gnd", ""),
    # Quang trở: nuôi 3V3 để AO không vượt 3,3 V
    ("ldr:VCC", "board:3V3", "3v3", ""),
    ("ldr:GND", "board:GND", "gnd", ""),
    ("ldr:AO", "esp:D32", "analog", "IO32 (ADC1); DO bỏ trống"),
    # RC522 (SPI): nuôi 3V3, RST nối thẳng 3V3, IRQ bỏ trống
    ("rc522:MISO", "esp:D33", "spi", "IO33"),
    ("rc522:SCK", "esp:D25", "spi", "IO25"),
    ("rc522:MOSI", "esp:D26", "spi", "IO26"),
    ("rc522:SDA", "esp:D27", "spi", "IO27 (CS)"),
    ("rc522:RST", "board:3V3", "3v3", "RST nối thẳng 3V3"),
    ("rc522:3.3V", "board:3V3", "3v3", "Chỉ cấp 3V3"),
    ("rc522:GND", "board:GND", "gnd", ""),
    # Servo cửa 360°: nuôi 5 V, tín hiệu IO12 (chân strapping — rút khi nạp lần đầu)
    ("servo:PWM", "esp:D12", "pwm", "IO12 — rút dây này khi nạp USB lần đầu"),
    ("servo:V+", "board:5V", "5v", ""),
    ("servo:GND", "board:GND", "gnd", ""),
    # Còi: kêu khi IO13 = LOW
    ("coi:I/O", "esp:D13", "pwm", "IO13, kích mức thấp"),
    ("coi:VCC", "board:5V", "5v", ""),
    ("coi:GND", "board:GND", "gnd", ""),
    # 2 module RGB chung 3 chân màu (mắc song song)
    ("rgb1:R", "esp:D23", "rgb_r", "IO23"),
    ("rgb1:G", "esp:D22", "rgb_g", "IO22"),
    ("rgb1:B", "esp:D21", "rgb_b", "IO21"),
    ("rgb1:-", "board:GND", "gnd", "Cathode chung"),
    ("rgb2:R", "rgb1:R", "rgb_r", "Song song với RGB phòng khách"),
    ("rgb2:G", "rgb1:G", "rgb_g", ""),
    ("rgb2:B", "rgb1:B", "rgb_b", ""),
    ("rgb2:-", "board:GND", "gnd", ""),
    # DHT11
    ("dht:VCC", "board:3V3", "3v3", ""),
    ("dht:DATA", "esp:D19", "vao", "IO19 (module có sẵn trở kéo lên)"),
    ("dht:GND", "board:GND", "gnd", ""),
    # Cảm biến lửa: nuôi 3V3, DO = LOW khi có lửa
    ("lua:VCC", "board:3V3", "3v3", ""),
    ("lua:GND", "board:GND", "gnd", ""),
    ("lua:DO", "esp:D18", "vao", "IO18, LOW = có lửa; AO bỏ trống"),
    # Relay 4 kênh kích mức thấp
    ("relay:IN1", "esp:D5", "relay", "IO5 — đèn hiên"),
    ("relay:IN2", "esp:TX2", "relay", "IO17 — đèn phòng khách"),
    ("relay:IN3", "esp:RX2", "relay", "IO16 — đèn phòng ngủ"),
    ("relay:IN4", "esp:D4", "relay", "IO4 — quạt hút"),
    ("relay:VCC", "board:5V", "5v", ""),
    ("relay:GND", "board:GND", "gnd", ""),
    # Tải 5 V: bus 5 V → COM (nối cầu 4 kênh), NO → tải (+), tải (−) → GND
    ("relay:COM1", "board:5V", "tai_relay", "5 V cho tải vào COM1"),
    ("relay:COM2", "relay:COM1", "tai_relay", "Nối cầu COM"),
    ("relay:COM3", "relay:COM2", "tai_relay", "Nối cầu COM"),
    ("relay:COM4", "relay:COM3", "tai_relay", "Nối cầu COM"),
    ("relay:NO1", "den_hien:+", "tai_relay", ""),
    ("relay:NO2", "den_khach:+", "tai_relay", ""),
    ("relay:NO3", "den_ngu:+", "tai_relay", ""),
    ("relay:NO4", "quat:+", "tai_relay", ""),
    ("den_hien:-", "board:GND", "gnd", ""),
    ("den_khach:-", "board:GND", "gnd", ""),
    ("den_ngu:-", "board:GND", "gnd", ""),
    ("quat:-", "board:GND", "gnd", ""),
]

# Chân ESP32 → khối trong firmware khai báo chân đó (id, hoặc platform nếu không có id, hoặc "spi.clk_pin")
FIRMWARE = {
    "VP": "acs_v", "VN": "gas_ao", "D34": "door_contact", "D35": "motion", "D32": "light_pct",
    "D33": "spi.miso_pin", "D25": "spi.clk_pin", "D26": "spi.mosi_pin", "D27": "rc522_spi.cs_pin",
    "D12": "servo_pwm", "D13": "buzzer", "D23": "pwm_r", "D22": "pwm_g", "D21": "pwm_b",
    "D19": "dht", "D18": "fire", "D5": "relay_porch", "TX2": "relay_living", "RX2": "relay_bed",
    "D4": "relay_fan",
}


def tach(ref):
    """'esp:D34' → ('esp', 'D34')"""
    part, _, pin = ref.partition(":")
    return part, pin


def chan_esp_dung():
    """Các chân ESP32 có dây nối (chữ in)."""
    return sorted({tach(r)[1] for d in DAY for r in d[:2] if tach(r)[0] == "esp"},
                  key=lambda p: (ESP_TRAI + ESP_PHAI).index(p))


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_multi_constructor("!", lambda loader, suffix, node: None)


def gpio_firmware(path=YAML):
    """{khóa: số GPIO} cho mọi chân khai báo trong firmware."""
    with open(path, encoding="utf-8") as f:
        cfg = yaml.load(f, Loader=_Loader)
    out = {}

    def so(v):
        if isinstance(v, dict):
            v = v.get("number")
        m = re.fullmatch(r"GPIO(\d+)", str(v or ""))
        return int(m.group(1)) if m else None

    def walk(node):
        if isinstance(node, dict):
            if "pin" in node and so(node["pin"]) is not None:
                out[node.get("id") or node.get("platform")] = so(node["pin"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(cfg)
    for blk, keys in (("spi", ("clk_pin", "mosi_pin", "miso_pin")), ("rc522_spi", ("cs_pin",))):
        b = cfg.get(blk)
        b = b[0] if isinstance(b, list) else b
        for k in keys:
            if b and so(b.get(k)) is not None:
                out[f"{blk}.{k}"] = so(b[k])
    return out


def kiem_tra(path=YAML):
    """Trả về danh sách lỗi (rỗng = sơ đồ khớp firmware)."""
    loi = []
    fw = gpio_firmware(path)
    # 1. Dây hợp lệ: linh kiện và chân có thật, chân "trống" không bị nối
    for a, b, loai, _ in DAY:
        if loai not in MAU:
            loi.append(f"Loại dây lạ: {loai}")
        for r in (a, b):
            p, c = tach(r)
            if p not in LINH_KIEN or c not in LINH_KIEN[p]["chan"]:
                loi.append(f"Chân không tồn tại: {r}")
            elif c in LINH_KIEN[p].get("trong", []):
                loi.append(f"Chân để trống mà có dây: {r}")
    # 2. Mỗi chân ESP32 có dây phải khớp GPIO trong firmware
    dung = chan_esp_dung()
    for chan in dung:
        khoa = FIRMWARE.get(chan)
        if khoa is None:
            loi.append(f"esp:{chan} có dây nhưng chưa khai báo khối firmware tương ứng")
        elif khoa not in fw:
            loi.append(f"Firmware không còn khối '{khoa}' (chân {chan})")
        elif fw[khoa] != GPIO[chan]:
            loi.append(f"{khoa}: firmware GPIO{fw[khoa]} ≠ sơ đồ {chan} (GPIO{GPIO[chan]})")
    # 3. Mọi GPIO firmware dùng đều có dây trên sơ đồ
    co_day = {GPIO[c] for c in dung}
    for khoa, g in fw.items():
        if g not in co_day:
            loi.append(f"Firmware dùng GPIO{g} ({khoa}) nhưng sơ đồ không có dây")
    return loi


if __name__ == "__main__":
    loi = kiem_tra()
    for l in loi:
        print("LỖI:", l)
    if loi:
        sys.exit(1)
    print(f"OK — {len(DAY)} dây, {len(chan_esp_dung())} chân ESP32 khớp esphome/smarthome.yaml")
