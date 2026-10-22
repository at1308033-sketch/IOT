# -*- coding: utf-8 -*-
"""Sinh bảng đấu dây từng sợi (Markdown) từ day_noi.py để dán vào báo cáo.

Mỗi sợi trong day_noi.DAY xuất hiện đúng một lần, đánh số liên tục theo thứ tự các bảng
(nguồn → cảm biến → RFID → chấp hành → tải). Chạy kiem_tra() trước, lệch firmware thì dừng.

Chạy:  python ve_bang_dau_day.py [file_ra]   (mặc định /config/SmartHome_BaoCao/so_do_day/bang_dau_day.md)
"""
import os
import sys

import day_noi as dn

OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/so_do_day/bang_dau_day.md"

# Tên ngắn dùng trong ô bảng
TEN = {
    "adapter": "Adapter 5 V", "acs": "ACS712", "r1": "Trở R1 1 kΩ", "r2": "Trở R2 2 kΩ",
    "mq2": "MQ-2", "cua": "Công tắc từ", "r3": "Trở R3 1 kΩ", "pir": "PIR", "ldr": "Quang trở",
    "rc522": "RC522", "servo": "Servo", "coi": "Module còi", "rgb1": "RGB khách", "rgb2": "RGB ngủ",
    "dht": "DHT11", "lua": "Cảm biến lửa", "relay": "Relay 4 kênh",
    "den_hien": "Đèn hiên", "den_khach": "Đèn phòng khách", "den_ngu": "Đèn phòng ngủ", "quat": "Quạt hút",
}
TAI = ("den_hien", "den_khach", "den_ngu", "quat")

# Các bảng theo thứ tự trong tài liệu: (tiêu đề, linh kiện thuộc bảng)
NHOM = [
    ("Nguồn chính và ACS712 (cầu chia áp R1/R2)", ("adapter", "acs", "r1", "r2")),
    ("Cảm biến khí gas MQ-2", ("mq2",)),
    ("Công tắc từ cửa (trở kéo lên R3)", ("cua", "r3")),
    ("Cảm biến chuyển động PIR HC-SR501", ("pir",)),
    ("Module quang trở", ("ldr",)),
    ("DHT11", ("dht",)),
    ("Cảm biến lửa", ("lua",)),
    ("RFID RC522 (SPI)", ("rc522",)),
    ("Servo cửa 360°", ("servo",)),
    ("Module còi", ("coi",)),
    ("2 module LED RGB (mắc song song)", ("rgb1", "rgb2")),
    ("Module relay 4 kênh — phía điều khiển", ("relay",)),
    ("Tải 5 V qua relay (COM → NO → tải)", TAI),
]


def nhom_cua(day):
    """Bảng chứa sợi dây: dây có đầu ở tải → bảng tải; còn lại theo đầu thứ nhất."""
    parts = [dn.tach(r)[0] for r in day[:2]]
    if any(p in TAI for p in parts):
        return len(NHOM) - 1
    for i, (_, ds) in enumerate(NHOM):
        if parts[0] in ds:
            return i
    raise ValueError(f"Dây không thuộc bảng nào: {day}")


def chu_chan(pin):
    return pin.replace("-", "−")


def dau(ref):
    """'esp:D34' → 'ESP32 · D34 (GPIO34)'"""
    p, c = dn.tach(ref)
    if p == "esp":
        return f"ESP32 · {c} (GPIO{dn.GPIO[c]})" if c in dn.GPIO else f"ESP32 · {c}"
    if p == "board":
        if c.startswith("JACK"):
            return f"Board mở rộng · jack DC ({'+' if c.endswith('+') else '−'})"
        return f"Board mở rộng · hàng chân {c}"
    if p == "cua":
        return f"{TEN[p]} · dây {c}"
    if p in ("r1", "r2", "r3"):
        return f"{TEN[p]} · chân {c}"
    return f"{TEN[p]} · {chu_chan(c)}"


def bang_nguon():
    """{nguồn: [linh kiện]} — module nào nuôi từ hàng chân nào (không tính dây tải qua relay)."""
    out = {"5V": [], "3V3": []}
    for a, b, loai, _ in dn.DAY:
        if loai not in ("5v", "3v3"):
            continue
        for x, y in ((a, b), (b, a)):
            px, _ = dn.tach(x)
            py, cy = dn.tach(y)
            if py == "board" and cy in out and px not in out[cy]:
                out[cy].append(px)
    return out


