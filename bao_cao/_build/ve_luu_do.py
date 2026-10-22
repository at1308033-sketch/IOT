# -*- coding: utf-8 -*-
"""Vẽ lại các lưu đồ báo cáo (Hình 3.17, 3.18, 3.19, 3.19b, 3.20) theo đúng esphome/smarthome.yaml.

Cùng một kiểu với các hình gốc: khối bo góc, bắt đầu/kết thúc xanh lá, xử lý xanh dương,
quyết định vàng, ghi log/chờ màu cam nhạt, báo động đỏ, ghi chú xám; nhãn "Có/Không" đỏ đậm.

Chạy:  python ve_luu_do.py [thư_mục_ra]   (mặc định /config/SmartHome_BaoCao/luu_do)
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "/config/SmartHome_BaoCao/luu_do"
W = 100  # 1 đơn vị = 0,1 inch → mọi hình rộng 10 inch, chèn cùng độ rộng thì chữ to bằng nhau
DPI = 220
FONT = 7
LABEL_FONT = 6.6
ARROW = "#404040"
LABEL = "#C00000"
STYLE = {  # (nền, viền)
    "start": ("#E2EFDA", "#6AA84F"),
    "proc": ("#DDEBF7", "#4A86C8"),
    "dec": ("#FFF2CC", "#D6A21E"),
    "log": ("#FCE4D6", "#E07B39"),
    "alarm": ("#F8CBAD", "#C0392B"),
    "gray": ("#EDEDED", "#808080"),
}

plt.rcParams["font.family"] = "DejaVu Sans"


class Chart:
    def __init__(self, height, bottom=0):
        self.h = height
        self.fig = plt.figure(figsize=(W / 10, (height - bottom) / 10))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(bottom, height)
        self.ax.axis("off")
        self.nodes = {}
        self.texts = []

    # ---------- khối ----------
    def node(self, key, kind, x, y, w, h, text):
        face, edge = STYLE[kind]
        if kind == "dec":
            pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
            self.ax.add_patch(Polygon(pts, closed=True, fc=face, ec=edge, lw=1.0, zorder=2))
        else:
            r = min(h * 0.45, 3.0) if kind == "start" else 0.35
            self.ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                             boxstyle=f"round,pad=0,rounding_size={r}",
                                             fc=face, ec=edge, lw=1.0, zorder=2))
        t = self.ax.text(x, y, text, ha="center", va="center", fontsize=FONT,
                         color="#1A1A1A", zorder=3, linespacing=1.25)
        self.texts.append((key, kind, x, y, w, h, t))
        self.nodes[key] = (x, y, w, h)

    def p(self, key, side):
        """Điểm nối: top / bottom / left / right."""
        x, y, w, h = self.nodes[key]
        return {"top": (x, y + h / 2), "bottom": (x, y - h / 2),
                "left": (x - w / 2, y), "right": (x + w / 2, y)}[side]

    # ---------- mũi tên gấp khúc ----------
    def edge(self, pts, arrow=True, label=None, at=None, ha="left", va="bottom"):
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        if arrow:
            self.ax.plot(xs[:-1], ys[:-1], color=ARROW, lw=0.9, zorder=1, solid_capstyle="butt")
            self.ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=1,
                             arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=0.9,
                                             mutation_scale=8, shrinkA=0, shrinkB=0))
        else:
            self.ax.plot(xs, ys, color=ARROW, lw=0.9, zorder=1)
        if label:
            if at:
                lx, ly = at
            else:
                (x0, y0), (x1, y1) = pts[0], pts[1]
                if y1 < y0 and x1 == x0:  # nhánh đi xuống: nhãn dưới đỉnh, bên phải đường
                    lx, ly, va = x0 + 1.0, y0 - 0.8, "top"
                elif x1 < x0:  # nhánh sang trái
                    lx, ly, ha = x0 - 1.0, y0 + 0.6, "right"
                else:  # nhánh sang phải
                    lx, ly = x0 + 1.0, y0 + 0.6
            self.ax.text(lx, ly, label, color=LABEL, fontsize=LABEL_FONT, fontweight="bold",
                         ha=ha, va=va, zorder=4)

    # ---------- kiểm tra chữ không tràn khối ----------
    def check(self, name):
        self.fig.canvas.draw()
        inv = self.ax.transData.inverted()
        bad = []
        for key, kind, x, y, w, h, t in self.texts:
            bb = t.get_window_extent()
            (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
            tw, th = x1 - x0, y1 - y0
            # hình thoi: chữ phải nằm trong hình thoi → |dx|/(w/2) + |dy|/(h/2) ≤ 1 ở góc khung chữ
            fit = (tw / w + th / h <= 0.98) if kind == "dec" else (tw <= w - 1.2 and th <= h - 0.8)
            if not fit:
                bad.append(f"{key} (chữ {tw:.1f}×{th:.1f}, khối {w}×{h})")
        if bad:
            print(f"[{name}] CHỮ TRÀN:", "; ".join(bad))
        return not bad

    def save(self, name):
        ok = self.check(name)
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, name)
        self.fig.savefig(path, dpi=DPI, facecolor="white")
        plt.close(self.fig)
        print(("OK  " if ok else "LỖI ") + path)
        return ok


# =====================================================================
# Hình 3.17 — script close_door
# =====================================================================
def hinh_3_17():
    c = Chart(136)
    X, R, LL, RL = 42, 78, 4, 95  # cột chính, cột phải, làn trái, làn phải
    c.node("s", "start", X, 129, 30, 6, "close_door · close_tries = 0")
    c.node("d_loop", "dec", X, 114, 28, 10, "close_tries < 3 ?")
    c.node("d_closed", "dec", X, 100, 32, 10, "Cảm biến báo\nđã đóng?")
    c.node("r_99", "proc", R, 100, 26, 8, "close_tries = 99\ndoor_stuck = false")
    c.node("p_turn", "proc", X, 88, 46, 7.5,
           "Quay −40% (thuận chiều kim đồng hồ),\nchờ cảm biến báo đóng tối đa 1500 ms")
    c.node("d_ok", "dec", X, 76, 32, 10, "Cảm biến báo\nđã đóng?")
    c.node("r_over", "proc", R, 76, 22, 7, "Quay thêm 100 ms\n(cho khít)")
    c.node("l_err", "log", X, 65, 34, 7, "Ghi log lỗi: quá 1500 ms\nmà cảm biến chưa báo đóng")
    c.node("p_stop", "proc", X, 54, 34, 6, "door_stop (nhả xung servo)")
    c.node("d_open", "dec", X, 43, 28, 10, "Cửa vẫn\nđang mở?")
    c.node("r_retry", "proc", R, 43, 30, 9,
           "close_tries += 1\nquay mở lại 700 ms · bíp dài\nchờ 3 s")
    c.node("p_final", "proc", X, 26, 34, 6, "door_stop (dừng hẳn servo)")
    c.node("d_99", "dec", X, 15.5, 28, 10, "close_tries ≠ 99 ?")
    c.node("a_stuck", "alarm", R, 15.5, 30, 8,
           "door_stuck = true (để cửa mở)\ngửi sự kiện door_stuck lên MQTT")
    c.node("end", "start", X, 4.5, 22, 6, "KẾT THÚC")

    merge = 121.5
    c.edge([c.p("s", "bottom"), c.p("d_loop", "top")])
    # Có → kiểm tra cửa; Không → thoát vòng lặp (làn trái)
    c.edge([c.p("d_loop", "bottom"), c.p("d_closed", "top")], label="Có")
    lx, ly = c.p("d_loop", "left")
    c.edge([(lx, ly), (LL, ly), (LL, 26), c.p("p_final", "left")],
           label="Không (hết lượt thử\nhoặc close_tries = 99)", at=(LL + 0.8, ly + 0.6))
    # Cửa đã đóng ngay từ đầu vòng → tries = 99 → quay lại điều kiện lặp (sẽ thoát)
    c.edge([c.p("d_closed", "right"), c.p("r_99", "left")], label="Có")
    c.edge([c.p("d_closed", "bottom"), c.p("p_turn", "top")], label="Không")
    c.edge([c.p("p_turn", "bottom"), c.p("d_ok", "top")])
    c.edge([c.p("d_ok", "right"), c.p("r_over", "left")], label="Có")
    c.edge([c.p("d_ok", "bottom"), c.p("l_err", "top")], label="Không")
    rx, ry = c.p("r_over", "bottom")
    c.edge([(rx, ry), (rx, 54), c.p("p_stop", "right")])
    c.edge([c.p("l_err", "bottom"), c.p("p_stop", "top")])
    c.edge([c.p("p_stop", "bottom"), c.p("d_open", "top")])
    c.edge([c.p("d_open", "right"), c.p("r_retry", "left")], label="Có")
    # Các đường quay lại đầu vòng lặp gom vào làn phải
    c.edge([c.p("r_99", "right"), (RL, 100)], arrow=False)
    c.edge([c.p("r_retry", "right"), (RL, 43)], arrow=False)
    bx, by = c.p("d_open", "bottom")
    c.edge([(bx, by), (bx, 34), (RL, 34), (RL, merge), (X, merge)],
           label="Không (đã đóng → lượt sau đặt close_tries = 99)", at=(bx + 1.0, by - 1.0), va="top")
    c.ax.text(RL - 0.8, merge + 0.6, "quay lại đầu vòng lặp", fontsize=LABEL_FONT,
              color="#595959", ha="right", va="bottom", style="italic")
    c.edge([c.p("p_final", "bottom"), c.p("d_99", "top")])
    c.edge([c.p("d_99", "right"), c.p("a_stuck", "left")], label="Có")
    c.edge([c.p("d_99", "bottom"), c.p("end", "top")], label="Không")
    ax_, ay_ = c.p("a_stuck", "bottom")
    c.edge([(ax_, ay_), (ax_, 4.5), c.p("end", "right")])
    return c.save("Hinh_3.17_close_door.png")


# =====================================================================
# Hình 3.18 — bộ xử lý báo động (interval 500 ms)
# =====================================================================
def hinh_3_18():
    c = Chart(104)
    X, R, LL = 40, 77, 5
    c.node("s", "start", X, 97, 32, 6, "Định kỳ 500 ms (interval)")
    c.node("p_gas", "proc", X, 86, 46, 6, "gas_now = báo gas VÀ đã sấy MQ-2 quá 60 s")
    c.node("d_gas", "dec", X, 74, 32, 10, "gas_now đổi\ntrạng thái?")
    c.node("r_fan", "proc", R, 74, 38, 11,
           "gas_active = gas_now\nCó gas: bật quạt hút ngay\nHết gas: fan_apply (quạt theo độ ẩm\nnếu Chế độ tự động bật)")
    c.node("p_on", "proc", X, 61, 46, 6, "on = có lửa HOẶC gas_now HOẶC đột nhập")
    c.node("d_chg", "dec", X, 49.5, 28, 10, "on ≠ alarm_on ?")
    c.node("r_led", "alarm", R, 49.5, 38, 11,
           "alarm_on = on\non: RGB hiệu ứng \"Nháy đỏ\"\noff: tắt RGB, alarm_muted = false,\ntắt còi")
    c.node("d_buz", "dec", X, 33, 40, 12, "on VÀ chưa tắt tiếng\nVÀ còi đang tắt?")
    c.node("a_buz", "alarm", X, 19, 30, 6, "Bật còi kêu liên tục")
    c.node("end", "start", X, 7, 34, 6, "KẾT THÚC (chờ 500 ms kế tiếp)")

    c.edge([c.p("s", "bottom"), c.p("p_gas", "top")])
    c.edge([c.p("p_gas", "bottom"), c.p("d_gas", "top")])
    c.edge([c.p("d_gas", "right"), c.p("r_fan", "left")], label="Có")
    c.edge([c.p("d_gas", "bottom"), c.p("p_on", "top")], label="Không")
    fx, fy = c.p("r_fan", "bottom")
    c.edge([(fx, fy), (fx, 66), (X, 66)])
    c.edge([c.p("p_on", "bottom"), c.p("d_chg", "top")])
    c.edge([c.p("d_chg", "right"), c.p("r_led", "left")], label="Có")
    c.edge([c.p("d_chg", "bottom"), c.p("d_buz", "top")], label="Không")
    lx, ly = c.p("r_led", "bottom")
    c.edge([(lx, ly), (lx, 41.5), (X, 41.5)])
    c.edge([c.p("d_buz", "bottom"), c.p("a_buz", "top")], label="Có")
    bx, by = c.p("d_buz", "left")
    c.edge([(bx, by), (LL, by), (LL, 7), c.p("end", "left")], label="Không", at=(LL + 0.8, by + 0.6))
    c.edge([c.p("a_buz", "bottom"), c.p("end", "top")])
    return c.save("Hinh_3.18_bo_xu_ly_bao_dong.png")


# =====================================================================
# Hình 3.19 — đèn hiên tự động
# =====================================================================
def hinh_3_19():
    c = Chart(128)
    X, R, LL = 38, 79, 5
    c.node("s_pir", "start", X, 121, 32, 7, "PIR báo có chuyển động\n(lọc bật 200 ms)")
    c.node("s_dark", "start", R, 121, 32, 7, "Trời vừa tối (lọc 3 s)\nVÀ PIR đang báo chuyển động")
    c.node("d_cond", "dec", X, 102, 46, 13, "Chế độ tự động bật VÀ\ntrời tối VÀ đèn hiên đang tắt?")
    c.node("p_on", "proc", X, 88, 34, 7, "Bật relay đèn hiên\nporch_auto = true")
    c.node("p_stop", "proc", X, 77, 36, 6, "Dừng bộ đếm porch_timer")
    c.node("l_wait", "log", X, 66, 50, 7,
           "Hết chuyển động: PIR về mức thấp sau 3–5 s,\nthêm lọc tắt 10 s")
    c.node("d_auto", "dec", X, 54, 32, 10, "porch_auto = true ?")
    c.node("g_hand", "gray", R, 54, 30, 7, "Đèn bật bằng tay\n(hoặc chưa bật): không tự tắt")
    c.node("p_timer", "proc", X, 42, 40, 7, "porch_timer: chờ \"Đèn hiên tắt sau\"\n(mặc định 2 phút)")
    c.node("d_again", "dec", X, 29.5, 38, 11, "PIR báo chuyển động lại\ntrước khi hết giờ?")
    c.node("p_off", "proc", X, 16.5, 32, 7, "Tắt đèn hiên\nporch_auto = false")
    c.node("end", "start", X, 5, 22, 6, "KẾT THÚC")

    merge = 112.5
    c.edge([c.p("s_pir", "bottom"), c.p("d_cond", "top")])
    dx, dy = c.p("s_dark", "bottom")
    c.edge([(dx, dy), (dx, merge), (X, merge)])
    c.edge([c.p("d_cond", "bottom"), c.p("p_on", "top")], label="Có")
    cx, cy = c.p("d_cond", "right")
    c.edge([(cx, cy), (R, cy), (R, 77), c.p("p_stop", "right")],
           label="Không (giữ nguyên đèn)", at=(cx + 1.0, cy + 0.6))
    c.edge([c.p("p_on", "bottom"), c.p("p_stop", "top")])
    c.edge([c.p("p_stop", "bottom"), c.p("l_wait", "top")])
    c.edge([c.p("l_wait", "bottom"), c.p("d_auto", "top")])
    c.edge([c.p("d_auto", "right"), c.p("g_hand", "left")], label="Không")
    c.edge([c.p("d_auto", "bottom"), c.p("p_timer", "top")], label="Có")
    c.edge([c.p("p_timer", "bottom"), c.p("d_again", "top")])
    ax_, ay_ = c.p("d_again", "left")
    c.edge([(ax_, ay_), (LL, ay_), (LL, merge + 3.5), (X, merge + 3.5)],
           label="Có (bộ đếm bị dừng,\nquay lại đầu)", at=(LL + 0.8, ay_ + 0.6))
    c.edge([c.p("d_again", "bottom"), c.p("p_off", "top")], label="Không")
    c.edge([c.p("p_off", "bottom"), c.p("end", "top")])
    hx, hy = c.p("g_hand", "bottom")
    c.edge([(hx, hy), (hx, 5), c.p("end", "right")])
    return c.save("Hinh_3.19_den_hien.png")


# =====================================================================
# Hình 3.19b — quạt hút theo độ ẩm (bổ sung, mục 3.2.7 có nói nhưng chưa có hình)
# =====================================================================
def hinh_3_19b():
    c = Chart(112, bottom=17)
    X, R, LL = 38, 80, 5
    c.node("s_dht", "start", X, 105, 32, 7, "DHT11 có giá trị độ ẩm mới\n(mỗi 10 s)")
    c.node("p_hyst", "proc", X, 93, 52, 7.5,
           "Tính hum_high (trễ 5 %): độ ẩm ≥ ngưỡng → true\nđộ ẩm ≤ ngưỡng − 5 % → false · ở giữa: giữ nguyên")
    c.node("d_chg", "dec", X, 80, 30, 10, "hum_high đổi\ntrạng thái?")
    c.node("s_other", "start", R, 80, 32, 7, "Bật Chế độ tự động\nhoặc vừa hết gas")
    c.node("d_auto", "dec", X, 63, 40, 12, "Chế độ tự động bật\nVÀ không có gas?")
    c.node("g_keep", "gray", R, 63, 30, 7, "Không tác động quạt\n(tay / báo gas giữ quyền)")
    c.node("d_high", "dec", X, 48, 28, 10, "hum_high = true ?")
    c.node("p_on", "proc", X, 36, 24, 6, "Bật quạt hút")
    c.node("p_off", "proc", 66, 48, 18, 6, "Tắt quạt hút")
    c.node("end", "start", X, 22, 22, 6, "KẾT THÚC")

    merge = 72
    c.edge([c.p("s_dht", "bottom"), c.p("p_hyst", "top")])
    c.edge([c.p("p_hyst", "bottom"), c.p("d_chg", "top")])
    c.edge([c.p("d_chg", "bottom"), c.p("d_auto", "top")], label="Có")
    lx, ly = c.p("d_chg", "left")
    c.edge([(lx, ly), (LL, ly), (LL, 22), c.p("end", "left")], label="Không", at=(LL + 0.8, ly + 0.6))
    ox, oy = c.p("s_other", "bottom")
    c.edge([(ox, oy), (ox, merge), (X, merge)])
    c.edge([c.p("d_auto", "right"), c.p("g_keep", "left")], label="Không")
    c.edge([c.p("d_auto", "bottom"), c.p("d_high", "top")], label="Có")
    c.edge([c.p("d_high", "bottom"), c.p("p_on", "top")], label="Có")
    c.edge([c.p("d_high", "right"), c.p("p_off", "left")], label="Không")
    c.edge([c.p("p_on", "bottom"), c.p("end", "top")])
    fx, fy = c.p("p_off", "bottom")
    c.edge([(fx, fy), (fx, 29), (X, 29)])
    gx, gy = c.p("g_keep", "bottom")
    c.edge([(gx, gy), (gx, 22), c.p("end", "right")])
    return c.save("Hinh_3.19b_quat_hut.png")


# =====================================================================
# Hình 3.20 — chế độ vắng nhà và phát hiện đột nhập
# =====================================================================
def hinh_3_20():
    c = Chart(128)
    X, R, LL, RL1, RL2 = 42, 77, 5, 92, 97
    c.node("s", "start", X, 121, 32, 6, "Bật \"Chế độ vắng nhà\"")
    c.node("p_arm", "proc", X, 110, 34, 7, "away_since = millis()\nbíp ngắn xác nhận")
    c.node("d_away", "dec", X, 93, 32, 11, "Chế độ vắng nhà\ncòn bật?")
    c.node("d_evt", "dec", X, 79, 34, 11, "Cửa mở hoặc PIR\nbáo chuyển động?")
    c.node("d_exit", "dec", X, 65, 40, 11, "millis() − away_since\n> 30 s ?")
    c.node("g_skip", "gray", R, 65, 22, 7, "Bỏ qua\n(đang ra khỏi nhà)")
    c.node("a_intr", "alarm", X, 52, 44, 7, "intrusion = true\ngửi sự kiện intrusion: on lên MQTT")
    c.node("a_alarm", "alarm", X, 41, 44, 7, "Bộ xử lý báo động (500 ms):\nRGB nháy đỏ + còi kêu liên tục")
    c.node("l_wait", "log", X, 29, 60, 8,
           "Chờ: nút \"Tắt báo động\" hoặc tắt Chế độ vắng nhà\n(mở cửa hợp lệ bằng thẻ / điện thoại / nút sẽ tự tắt)")
    c.node("p_clear", "proc", X, 17.5, 40, 7, "intrusion = false · im còi\ngửi sự kiện intrusion: off")
    c.node("end", "start", 17, 6, 22, 6, "KẾT THÚC")

    merge = 102
    c.edge([c.p("s", "bottom"), c.p("p_arm", "top")])
    c.edge([c.p("p_arm", "bottom"), c.p("d_away", "top")])
    c.edge([c.p("d_away", "bottom"), c.p("d_evt", "top")], label="Có")
    ax_, ay_ = c.p("d_away", "left")
    c.edge([(ax_, ay_), (LL, ay_), (LL, 6), c.p("end", "left")],
           label="Không (thôi canh gác)", at=(LL + 0.8, ay_ + 0.6))
    c.edge([c.p("d_evt", "bottom"), c.p("d_exit", "top")], label="Có")
    ex, ey = c.p("d_evt", "right")
    c.edge([(ex, ey), (RL1, ey)], arrow=False, label="Không (chờ sự kiện)", at=(ex + 1.0, ey + 0.6))
    c.edge([c.p("d_exit", "right"), c.p("g_skip", "left")], label="Không")
    sx, sy = c.p("g_skip", "right")
    c.edge([(sx, sy), (RL1, sy), (RL1, merge), (X, merge)])
    c.edge([c.p("d_exit", "bottom"), c.p("a_intr", "top")], label="Có")
    c.edge([c.p("a_intr", "bottom"), c.p("a_alarm", "top")])
    c.edge([c.p("a_alarm", "bottom"), c.p("l_wait", "top")])
    c.edge([c.p("l_wait", "bottom"), c.p("p_clear", "top")])
    px, py = c.p("p_clear", "right")
    c.edge([(px, py), (RL2, py), (RL2, merge), (RL1, merge)], arrow=False)
    c.ax.text(RL2 - 0.8, merge + 0.6, "kiểm tra lại", fontsize=LABEL_FONT,
              color="#595959", ha="right", va="bottom", style="italic")
    return c.save("Hinh_3.20_vang_nha.png")


if __name__ == "__main__":
    results = [f() for f in (hinh_3_17, hinh_3_18, hinh_3_19, hinh_3_19b, hinh_3_20)]
    sys.exit(0 if all(results) else 1)
