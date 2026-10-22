"""Sơ đồ chân ESP32 DevKit V1 (30 chân) cho mô hình — nguồn dữ liệu chân DUY NHẤT cho:
  • /config/www/smarthome/esp32_pinout.svg  (hình chân, tô màu theo thiết bị)
  • bảng đấu dây trên trang "Đấu dây" và số chân trong tiêu đề thiết bị (build_dashboard.py import)
Phải khớp với /config/esphome/smarthome.yaml.
"""
import hashlib
import os

C_IN, C_OUT, C_SPI, C_PWR, C_GND, C_33, C_NONE = (
    "#0a8fc2", "#c2187a", "#7b4fd0", "#d62828", "#1a1a1a", "#f08c00", "#b8b2aa")

# Hàng chân của DOIT ESP32 DevKit V1 30 chân, nhìn từ mặt có linh kiện, ăng-ten ở trên, cổng USB ở dưới
LEFT = ["EN", "VP", "VN", "D34", "D35", "D32", "D33", "D25", "D26", "D27", "D14", "D12", "GND", "D13", "VIN"]
RIGHT = ["D23", "D22", "TX0", "RX0", "D21", "D19", "D18", "D5", "TX2", "RX2", "D4", "D2", "D15", "GND", "3V3"]
GPIO = {"VP": 36, "VN": 39, "TX0": 1, "RX0": 3, "TX2": 17, "RX2": 16}

# Chân → (nối tới, màu, ghi chú ngắn)
PINS = {
    "EN": ("—", C_NONE, "nút reset"),
    "VP": ("ACS712 OUT", C_IN, "qua cầu chia 10k/20k"),
    "VN": ("MQ-2 AO", C_IN, "khí gas"),
    "D34": ("LDR AO", C_IN, "ánh sáng"),
    "D35": ("KY-026 AO", C_IN, "cảm biến lửa"),
    "D32": ("Servo SG90", C_OUT, "dây cam"),
    "D33": ("PIR OUT", C_IN, ""),
    "D25": ("Relay K1", C_OUT, "LED dây phòng khách"),
    "D26": ("DHT11 DATA", C_IN, ""),
    "D27": ("Relay K2", C_OUT, "quạt"),
    "D14": ("MC-38 cửa", C_IN, "dây còn lại → GND"),
    "D12": ("Relay K3", C_OUT, "đèn ngủ · chân strapping"),
    "GND": ("GND chung", C_GND, ""),
    "D13": ("—", C_NONE, "dự phòng"),
    "VIN": ("5V thanh nguồn", C_PWR, "nuôi ESP32"),
    "D23": ("RC522 MOSI", C_SPI, ""),
    "D22": ("—", C_NONE, "dự phòng"),
    "TX0": ("—", C_NONE, "để trống (USB)"),
    "RX0": ("—", C_NONE, "để trống (USB)"),
    "D21": ("RC522 RST", C_SPI, ""),
    "D19": ("RC522 MISO", C_SPI, ""),
    "D18": ("RC522 SCK", C_SPI, ""),
    "D5": ("RC522 SDA", C_SPI, "chân strapping"),
    "TX2": ("Relay K5", C_OUT, "đèn hiên"),
    "RX2": ("Relay K4", C_OUT, "đèn bếp"),
    "D4": ("Còi", C_OUT, ""),
    "D2": ("—", C_NONE, "dự phòng · LED trên board"),
    "D15": ("—", C_NONE, "dự phòng"),
    "3V3": ("3.3V ra", C_33, "RC522 · DHT11 · KY-026 · LDR"),
}

# Bảng đấu dây theo thiết bị (Markdown)
WIRING = [
    # (thiết bị, chân tín hiệu → ESP32, nguồn, lưu ý) — theo repo esp32-smarthome-gateway, còi ở D4
    ("RFID RC522", "SDA→**D5** · SCK→**D18** · MOSI→**D23** · MISO→**D19** · RST→**D21** · IRQ để trống",
     "**3.3V** · GND", "⚠ Không cấp 5V"),
    ("Servo SG90", "Dây cam→**D32**", "Đỏ **5V** thanh nguồn · Nâu GND", "Không lấy 5V từ chân ESP32"),
    ("Còi", "I/O→**D4**", "**5V** · GND", "Còi rời: kích qua S8050"),
    ("DHT11", "DATA→**D26**", "**3.3V** · GND", "Module có sẵn trở kéo lên"),
    ("PIR SR501", "OUT→**D33**", "**5V** · GND", ""),
    ("MC-38 (cửa)", "Dây 1→**D14** · dây 2→GND", "—", "Dùng trở kéo lên trong chip, không cần trở ngoài"),
    ("KY-026 (lửa)", "**AO**→**D35** · DO để trống", "**3.3V** · GND", "Đọc analog như repo"),
    ("MQ-2 (khí gas)", "**AO**→**VN** (GPIO39) · DO để trống", "**5V** · GND",
     "Nuôi 5V thì AO có thể > 3.3V → nên chia áp 10k/20k; cần sấy nóng vài phút"),
    ("LDR (module)", "**AO**→**D34** · DO để trống", "**3.3V** · GND", "Trời tối → điện áp cao"),
    ("ACS712", "OUT→10 kΩ→**VP**; VP→20 kΩ→GND", "**5V lấy trước IP+** · GND",
     "IP+ ← adapter, IP− → thanh 5V"),
    ("Relay 4 kênh", "IN1→**D25** (LED dây) · IN2→**D27** (quạt) · IN3→**D12** (đèn ngủ) · IN4→**RX2** (đèn bếp)",
     "VCC **5V** · GND", "Loại **kích mức cao** (như config.h của repo)"),
    ("Relay 2 kênh", "IN1→**TX2** (đèn hiên) · IN2 để trống (dự phòng)", "VCC **5V** · GND", "Kích mức cao"),
    ("Tải qua relay", "COM←**5V** thanh nguồn · NO→(+) tải", "(−) tải → GND",
     "LED dây, quạt, đèn ngủ, đèn bếp, đèn hiên"),
    ("ESP32", "—", "VIN ← **5V** · GND ← GND", "Nạp code qua USB vẫn để adapter cắm được"),
]

