"""Sinh /config/www/smarthome/floorplan.svg + /config/smarthome/dashboard.yaml.

Mặt bằng chỉ để THAO TÁC (17/10/2026): không còn khu kỹ thuật, dây hay chú giải.
  • Phía trên (tường trước, y = 0): PHÒNG KHÁCH kiêm sảnh — cửa chính góc trái, cửa sổ giữa,
    TV treo tường trước, sofa áp vách giữa quay về TV.
  • Vách giữa (y = 188) có 2 cửa: trái vào BẾP, phải vào PHÒNG NGỦ (giường đôi, đầu giường tường phải).
  • Vách ngăn bếp | ngủ x = 220, tường sau y = 355.
1 đơn vị SVG = 1 mm của mô hình. Chân ESP32 theo bảng 16/10 (khớp /config/esphome/smarthome.yaml).
Trang "Điều khiển" lấy từ /config/smarthome/dashboard_dieu_khien.yaml.
"""
import hashlib
import json
import os
import textwrap

import yaml

VB_X, VB_Y, VB_W, VB_H = -20, -55, 540, 430


def pct(x, y):
    return f"{(x - VB_X) / VB_W * 100:.1f}%", f"{(y - VB_Y) / VB_H * 100:.1f}%"


# ---------------- Kích thước chính ----------------
HOUSE_W, MID_Y, PART_X, BACK_Y = 500, 188, 220, 355
W = 12  # lệch từ mặt tường tới tâm biểu tượng

# ---------------- Thiết bị trên mặt bằng ----------------
# slug: (loại, entity, vị trí mm, chạm, icon riêng, tên · chân, chỗ hiện tên)
#   chạm: toggle (bật/tắt) · more-info (xem chi tiết). Còi chỉ xem chi tiết để khỏi bấm nhầm.
#   Nhấn giữ bất kỳ thiết bị nào → bảng chi tiết (vd chọn màu đèn RGB, nút dừng cửa).
E = "smarthome"
DEV = {
    # phòng khách & sảnh
    "door":    ("icon", f"cover.{E}_cua", (52, W), "toggle", None,
                "Cửa · chạm để mở/đóng · công tắc từ IO34 · servo IO12", "below"),
    "buzzer":  ("icon", f"switch.{E}_coi", (W, 70), "more-info", "mdi:bullhorn", "Còi · IO13", "right"),
    "pir":     ("icon", f"binary_sensor.{E}_chuyen_dong_truoc_nha", (HOUSE_W - W, 75), "more-info", None,
                "PIR HC-SR501 · IO35", "left"),
    "living":  ("icon", f"switch.{E}_den_phong_khach", (470, W), "toggle", "mdi:ceiling-light",
                "Đèn phòng khách · relay IO17", "left"),
    "rgb":     ("icon", f"light.{E}_den_rgb", (280, 150), "toggle", "mdi:lightbulb-multiple",
                "Đèn RGB khách + ngủ · IO23/22/21 · nhấn giữ để chọn màu", "above"),
    # mặt ngoài tường trước
    "porch":   ("icon", f"switch.{E}_den_hien", (75, -W), "toggle", "mdi:outdoor-lamp",
                "Đèn hiên · relay IO5", "above"),
    "rfid":    ("icon", f"sensor.{E}_the_vua_quet", (128, -W), "more-info", "mdi:nfc-variant",
                "RFID RC522 · SPI 25/26/33/27", "above"),
    "ldr":     ("icon", f"binary_sensor.{E}_troi_toi", (180, -W), "more-info", "mdi:weather-night",
                "Quang trở · IO32", "above"),
    # bếp
    "gas":     ("icon", f"binary_sensor.{E}_bao_khi_gas_bep", (W, 245), "more-info", None,
                "MQ-2 · IO39", "right"),
    "gaslvl":  ("label", f"sensor.{E}_muc_khi_gas", (52, 245), "more-info", None, "Mức khí gas (AO)", "below"),
    "flame":   ("icon", f"binary_sensor.{E}_bao_chay_bep", (W, 282), "more-info", None,
                "Cảm biến lửa · IO18", "right"),
    # phòng ngủ
    "fan":     ("icon", f"switch.{E}_quat_hut_phong_ngu", (PART_X + W, 268), "toggle", "mdi:fan",
                "Quạt hút · relay IO4", "right"),
    "dht":     ("label", f"sensor.{E}_dht11", (318, BACK_Y - 11), "more-info", None, "DHT11 · IO19", "above"),
    "bedroom": ("icon", f"switch.{E}_den_phong_ngu", (440, BACK_Y - W), "toggle", "mdi:lamp",
                "Đèn ngủ · relay IO16", "above"),
}

