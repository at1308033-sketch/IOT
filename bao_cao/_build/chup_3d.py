"""Chụp thẻ smarthome-3d-card (thẻ thật, qua harness test) cho báo cáo. Trạng thái mẫu, không gọi HA.
Cần venv có playwright (Chromium của ~/.cache/ms-playwright). Ra: /config/SmartHome_BaoCao/hinh_3_3"""
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

PORT = 8790
OUT = "/config/SmartHome_BaoCao/hinh_3_3"
ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
W, H = 1400, 820

# fullStates() của harness + vài thiết bị đang bật cho ảnh sinh động
SETUP = """(extra) => {
  const s = fullStates();
  for (const [e, st] of Object.entries(extra)) s[e] = { ...(s[e] || { attributes: {} }), ...st };
  card.hass = fakeHass(s);
}"""
NORMAL = {
    "switch.smarthome_den_phong_khach": {"state": "on"},
    "light.smarthome_den_rgb": {"state": "on", "attributes": {"supported_color_modes": ["rgb"],
                                                              "rgb_color": [40, 120, 255], "brightness": 255}},
    "switch.smarthome_den_phong_ngu": {"state": "on"},
    "sensor.smarthome_cong_suat_tieu_thu": {"state": "3.2", "attributes": {"unit_of_measurement": "W"}},
    "sensor.smarthome_muc_khi_gas": {"state": "0.62", "attributes": {"unit_of_measurement": "V"}},
}
NIGHT = dict(NORMAL, **{"switch.smarthome_den_hien": {"state": "on"},
                        "binary_sensor.smarthome_troi_toi": {"state": "on"},
                        "binary_sensor.smarthome_chuyen_dong_truoc_nha": {"state": "on"}})
GAS = {"binary_sensor.smarthome_bao_khi_gas_bep": {"state": "on"},
       "sensor.smarthome_muc_khi_gas": {"state": "1.92", "attributes": {"unit_of_measurement": "V"}},
       "switch.smarthome_quat_hut_phong_ngu": {"state": "on"},
       "switch.smarthome_coi": {"state": "on"},
       "light.smarthome_den_rgb": {"state": "on", "attributes": {"supported_color_modes": ["rgb"],
                                                                 "rgb_color": [255, 0, 0], "brightness": 255,
                                                                 "effect": "Nháy đỏ"}}}

SHOTS = [  # (tên file, trạng thái thêm, chế độ, góc nhìn)
    ("3D_toan_canh_ngay.png", NORMAL, "Ngày", "Toàn cảnh"),
    ("3D_toan_canh_dem.png", NIGHT, "Đêm", "Toàn cảnh"),
    ("3D_phong_khach.png", NORMAL, "Ngày", "Phòng khách"),
    ("3D_bao_dong_gas.png", GAS, "Ngày", "Toàn cảnh"),
]


def click(page, label):
    page.locator("smarthome-3d-card button", has_text=label).first.click()


def main(only=None):
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                           cwd="/config", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", PORT), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        with sync_playwright() as p:
            b = p.chromium.launch(args=ARGS)
            for name, extra, mode, view in SHOTS:
                if only and only not in name:
                    continue
                ctx = b.new_context(viewport={"width": W, "height": H}, locale="vi-VN")
                page = ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.goto(f"http://127.0.0.1:{PORT}/smarthome/tests/3d/harness.html?w={W}&h={H}")
                page.wait_for_function("window.card && window.fullStates", timeout=30000)
                page.evaluate(SETUP, extra)
                page.evaluate("card.ready")
                click(page, mode)
                page.wait_for_timeout(500)
                click(page, view)
                page.wait_for_timeout(12000)  # chờ tween camera + tường hạ + vài khung swiftshader
                page.screenshot(path=f"{OUT}/{name}", clip={"x": 0, "y": 0, "width": W, "height": H}, timeout=120000)
                print(name, "lỗi:" if errs else "ok", errs[:3])
                ctx.close()
            b.close()
    finally:
        srv.terminate()
        srv.wait(timeout=5)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