# Số chân hiển thị trong tiêu đề thiết bị trên mặt bằng
TITLE_PINS = {
    "servo": "D32", "buzzer": "D4", "pir": "D33", "bedroom": "Relay K3 · D12",
    "strip": "Relay K1 · D25", "fan": "Relay K2 · D27", "kitchen": "Relay K4 · RX2", "porch": "Relay K5 · TX2",
    "rfid": "SPI · D5·18·19·23·21", "ldr": "D34", "flame": "D35", "gas": "VN", "mc38": "D14", "dht": "D26",
    "acs": "VP",
}


def pin_label(p):
    return f"{p} · GPIO{GPIO[p]}" if p in GPIO else p


def svg():
    W, H, TOP, STEP = 980, 700, 92, 34
    bx, bw = 400, 180
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           'font-family="Inter, Roboto, Arial, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#fbfaf8"/>',
           f'<rect x="{bx}" y="40" width="{bw}" height="{TOP + STEP * 15 - 10}" rx="10" fill="#1f2a36"/>',
           f'<rect x="{bx + 40}" y="52" width="{bw - 80}" height="70" rx="4" fill="#9aa5b1"/>',  # vỏ module WROOM
           f'<text x="{bx + bw / 2}" y="92" font-size="13" font-weight="700" fill="#1f2a36" text-anchor="middle">ESP32</text>',
           f'<text x="{bx + bw / 2}" y="108" font-size="9" fill="#1f2a36" text-anchor="middle">WROOM-32</text>',
           f'<rect x="{bx + bw / 2 - 22}" y="{TOP + STEP * 15 - 34}" width="44" height="26" rx="3" fill="#c9ced4"/>',  # USB
           f'<text x="{bx + bw / 2}" y="{TOP + STEP * 15 - 17}" font-size="9" fill="#1f2a36" text-anchor="middle">USB</text>',
           f'<text x="{W / 2}" y="26" font-size="16" font-weight="700" fill="#2f2925" text-anchor="middle">'
           'Sơ đồ đấu dây ESP32 DevKit V1 — Smarthome đồ án</text>']
    for side, names in (("L", LEFT), ("R", RIGHT)):
        for i, p in enumerate(names):
            y = TOP + 40 + i * STEP
            px = bx + 14 if side == "L" else bx + bw - 14
            dev, color, note = PINS[p]
            used = color != C_NONE
            out.append(f'<circle cx="{px}" cy="{y}" r="6" fill="#d4af37" stroke="#7a6420"/>')
            tx = px + 12 if side == "L" else px - 12
            out.append(f'<text x="{tx}" y="{y + 4}" font-size="10.5" fill="#e8edf2" '
                       f'text-anchor="{"start" if side == "L" else "end"}">{pin_label(p)}</text>')
            # dây dẫn + nhãn thiết bị
            lx2 = bx - 30 if side == "L" else bx + bw + 30
            out.append(f'<line x1="{px}" y1="{y}" x2="{lx2}" y2="{y}" stroke="{color}" stroke-width="{3 if used else 1.5}"'
                       f'{"" if used else " stroke-dasharray=\"3 3\""}/>')
            bw2 = 270
            rx = lx2 - bw2 if side == "L" else lx2
            out.append(f'<rect x="{rx}" y="{y - 13}" width="{bw2}" height="26" rx="6" '
                       f'fill="{"#ffffff" if used else "#f1efeb"}" stroke="{color}" stroke-width="{1.6 if used else 1}"/>')
            tx = rx + 10
            out.append(f'<text x="{tx}" y="{y + 4.5}" font-size="12" font-weight="700" '
                       f'fill="{"#2f2925" if used else "#9a948c"}">{dev}'
                       f'<tspan dx="8" font-size="10.5" font-weight="400" fill="#6b6259">{note}</tspan></text>')
    legend = [(C_IN, "Tín hiệu vào"), (C_OUT, "Điều khiển ra"), (C_SPI, "SPI (RFID)"), (C_PWR, "5V"), (C_33, "3.3V"),
              (C_GND, "GND"), (C_NONE, "Không dùng")]
    for i, (c, t) in enumerate(legend):
        x = 70 + i * 125
        out.append(f'<line x1="{x}" y1="{H - 22}" x2="{x + 24}" y2="{H - 22}" stroke="{c}" stroke-width="4"/>'
                   f'<text x="{x + 30}" y="{H - 18}" font-size="12" fill="#2f2925">{t}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write():
    text = svg()
    os.makedirs("/config/www/smarthome", exist_ok=True)
    open("/config/www/smarthome/esp32_pinout.svg", "w", encoding="utf-8").write(text)
    return hashlib.md5(text.encode()).hexdigest()[:8]


def wiring_markdown():
    rows = ["| Thiết bị | Tín hiệu → chân ESP32 | Nguồn | Lưu ý |", "|:--|:--|:--|:--|"]
    rows += [f"| **{d}** | {s} | {p} | {n} |" for d, s, p, n in WIRING]
    return "\n".join(rows)


if __name__ == "__main__":
    print(write())