# Vị trí người dùng tự kéo trong trình soạn HA (push_dashboard.py --pull → positions.json, đơn vị %).
# File ghi kèm viewBox lúc lấy vị trí → đổi khung ảnh vẫn quy đúng ra mm.
POS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")
if os.path.exists(POS_FILE):
    raw = json.load(open(POS_FILE, encoding="utf-8"))
    px, py, pw, ph = raw.pop("_viewbox", [VB_X, VB_Y, VB_W, VB_H])
    user_pos = {ent: (round(px + lp / 100 * pw, 1), round(py + tp / 100 * ph, 1))
                for ent, (lp, tp) in raw.items()}
    for slug, d in DEV.items():
        if d[1] in user_pos:
            DEV[slug] = (d[0], d[1], user_pos[d[1]], *d[3:])

# ---------------- SVG ----------------
WALL = 'stroke="#2f2925" stroke-width="6" stroke-linecap="square"'
walls = [
    (0, 0, 45, 0), (105, 0, 201, 0), (321, 0, 500, 0),        # tường trước: cửa chính 45–105, cửa sổ 201–321
    (0, 0, 0, BACK_Y), (500, 0, 500, BACK_Y),                  # tường trái / phải
    (0, MID_Y, 55, MID_Y), (105, MID_Y, 235, MID_Y), (285, MID_Y, 500, MID_Y),  # vách giữa + cửa bếp / cửa ngủ
    (PART_X, MID_Y, PART_X, BACK_Y),                           # vách ngăn bếp | ngủ
    (0, BACK_Y, 500, BACK_Y),                                  # tường sau
]
rooms = [
    (0, 0, 500, MID_Y, "#f1f6ee", "PHÒNG KHÁCH", 200, 95),
    (0, MID_Y, PART_X, BACK_Y - MID_Y, "#f8f1ea", "BẾP", 122, MID_Y + 22),
    (PART_X, MID_Y, 500 - PART_X, BACK_Y - MID_Y, "#eef2f8", "PHÒNG NGỦ", 296, MID_Y + 22),
]
TXT = 'font-size="13" font-weight="600" letter-spacing="1"'
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VB_X} {VB_Y} {VB_W} {VB_H}" '
    'font-family="Inter, Roboto, Arial, sans-serif">',
    f'<rect x="{VB_X}" y="{VB_Y}" width="{VB_W}" height="{VB_H}" fill="#fbfaf8"/>',
    # lưới nền 1 cm như sơ đồ gốc
    '<defs><pattern id="g" width="10" height="10" patternUnits="userSpaceOnUse">'
    '<path d="M10 0H0V10" fill="none" stroke="#ebe8e3" stroke-width="0.6"/></pattern></defs>',
    f'<rect x="{VB_X}" y="{VB_Y}" width="{VB_W}" height="{VB_H}" fill="url(#g)"/>',
]
for x, y, w, h, c, *_ in rooms:
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>')
for *_, label, lx, ly in rooms:
    svg.append(f'<text x="{lx}" y="{ly}" {TXT} fill="#7a6f66">{label}</text>')