def main():
    loi = dn.kiem_tra()
    if loi:
        for l in loi:
            print("LỖI:", l)
        sys.exit("Sơ đồ lệch firmware — sửa day_noi.py trước khi sinh bảng.")

    theo_nhom = [[] for _ in NHOM]
    for d in dn.DAY:
        theo_nhom[nhom_cua(d)].append(d)

    md = [
        "# Bảng đấu dây mạch Smarthome",
        "",
        "Bảng liệt kê **từng sợi dây** của mạch ESP32 DevKit V1 (30 chân) cắm trên board mở rộng, "
        "khớp với firmware `esphome/smarthome.yaml` (đã kiểm tra tự động khi sinh bảng). "
        "Đọc cùng hình *Sơ đồ đấu dây*: tên chân và màu dây giống nhau.",
        "",
        "- Tên chân ESP32 ghi theo **chữ in trên board** (VP, VN, D34, TX2…), trong ngoặc là số GPIO.",
        "- \"Board mở rộng · hàng chân 5V/3V3/GND\" là các hàng chân nguồn trên board mở rộng, "
        "nhiều dây cắm chung một hàng.",
        "- Màu dây là **quy ước trên sơ đồ**, không bắt buộc trùng màu dây thật.",
        "",
        "**Quy ước màu dây**",
        "",
        "| Màu | Ý nghĩa | Mã màu trên hình |",
        "|---|---|---|",
    ]
    for loai, (mau, y_nghia) in dn.CHU_THICH.items():
        md.append(f"| {mau} | {y_nghia} | `{dn.MAU[loai]}` |")

    so = 0
    for (tieu_de, ds), days in zip(NHOM, theo_nhom):
        md += ["", f"## {tieu_de}", "", "| # | Từ (module · chân) | Tới (module · chân) | Màu dây | Ghi chú |",
               "|---:|---|---|---|---|"]
        for a, b, loai, ghi_chu in days:
            so += 1
            md.append(f"| {so} | {dau(a)} | {dau(b)} | {dn.CHU_THICH[loai][0]} | {ghi_chu} |")
        if "servo" in ds:
            md += ["", f"Dây servo: {dn.LINH_KIEN['servo']['ghi_chu']}."]
    assert so == len(dn.DAY), (so, len(dn.DAY))

    # Chân để trống
    md += ["", "## Chân để trống (không nối)", "", "| Linh kiện | Chân | Ghi chú |", "|---|---|---|"]
    for p, lk in dn.LINH_KIEN.items():
        if lk.get("trong"):
            md.append(f"| {TEN.get(p, lk['ten'])} | {', '.join(chu_chan(c) for c in lk['trong'])} | |")
    dung = set(dn.chan_esp_dung())
    nguon_esp = ("GND", "VIN", "3V3")
    trong_esp = [c for c in dn.ESP_TRAI + dn.ESP_PHAI if c not in dung and c not in nguon_esp]
    ghi_esp = {"EN": "Nút reset", "TX0": "Cổng USB nạp/log", "RX0": "Cổng USB nạp/log",
               "D2": "Chân strapping, để hở", "D15": "Chân strapping, để hở", "D14": "Còn trống"}
    for c in trong_esp:
        md.append(f"| ESP32 | {c} | {ghi_esp.get(c, '')} |")
    md.append("| ESP32 | GND, VIN, 3V3 | Nối qua đế cắm của board mở rộng, không đi dây riêng |")

    # Tóm tắt nguồn
    nguon = bang_nguon()
    md += ["", "## Tóm tắt nguồn", "", "| Nguồn | Linh kiện | Ghi chú |", "|---|---|---|",
           "| Adapter 5 V | → ACS712 (IP+ → IP−) → jack DC board mở rộng | Mọi dòng tải, kể cả ESP32, "
           "đi qua ACS712 |"]
    ghi_5v = "Lấy từ hàng chân 5V của board. PIR đi dây 5 V riêng (đi chung dây relay/servo làm PIR kẹt ON)"
    ghi_3v3 = ("Lấy từ hàng chân 3V3. Các module này nuôi 5 V thì chân ra sẽ vượt 3,3 V vào thẳng ESP32. "
               "Trở R3 (kéo lên công tắc từ) cũng nối hàng 3V3")
    for k, ghi in (("5V", ghi_5v), ("3V3", ghi_3v3)):
        mods = [TEN.get(p, p) for p in nguon[k] if p not in ("r1", "r2", "r3")]
        md.append(f"| Hàng chân {k} | {', '.join(mods)} | {ghi} |")
    md.append("| Hàng chân 5V qua relay | " + ", ".join(TEN[p] for p in TAI) +
              " | 5 V vào COM1 (nối cầu COM1–COM4), NO → tải (+), tải (−) → GND |")

    md += ["", f"Tổng cộng **{len(dn.DAY)} sợi dây**, {len(dung)} chân ESP32 có tín hiệu.", ""]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Đã ghi {OUT} — {len(dn.DAY)} dây")


if __name__ == "__main__":
    main()
