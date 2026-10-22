"""Fixture pytest cho test thẻ 3D: máy chủ tĩnh gốc /config + Chromium headless (Playwright sync).

Cờ Chromium chạy được WebGL headless trong container: --use-gl=angle --use-angle=swiftshader
--enable-unsafe-swiftshader (render phần mềm, không cần GPU).
"""
import socket
import subprocess
import sys
import time

import pytest
from playwright.sync_api import sync_playwright

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
HARNESS = f"{BASE}/smarthome/tests/3d/harness.html"
CHROMIUM_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]


@pytest.fixture(scope="session")
def server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd="/config", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):  # chờ cổng mở (tối đa ~10 giây)
            try:
                socket.create_connection(("127.0.0.1", PORT), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("máy chủ http không mở được cổng")
        yield BASE
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(args=CHROMIUM_ARGS)
        yield b
        b.close()


@pytest.fixture
def page(browser, server):
    # Ngữ cảnh mới mỗi test để localStorage sạch
    ctx = browser.new_context(viewport={"width": 1000, "height": 700})
    pg = ctx.new_page()
    pg.errors = []
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    yield pg
    ctx.close()