FURN = 'fill="#ffffff" stroke="#3a3430" stroke-width="1.2" rx="3"'
# Nội thất: (loại, x, y, rộng, sâu, các phần tử SVG) — SVG và model3d.json dùng chung khối thô (x, y, w, d)
FURNITURE = [
    # TV treo tường trước
    ("tv", 345, 4, 100, 6, [
        '<rect x="345" y="4" width="100" height="6" fill="#3a3430" rx="1.5"/>',
        '<rect x="380" y="10" width="30" height="3" fill="#8a817a" rx="1"/>',
    ]),
    # sofa 3 chỗ áp vách giữa, quay về TV
    ("sofa", 340, 140, 120, 45, [
        f'<rect x="340" y="140" width="120" height="45" {FURN}/>',
        f'<rect x="340" y="176" width="120" height="9" {FURN}/>',                 # tựa lưng
        f'<rect x="340" y="140" width="9" height="45" {FURN}/>',
        f'<rect x="451" y="140" width="9" height="45" {FURN}/>',
        '<line x1="400" y1="140" x2="400" y2="176" stroke="#3a3430" stroke-width="1"/>',
    ]),
    # giường đôi, đầu giường tường phải
    ("bed", 375, 215, 120, 100, [
        f'<rect x="375" y="215" width="120" height="100" {FURN}/>',
        f'<rect x="466" y="222" width="22" height="40" {FURN}/>',                 # gối
        f'<rect x="466" y="268" width="22" height="40" {FURN}/>',
        '<line x1="460" y1="215" x2="460" y2="315" stroke="#3a3430" stroke-width="1"/>',
    ]),
    # bếp nấu áp tường sau
    ("stove", 60, 305, 70, 47, [
        f'<rect x="60" y="305" width="70" height="47" {FURN}/>',
        '<circle cx="78" cy="328" r="9" fill="#3a3430"/><circle cx="112" cy="328" r="9" fill="#3a3430"/>',
    ]),
]
for *_, parts in FURNITURE:
    svg += parts
for x1, y1, x2, y2 in walls:
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {WALL}/>')
# cửa sổ 12 cm giữa tường trước
svg.append('<rect x="201" y="-2.5" width="120" height="5" fill="#ffffff" stroke="#3a3430" stroke-width="1"/>'
           '<line x1="201" y1="0" x2="321" y2="0" stroke="#7fb1d8" stroke-width="1.5"/>')


# cửa đi: bản lề + cánh mở vào trong + cung quay
def door(x_free, x_hinge, y):
    r = x_hinge - x_free
    return (f'<line x1="{x_hinge}" y1="{y}" x2="{x_hinge}" y2="{y + r}" stroke="#3a3430" stroke-width="2"/>'
            f'<path d="M{x_free} {y} A{r} {r} 0 0 0 {x_hinge} {y + r}" fill="none" stroke="#3a3430" '
            f'stroke-width="1"/>')


DOORS = [(45, 105, 0), (55, 105, MID_Y), (235, 285, MID_Y)]   # (x_free, x_hinge, y); cửa y = 0 là cửa chính
svg += [door(*d) for d in DOORS]
svg.append('<text x="250" y="-45" font-size="10" fill="#9a8f84" text-anchor="middle">'
           'Phía ngoài tường trước: đèn hiên · đầu đọc RFID · quang trở</text>')
svg.append("</svg>")

os.makedirs("/config/www/smarthome", exist_ok=True)
SVG_TEXT = "\n".join(svg) + "\n"
open("/config/www/smarthome/floorplan.svg", "w", encoding="utf-8").write(SVG_TEXT)
# HA cho trình duyệt lưu đệm /local rất lâu → gắn mã phiên bản để ảnh mới luôn được tải lại
SVG_VER = hashlib.md5(SVG_TEXT.encode()).hexdigest()[:8]



# ---------------- model3d.json cho thẻ three.js ----------------
def export_model3d(path):
    """Xuất hình học nhà + vị trí thiết bị (mm, đã áp positions.json) cho thẻ 3D."""
    model = {
        "house": {"w": HOUSE_W, "d": BACK_Y, "wall_h": 135, "door_h": 105, "wall_t": 6},
        "walls": [list(w) for w in walls],
        "rooms": [{"name": r[5], "x": r[0], "y": r[1], "w": r[2], "d": r[3], "color": r[4]} for r in rooms],
        "window": {"x1": 201, "x2": 321, "y": 0, "sill": 45, "top": 105},
        "doors": [{"x_free": xf, "x_hinge": xh, "y": y, **({"main": True} if y == 0 else {})}
                  for xf, xh, y in DOORS],
        "furniture": [{"kind": k, "x": x, "y": y, "w": w, "d": d} for k, x, y, w, d, _ in FURNITURE],
        "devices": {slug: {"entity": d[1], "x": d[2][0], "y": d[2][1], "tap": d[3],
                           "title": d[5].split(" · ")[0]} for slug, d in DEV.items()},
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
        f.write("\n")


export_model3d("/config/www/smarthome/3d/model3d.json")

# ---------------- Phần tử trên mặt bằng ----------------
# Tên thiết bị hiện khi rê chuột; thiết bị offline (unavailable / chưa có trong HA) → luôn hiện.
PLACE = {
    "above": "left: 50%; bottom: calc(100% + 3px); transform: translateX(-50%);",
    "below": "left: 50%; top: calc(100% + 3px); transform: translateX(-50%);",
    "left": "right: calc(100% + 5px); top: 50%; transform: translateY(-50%);",
    "right": "left: calc(100% + 5px); top: 50%; transform: translateY(-50%);",
}


def title_css():
    base = ('#root > .element::after { content: none; position: absolute; white-space: nowrap; '
            'pointer-events: none; z-index: 3; padding: 2px 7px; border-radius: 6px; '
            'background: rgba(40,36,33,0.92); color: #fff; font-size: 11px; font-weight: 600; '
            'line-height: 1.35; letter-spacing: 0; opacity: 0; transition: opacity 0.15s; }')
    rules = [f'#root > .element[style*="--e-{slug}:"]::after {{ content: "{d[5]}"; {PLACE[d[6]]} }}'
             for slug, d in DEV.items()]
    # ("unknown" của entity đang tồn tại — vd chưa quẹt thẻ — vẫn tính là online)
    offline = [f"{{% if is_state('{d[1]}', 'unavailable') or state_attr('{d[1]}', 'friendly_name') is none %}}"
               f'#root > .element[style*="--e-{slug}:"]::after {{ opacity: 1; }}{{% endif %}}'
               for slug, d in DEV.items()]
    return "\n".join([base, *rules, "#root > .element:hover::after { opacity: 1; }", *offline]) + "\n"


def element_yaml(slug, kind, entity, xy, tap, icon, title, _place):
    left, top = pct(*xy)
    head = f"        - type: {'state-icon' if kind == 'icon' else 'state-label'}\n          entity: {entity}\n"
    if icon:
        head += f"          icon: {icon}\n"
    head += (f"          title: \"{title}\"\n"
             f"          tap_action: {{ action: {tap} }}\n"
             "          hold_action: { action: more-info }\n")
    style = f"          style:\n            left: {left}\n            top: {top}\n            --e-{slug}: 1\n"
    if kind == "icon":
        style += ("            '--mdc-icon-size': 30px\n"
                  "            background: rgba(255,255,255,0.85)\n"
                  "            border-radius: 50%\n"
                  "            padding: 4px\n"
                  "            box-shadow: 0 1px 3px rgba(0,0,0,0.25)\n")
    else:
        style += ("            color: '#3d3530'\n"
                  "            font-size: 15px\n"
                  "            font-weight: 600\n"
                  "            background: rgba(255,255,255,0.85)\n"
                  "            border-radius: 8px\n"
                  "            padding: 2px 8px\n")
    return head + style


def reindent(block, n):
    return textwrap.indent(textwrap.dedent(block), " " * n)


TITLE_CSS = reindent(title_css(), 16).rstrip("\n")
ELEMENTS = reindent("".join(element_yaml(slug, *d) for slug, d in DEV.items()), 14).rstrip("\n")

ACCESS_TABLE = reindent(r"""{% set rows = state_attr('sensor.smarthome_db_lich_su_truy_cap', 'items') %}
{% set rows = (rows | from_json) if rows is string else (rows or []) %}
{% if rows | count == 0 %}
_Chưa có lượt truy cập nào._
{% else %}
| Thời gian | Người | UID | Kết quả |
|:--|:--|:--|:--|
{% for r in rows -%}
| {{ r.t }} | {{ r.who }} | `{{ r.uid if r.uid else '—' }}` | {{ {'granted': '✅', 'denied': '❌', 'lockout': '🚨'}[r.r] }} {{ r.rv }} |
{% endfor %}
{% endif %}""", 14).lstrip()

EVENTS_TABLE = reindent(r"""{% set rows = state_attr('sensor.smarthome_db_su_kien', 'items') %}
{% set rows = (rows | from_json) if rows is string else (rows or []) %}
{% set label = {'door/open': '🚪 Cửa mở', 'door/closed': '🚪 Cửa đóng', 'fire/on': '🔥 Báo cháy', 'fire/off': '✅ Hết báo cháy', 'gas/on': '💨 Rò khí gas', 'gas/off': '✅ Hết khí gas'} %}
{% if rows | count == 0 %}
_Chưa có sự kiện._
{% else %}
| Thời gian | Sự kiện |
|:--|:--|
{% for r in rows -%}
| {{ r.t }} | {{ label.get((r.kind if r.type == 'alarm' else r.type) ~ '/' ~ r.state, r.type ~ ' ' ~ r.state) }} |
{% endfor %}
{% endif %}""", 14).lstrip()

CARDS_TABLE = reindent(r"""{% set cards = state_attr('sensor.smarthome_db_danh_sach_the', 'cards') %}
{% set cards = (cards | from_json) if cards is string else (cards or []) %}
{% if cards | count == 0 %}
_Chưa có thẻ nào. Quẹt thẻ vào đầu đọc, bấm **Lấy UID thẻ vừa quẹt**, nhập tên rồi **Thêm thẻ**._
{% else %}
| UID | Chủ thẻ | Trạng thái | Ngày thêm |
|:--|:--|:--|:--|
{% for c in cards -%}
| `{{ c.uid }}` | {{ c.name if c.name else '_chưa đặt tên_' }} | {{ '🟢 Hoạt động' if c.active else '⛔ Đã khóa' }} | {{ c.created }} |
{% endfor %}
{% endif %}
{% if has_value('sensor.smarthome_so_the_hop_le') %}Trên ESP32 hiện có **{{ states('sensor.smarthome_so_the_hop_le') | int }}** thẻ hợp lệ.{% else %}_ESP32 chưa kết nối — chưa đối chiếu được số thẻ._{% endif %}""", 14).lstrip()

DASHBOARD = f"""# Sinh tự động — Smarthome đồ án. Mặt bằng: /local/smarthome/floorplan.svg
title: Smarthome đồ án
views:
  # ================= 1. TỔNG QUAN =================
  - title: Tổng quan
    path: tong-quan
    icon: mdi:floor-plan
    type: sections
    max_columns: 3
    sections:
      - column_span: 2
        cards:
          - type: heading
            heading: Mô hình nhà thông minh
            heading_style: title
            badges:
              - type: entity
                entity: binary_sensor.smarthome_ket_noi
                show_state: true
                color: green
              - type: entity
                entity: switch.smarthome_che_do_tu_dong
                show_state: true
          - type: picture-elements
            image: /local/smarthome/floorplan.svg?v={SVG_VER}
            card_mod:
              style: |
{TITLE_CSS}
            grid_options: {{ columns: full }}
            elements:
{ELEMENTS}
      - cards:
          - type: conditional
            conditions:
              - condition: state
                entity: binary_sensor.smarthome_ket_noi
                state_not: "on"
            card:
              type: markdown
              content: >-
                **ESP32 chưa kết nối.** Thiết bị trên mặt bằng hiện tên khi board offline.
          - type: conditional
            conditions:
              - condition: state
                entity: binary_sensor.smarthome_bao_chay_bep
                state: "on"
            card:
              type: markdown
              content: "## 🔥 PHÁT HIỆN LỬA Ở BẾP\\nCòi và đèn RGB đang báo động."
          - type: conditional
            conditions:
              - condition: state
                entity: binary_sensor.smarthome_bao_khi_gas_bep
                state: "on"
            card:
              type: markdown
              content: "## 💨 RÒ KHÍ GAS Ở BẾP\\nCòi kêu, quạt hút đã bật."
          - type: heading
            heading: Cửa chính
          - type: tile
            entity: cover.smarthome_cua
            name: Cửa
            grid_options: {{ columns: 12 }}
            features:
              - type: cover-open-close
          - type: tile
            entity: button.smarthome_mo_cua
            name: Mở cửa
            icon: mdi:door-open
            tap_action:
              action: perform-action
              perform_action: button.press
              target: {{ entity_id: button.smarthome_mo_cua }}
          - type: tile
            entity: button.smarthome_dong_cua
            name: Đóng cửa
            icon: mdi:door-closed
            tap_action:
              action: perform-action
              perform_action: button.press
              target: {{ entity_id: button.smarthome_dong_cua }}
          - type: tile
            entity: sensor.smarthome_db_lich_su_truy_cap
            name: Lượt gần nhất
            grid_options: {{ columns: 12 }}
          - type: heading
            heading: Tình trạng
          - type: tile
            entity: sensor.smarthome_nhiet_do_phong_ngu
            name: Nhiệt độ
          - type: tile
            entity: sensor.smarthome_do_am_phong_ngu
            name: Độ ẩm
          - type: tile
            entity: sensor.smarthome_muc_khi_gas
            name: Mức gas
          - type: tile
            entity: sensor.smarthome_cong_suat_tieu_thu
            name: Công suất
          - type: tile
            entity: button.smarthome_tat_bao_dong
            name: Tắt báo động
            color: red
            grid_options: {{ columns: 12 }}
            tap_action:
              action: perform-action
              perform_action: button.press
              target: {{ entity_id: button.smarthome_tat_bao_dong }}

  # ================= 2. TRUY CẬP =================
  - title: Lịch sử truy cập
    path: truy-cap
    icon: mdi:card-account-details
    type: sections
    max_columns: 3
    sections:
      - cards:
          - type: heading
            heading: Thống kê
          - type: tile
            entity: sensor.smarthome_db_luot_truy_cap_hom_nay
            name: Lượt hôm nay
          - type: tile
            entity: sensor.smarthome_db_sai_the_hom_nay
            name: Sai thẻ hôm nay
            color: red
          - type: tile
            entity: sensor.smarthome_db_luot_truy_cap_7_ngay
            name: 7 ngày qua
          - type: tile
            entity: sensor.smarthome_the_vua_quet
            name: Thẻ vừa quẹt
          - type: heading
            heading: Sự kiện cửa & báo cháy
          - type: markdown
            content: |-
              {EVENTS_TABLE}
      - column_span: 2
        cards:
          - type: heading
            heading: 20 lượt truy cập gần nhất
          - type: markdown
            content: |-
              {ACCESS_TABLE}

  # ================= 4. QUẢN LÝ =================
  - title: Quản lý
    path: quan-ly
    icon: mdi:cog
    type: sections
    max_columns: 3
    sections:
      - cards:
          - type: heading
            heading: Thêm thẻ mới
          - type: markdown
            content: |-
              1. Quẹt thẻ mới vào đầu đọc (sẽ báo sai thẻ — bình thường).
              2. Bấm **Lấy UID thẻ vừa quẹt**, nhập tên chủ thẻ.
              3. Bấm **Thêm thẻ** — ESP32 nhận danh sách mới sau 1–2 giây.
          - type: entities
            entities:
              - entity: sensor.smarthome_the_vua_quet
                name: Thẻ vừa quẹt
              - entity: input_text.smarthome_card_uid
                name: UID
              - entity: input_text.smarthome_card_name
                name: Tên chủ thẻ
          - type: tile
            entity: script.smarthome_doan_lay_the_vua_quet
            name: Lấy UID thẻ vừa quẹt
            icon: mdi:card-search
            tap_action: {{ action: perform-action, perform_action: script.smarthome_doan_lay_the_vua_quet }}
          - type: tile
            entity: script.smarthome_doan_them_the
            name: Thêm thẻ
            icon: mdi:card-plus
            color: green
            tap_action: {{ action: perform-action, perform_action: script.smarthome_doan_them_the }}
      - cards:
          - type: heading
            heading: Thẻ đã đăng ký
          - type: markdown
            content: |-
              {CARDS_TABLE}
          - type: entities
            entities:
              - entity: input_select.smarthome_card_pick
                name: Chọn thẻ
          - type: tile
            entity: script.smarthome_doan_the_da_chon
            name: Khóa thẻ
            icon: mdi:card-remove
            color: orange
            tap_action:
              action: perform-action
              perform_action: script.smarthome_doan_the_da_chon
              data: {{ lenh: disable }}
          - type: tile
            entity: script.smarthome_doan_the_da_chon
            name: Bật lại thẻ
            icon: mdi:card-account-details
            color: green
            tap_action:
              action: perform-action
              perform_action: script.smarthome_doan_the_da_chon
              data: {{ lenh: enable }}
          - type: tile
            entity: script.smarthome_doan_the_da_chon
            name: Xóa thẻ
            icon: mdi:delete
            color: red
            tap_action:
              action: perform-action
              perform_action: script.smarthome_doan_the_da_chon
              data: {{ lenh: delete }}
              confirmation:
                text: Xóa hẳn thẻ đang chọn? Lịch sử truy cập vẫn được giữ.
      - cards:
          - type: heading
            heading: Hệ thống
          - type: entities
            entities:
              - entity: switch.smarthome_che_do_tu_dong
              - entity: button.smarthome_dong_cua
              - entity: switch.smarthome_coi
              - type: divider
              - entity: binary_sensor.smarthome_ket_noi
              - entity: sensor.smarthome_so_the_hop_le
              - entity: sensor.smarthome_db_danh_sach_the
                name: Số thẻ trong database
              - type: divider
              - entity: button.smarthome_hieu_chuan_acs712_0_a
          - type: markdown
            content: >-
              **Hiệu chuẩn ACS712:** tháo dây IP− khỏi rail, cắm USB cho ESP32
              (adapter vẫn cắm), bấm nút hiệu chuẩn rồi nối lại dây.
"""

# Trang "Điều khiển" và "Mô hình 3D" (nguồn riêng) chèn ngay sau Tổng quan để --full không làm mất các trang này
board = yaml.safe_load(DASHBOARD)
board["views"].insert(1, yaml.safe_load(open("/config/smarthome/dashboard_dieu_khien.yaml", encoding="utf-8")))
board["views"].insert(2, yaml.safe_load(open("/config/smarthome/dashboard_3d.yaml", encoding="utf-8")))
with open("/config/smarthome/dashboard.yaml", "w", encoding="utf-8") as f:
    f.write("# Sinh tự động bởi tools/build_dashboard.py — đừng sửa tay\n")
    yaml.safe_dump(board, f, allow_unicode=True, sort_keys=False, width=1000)
print("ok", [v["path"] for v in board["views"]])
