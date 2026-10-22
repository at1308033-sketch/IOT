"""Kiểm tra thẻ smarthome-3d-card qua harness (nhánh mặc định: thẻ thật 900×600)."""
from conftest import HARNESS

GAS = "binary_sensor.smarthome_bao_khi_gas_bep"

# Đếm rAF đang chờ (gói window.requestAnimationFrame trước khi trang chạy)
RAF_JS = """(() => {
  const req = window.requestAnimationFrame.bind(window), can = window.cancelAnimationFrame.bind(window);
  const ids = new Set(), st = window.__raf = { max: 0, total: 0 };
  window.requestAnimationFrame = (cb) => {
    const id = req((t) => { ids.delete(id); cb(t); });
    ids.add(id); st.total++; st.max = Math.max(st.max, ids.size);
    return id;
  };
  window.cancelAnimationFrame = (id) => { ids.delete(id); can(id); };
})();"""

NO_WEBGL_JS = """(() => {
  const orig = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (t, ...a) {
    return /webgl/i.test(t) ? null : orig.call(this, t, ...a);
  };
})();"""


def open_card(page, query="", states="fullStates()", wait=True):
    page.goto(f"{HARNESS}{query}")
    page.wait_for_function("window.card && window.fullStates", timeout=20000)
    if states:
        page.evaluate(f"card.hass = fakeHass({states})")
    if wait:
        page.evaluate("card.ready")
        page.wait_for_timeout(100)


def point(page, slug):
    return page.evaluate("""(s) => {
      const r = card.getBoundingClientRect(), p = card.debug(s).screen;
      return [r.left + p[0], r.top + p[1]];
    }""", slug)


def tap(page, slug, hold=60):
    x, y = point(page, slug)
    page.mouse.move(x, y)
    page.mouse.down()
    page.wait_for_timeout(hold)
    page.mouse.up()
    page.wait_for_timeout(50)


def settle(page):
    # chờ hết tác vụ đang xử lý + một khung (xác định, không ngủ cố định)
    page.evaluate("new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)))")


def front_h(page):
    # chiều cao hiện tại của đường tường trước (y = 0)
    return page.evaluate("card._scene.getObjectByName('house').userData.cutaway.lines.find((l) => l.key === 'h0').H")


def calls(page):
    return page.evaluate("window.calls")


def more_info(page):
    return page.evaluate("window.moreInfo")


def set_state(page, entity, st):
    page.evaluate("([e, st]) => { const s = { ...card._hass.states, [e]: st }; card.hass = fakeHass(s); }",
                  [entity, st])


def test_tap_toggle(page):
    open_card(page)
    tap(page, "living")
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_den_phong_khach"}]]
    assert more_info(page) == []
    assert page.errors == []


def test_tap_buzzer_more_info(page):
    open_card(page)
    tap(page, "buzzer")
    assert calls(page) == []
    assert more_info(page) == ["switch.smarthome_coi"]
    assert page.errors == []


def test_hold_more_info(page):
    open_card(page)
    tap(page, "fan", hold=700)
    assert more_info(page) == ["switch.smarthome_quat_hut_phong_ngu"]
    assert calls(page) == []
    assert page.errors == []


def test_drag_no_toggle(page):
    open_card(page)
    x, y = point(page, "living")
    x2, y2 = point(page, "rgb")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - 80, y, steps=8)       # kéo 80 px
    page.mouse.move(x2, y2, steps=8)          # rồi nhả trên rgb
    page.mouse.up()
    settle(page)
    assert calls(page) == []
    assert more_info(page) == []
    assert page.errors == []


def test_hass_before_ready(page):
    # gán hass ngay khi thẻ vừa tạo (cùng tác vụ JS), lúc cảnh chắc chắn chưa dựng xong
    page.add_init_script("""window.onCard = (card) => {
      let done = false; card.ready.then(() => { done = true; });
      const s = fullStates(); s['switch.smarthome_den_phong_ngu'] = { state: 'on', attributes: {} };
      card.hass = fakeHass(s);
      window.early = Promise.resolve().then(() => done);
    };""")
    open_card(page, states=None)
    assert page.evaluate("window.early") is False
    assert page.evaluate("card.debug('bedroom').vis.on") is True
    assert page.errors == []


def test_state_update(page):
    open_card(page)
    set_state(page, "light.smarthome_den_rgb",
              {"state": "on", "attributes": {"rgb_color": [0, 0, 255], "brightness": 255}})
    assert page.evaluate("card.debug('rgb').vis.color") == [0, 0, 255]
    assert page.errors == []


def test_alarm_button(page):
    open_card(page)
    btn = page.locator("smarthome-3d-card button.alarm")
    assert not btn.is_visible()
    set_state(page, GAS, {"state": "on", "attributes": {}})
    btn.wait_for(state="visible", timeout=1000)
    assert "Tắt báo động" in btn.inner_text()
    btn.click()
    assert calls(page)[-1] == ["button", "press", {"entity_id": "button.smarthome_tat_bao_dong"}]
    set_state(page, GAS, {"state": "off", "attributes": {}})
    btn.wait_for(state="hidden", timeout=1000)
    assert page.errors == []


def test_demo(page):
    open_card(page, "?demo=1")
    tap(page, "door")
    assert page.evaluate("card.debug('door').vis.door") == 1
    page.wait_for_timeout(300)
    tap(page, "door")
    assert page.evaluate("card.debug('door').vis.door") == 0
    assert calls(page) == []
    assert page.errors == []


def test_idle_stops_loop(page):
    open_card(page)
    page.wait_for_timeout(2000)
    assert page.evaluate("card.loopRunning") is False
    assert page.errors == []


def test_reconnect(page):
    page.add_init_script(RAF_JS)
    open_card(page)
    stopped = page.evaluate("""async () => {
      const p = card.parentNode; card.remove();
      const off = card.loopRunning;
      await new Promise((r) => setTimeout(r, 100));
      p.appendChild(card);
      await new Promise((r) => setTimeout(r, 100));
      return off;
    }""")
    assert stopped is False
    tap(page, "living")
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_den_phong_khach"}]]
    # xoay camera để vòng lặp chạy lại
    t0 = page.evaluate("window.__raf.total")
    page.mouse.move(450, 300)
    page.mouse.down()
    page.mouse.move(520, 320, steps=10)
    page.mouse.up()
    page.wait_for_timeout(300)
    r = page.evaluate("window.__raf")
    assert r["total"] > t0, r
    assert r["max"] <= 1, r
    assert page.errors == []


def test_resize(page):
    open_card(page)
    page.evaluate("card.style.width = '500px'; card.style.height = '400px'")
    page.wait_for_function("card.renderer.domElement.clientWidth === 500 && "
                           "card.renderer.domElement.clientHeight === 400", timeout=10000)
    assert page.evaluate("card.renderer.domElement.clientHeight") == 400
    assert page.errors == []


def test_mode_persist(page):
    open_card(page)
    assert page.evaluate("card.mode") == "auto"
    page.locator("smarthome-3d-card button[data-mode=night]").click()
    assert page.evaluate("card.theme") == "night"
    page.reload()
    page.wait_for_function("window.card", timeout=20000)
    page.evaluate("card.ready")
    assert page.evaluate("card.mode") == "night"
    assert page.evaluate("card.theme") == "night"
    assert "active" in page.locator("smarthome-3d-card button[data-mode=night]").get_attribute("class")
    assert page.errors == []


# ---- kiểm tra thêm theo quyết định của điều phối ----

def test_label_tap(page):
    open_card(page)
    page.locator("smarthome-3d-card [data-slug=gaslvl]").click()
    page.locator("smarthome-3d-card [data-slug=dht]").click()
    page.wait_for_timeout(50)
    assert more_info(page) == ["sensor.smarthome_muc_khi_gas", "sensor.smarthome_nhiet_do_phong_ngu"]
    assert calls(page) == []
    assert page.errors == []


ALL = ['door', 'buzzer', 'pir', 'living', 'rgb', 'porch', 'rfid', 'ldr', 'gas', 'gaslvl', 'flame', 'fan',
       'dht', 'bedroom']


def test_devices_hit_in_default_view(page):
    # v2: tường trước tự hạ ở Toàn cảnh -> hiên/RFID/quang trở (gắn mặt ngoài tường trước) ẩn theo tường,
    # thay bằng chip tròn ngay ngoài tường; debug(s).hit = slug tại điểm chạm (phần tử DOM rồi raycast)
    open_card(page)
    hits = page.evaluate("(a) => Object.fromEntries(a.map((s) => [s, card.debug(s)]))", ALL)
    for s in ALL:
        assert hits[s]["hit"] == s, (s, hits[s])
    for s in ("porch", "rfid", "ldr"):
        assert hits[s]["chip"] is True, (s, hits[s])
    # chạm chip = chạm thiết bị
    tap(page, "porch")
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_den_hien"}]]
    tap(page, "rfid")
    assert more_info(page) == ["sensor.smarthome_the_vua_quet"]
    assert page.errors == []


LABELS = ("gaslvl", "dht")
BADGE_JS = """(a) => Object.fromEntries(a.map((s) => {
  const d = card.debug(s), el = card._chips[s] && card._chips[s].element.querySelector('button');
  const r = el && el.getBoundingClientRect();
  return [s, { ...d, size: r ? Math.min(r.width, r.height) : 0, on: !!(el && el.parentNode.classList.contains('on')) }];
}))"""


def test_badges_every_view(page):
    # mọi thiết bị (trừ nhãn) có huy hiệu tròn luôn hiện, đủ lớn để chạm, ở MỌI góc nhìn — kể cả khi tường
    # gắn thiết bị đang hạ (vd quạt trên vách bếp|ngủ x = 220 khi nhìn từ bên phải nhà)
    open_card(page)
    for view in ("overview", "living", "kitchen", "bedroom", "top"):
        page.locator(f"smarthome-3d-card button[data-view={view}]").click()
        page.wait_for_function("!card._tween && !card.loopRunning", timeout=20000)
        page.wait_for_timeout(250)   # hết chuyển động cuống huy hiệu (CSS transition 0,18 s)
        b = page.evaluate(BADGE_JS, ALL)
        w, h = page.evaluate("[card.clientWidth, card.clientHeight]")
        for s in ALL:
            x, y = b[s]["screen"]
            if 0 <= x < w and 0 <= y < h:   # trong khung: không bị huy hiệu/nhãn khác che
                assert b[s]["hit"] == s, (view, s, b[s])
            if s not in LABELS:
                assert b[s]["chip"] is True and b[s]["size"] >= 28, (view, s, b[s])
    # nhìn từ bên phải: vách x = 220 hạ -> quạt ẩn theo tường, huy hiệu vẫn chạm được (hạ xuống chân tường)
    page.evaluate("""() => { card._camera.position.set(1150, 520, 260); card._controls.target.set(250, 0, 178);
      card._controls.update(); card._kick(); }""")
    page.wait_for_function("!card.loopRunning", timeout=20000)
    b = page.evaluate(BADGE_JS, ["fan"])["fan"]
    assert b["down"] is True and b["hit"] == "fan", b
    tap(page, "fan")
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_quat_hut_phong_ngu"}]]
    assert page.errors == []


# vị trí màn hình của mọi huy hiệu: đáy-giữa phần tử (mũi nhọn) và điểm neo world chiếu lên màn hình,
# hộp nút tròn; cộng vị trí CSS của mọi phần tử con lớp CSS2D
LAYOUT_JS = """() => {
  const cam = card._camera, hr = card.getBoundingClientRect(), chips = {};
  for (const [s, o] of Object.entries(card._chips)) {
    const v = o.position.clone().project(cam), r = o.element.getBoundingClientRect();
    const b = o.element.querySelector('button').getBoundingClientRect();
    chips[s] = { tip: [r.left + r.width / 2 - hr.left, r.bottom - hr.top],
      proj: [(v.x + 1) / 2 * card._w, (1 - v.y) / 2 * card._h],
      box: [b.left - hr.left, b.top - hr.top, b.right - hr.left, b.bottom - hr.top], y: o.position.y,
      shown: o.element.style.display !== 'none' };
  }
  const pos = [...card._css.domElement.children].map((e) => getComputedStyle(e).position);
  const warns = [...card._css.domElement.children].filter((e) => e.textContent === '⚠' && e.style.display !== 'none').length;
  return { chips, pos, warns };
}"""


def check_layout(lay, ctx):
    assert set(lay["pos"]) == {"absolute"}, (ctx, lay["pos"])
    for s, c in lay["chips"].items():
        if not c["shown"]:
            continue
        # mũi nhọn đúng điểm neo (lớp CSS2D không bị đẩy lệch)
        assert abs(c["tip"][0] - c["proj"][0]) < 1.5 and abs(c["tip"][1] - c["proj"][1]) < 1.5, (ctx, s, c)
        # điểm neo không bao giờ thấp hơn mép tường đã hạ (25) + 5
        assert c["y"] >= 29, (ctx, s, c)
    # nút tròn không chồng nhau (cho phép chạm mép 2 px)
    sh = [(s, c["box"]) for s, c in lay["chips"].items() if c["shown"]]
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            (a, p), (b, q) = sh[i], sh[j]
            ov = min(p[2], q[2]) - max(p[0], q[0]), min(p[3], q[3]) - max(p[1], q[1])
            assert ov[0] <= 2 or ov[1] <= 2, (ctx, a, b, p, q)


def test_badges_unavailable_and_orbit(page):
    # ESP32 mất kết nối: mọi thiết bị không khả dụng -> huy hiệu xám, ⚠ rời chỉ còn ở nhãn; lớp CSS2D không lệch
    open_card(page, states="{}")
    lay = page.evaluate(LAYOUT_JS)
    check_layout(lay, "na")
    assert lay["warns"] <= 2, lay["warns"]   # chỉ nhãn gaslvl/dht
    assert page.evaluate("[...card.shadowRoot.querySelectorAll('.chip')].every((e) => e.classList.contains('na'))")
    # xoay một vòng quanh nhà (tường tự hạ/nâng theo góc): huy hiệu bám đúng thiết bị, không chồng nhau
    for k in range(12):
        page.evaluate("""(k) => { const c = card._controls, cam = card._camera, t = c.target;
          const off = cam.position.clone().sub(t), a = Math.PI / 6;
          cam.position.set(t.x + off.x * Math.cos(a) + off.z * Math.sin(a), cam.position.y,
            t.z - off.x * Math.sin(a) + off.z * Math.cos(a));
          c.update(); card._kick(); }""", k)
        page.wait_for_function("!card.loopRunning", timeout=20000)
        page.wait_for_timeout(250)   # hết chuyển động cuống (CSS transition)
        check_layout(page.evaluate(LAYOUT_JS), f"orbit {k * 30}°")
    assert page.errors == []


def test_badge_follows_wall(page):
    # tường trước hạ dần -> RFID (mặt tiền) trượt theo: mọi khung đáy thân ngồi đúng trên mép tường (không nhảy cóc,
    # không biến mất), huy hiệu bám theo điểm neo
    open_card(page)
    page.locator("smarthome-3d-card button[data-view=top]").click()
    page.wait_for_function("!card._tween && !card.loopRunning", timeout=20000)
    fr = page.evaluate("""() => new Promise((res) => {
      const L = card._scene.getObjectByName('house').userData.cutaway.lines.find((l) => l.key === 'h0');
      const m = card._devs.rfid.api.object.userData.mounts[0], fr = [];
      card.shadowRoot.querySelector('button[data-view=overview]').click();
      const f = () => {
        const c = card._chips.rfid, pin = card._devs.rfid.api.pin.getWorldPosition(c.position.clone());
        fr.push({ H: L.H, off: m.o.position.y, y0: m.y0, badge: c.position.distanceTo(pin) });
        card.loopRunning ? requestAnimationFrame(f) : res(fr);
      };
      requestAnimationFrame(f);
    })""")
    assert fr[0]["off"] == 0 and fr[-1]["H"] == 25, (fr[0], fr[-1])
    for f in fr:
        # đáy = y0 + off = H + 1 khi mép tường thấp hơn đáy; còn lại đứng yên ở chỗ lắp (đáy = y0)
        assert abs(f["y0"] + f["off"] - min(f["y0"], f["H"] + 1)) < 1e-6, f
        assert f["badge"] < 1e-6, f
    assert fr[-1]["off"] < -25, fr[-1]
    d = page.evaluate("card.debug('rfid')")
    assert d["down"] is True and d["hit"] == "rfid", d
    assert page.errors == []


def test_badge_does_not_block_orbit(page):
    # chạm huy hiệu bật/tắt; lăn chuột / kéo bắt đầu trên huy hiệu vẫn phóng to / xoay (sự kiện thật chuyển cho
    # OrbitControls) và không bật/tắt. Không chờ hết quán tính sau khi kéo (render phần mềm: vài khung/giây)
    open_card(page)
    tap(page, "living")
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_den_phong_khach"}]]
    x, y = point(page, "living")
    d0 = page.evaluate("card._camera.position.distanceTo(card._controls.target)")
    page.mouse.move(x, y)
    page.mouse.wheel(0, -400)
    page.wait_for_function("!card.loopRunning", timeout=60000)
    d1 = page.evaluate("card._camera.position.distanceTo(card._controls.target)")
    assert d1 < d0 - 5, (d0, d1)
    p0 = page.evaluate("card._camera.position.toArray()")
    x, y = point(page, "living")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 120, y + 10, steps=10)
    page.mouse.up()
    page.wait_for_function("(p) => card._camera.position.distanceTo({ x: p[0], y: p[1], z: p[2] }) > 5", arg=p0,
                           timeout=20000)
    assert page.evaluate("card._controls.state") == -1     # OrbitControls đã nhả con trỏ
    assert len(calls(page)) == 1 and more_info(page) == []
    assert page.errors == []


def test_tap_device_mesh(page):
    # chạm thẳng vào hình 3D thiết bị gắn tường (thân + viền) cũng nhận đúng thiết bị (raycast)
    open_card(page)
    PICK = """(a) => Object.fromEntries(a.map((s) => {
      const ring = card._devs[s].api.object.getObjectsByProperty('name', 'dev_ring')[0];
      const p = ring.getWorldPosition(ring.position.clone()).project(card._camera);
      const c = card._renderer.domElement.getBoundingClientRect();
      const x = c.left + (p.x + 1) / 2 * c.width, y = c.top + (1 - p.y) / 2 * c.height;
      return [s, card._pick(x, y + 1)];
    }))"""
    # Toàn cảnh: thiết bị mặt trước (tường hạ -> trượt xuống) quay về camera; Từ trên: thiết bị tường bên
    r = page.evaluate(PICK, ["rfid", "ldr", "rgb"])
    page.locator("smarthome-3d-card button[data-view=top]").click()
    page.wait_for_function("!card._tween && !card.loopRunning", timeout=20000)
    r.update(page.evaluate(PICK, ["gas", "pir", "buzzer"]))
    assert r == {s: s for s in r}, r
    assert page.errors == []


def test_badge_state(page):
    open_card(page)
    b = page.evaluate(BADGE_JS, ["living", "bedroom", "door"])
    page.evaluate("card.setConfig({ demo: true })")
    tap(page, "living" if not b["living"]["on"] else "bedroom")
    b2 = page.evaluate(BADGE_JS, ["living", "bedroom"])
    assert (b2["living"]["on"], b2["bedroom"]["on"]) != (b["living"]["on"], b["bedroom"]["on"])
    assert page.errors == []


OWN = ("smarthome-3d-card.js", "3d/logic.js", "3d/scene.js", "3d/house.js", "3d/furnish.js", "3d/kit.js",
       "3d/devices.js", "3d/assets.js", "3d/model3d.json", "3d/assets/manifest.json")
VENDOR_DESKTOP = ("three.module.min.js", "OrbitControls.js", "CSS2DRenderer.js", "BufferGeometryUtils.js",
                  "RoomEnvironment.js", "GLTFLoader.js", "EffectComposer.js", "RenderPass.js", "GTAOPass.js",
                  "OutputPass.js")


def test_module_urls(page):
    page.add_init_script("performance.setResourceTimingBufferSize(2000)")
    open_card(page)
    names = page.evaluate("performance.getEntriesByType('resource').map((e) => e.name)")
    for f in OWN:
        assert any(n.endswith("/www/smarthome/" + f + "?v=test") for n in names), (f, names)
    vendor = [n for n in names if "/3d/vendor/" in n]
    assert all("?" not in n for n in vendor), vendor
    assert len(vendor) == len(set(vendor)), vendor        # không nạp trùng (một bản three duy nhất)
    files = {n.rsplit("/", 1)[1] for n in vendor}
    assert set(VENDOR_DESKTOP) <= files, files               # máy tính (900 px): có chuỗi GTAO
    assert page.evaluate("window.customCards.some((c) => c.type === 'smarthome-3d-card')")
    assert page.errors == []


def test_status_and_views(page):
    open_card(page)
    bar = page.locator("smarthome-3d-card .bar").inner_text()
    assert "28.5 °C" in bar and "65 %" in bar and "12 %" in bar and "3.2 W" in bar, bar
    page.locator("smarthome-3d-card button[data-view=top]").click()
    # swiftshader vẽ chậm: chờ nội suy 0,8 s xong hẳn thay vì chờ cố định. Tường nâng lần đầu -> SwiftShader
    # dịch JIT đường ống của kính cửa sổ ở lần vẽ đầu (~5 s, chỉ có ở render phần mềm) -> chờ tới 20 s
    page.wait_for_function("!card._tween && !card.loopRunning", timeout=20000)
    pos = page.evaluate("card._camera.position.toArray().map(Math.round)")
    assert pos == [250, 1000, 238], pos
    assert page.evaluate("localStorage.getItem('smarthome3d.view')") == "top"
    assert page.errors == []


def test_no_webgl(page):
    page.add_init_script(NO_WEBGL_JS)
    open_card(page)
    msg = page.locator("smarthome-3d-card .msg")
    assert "Trình duyệt không hỗ trợ WebGL" in msg.inner_text()
    assert msg.is_visible()
    assert page.errors == []


# ---- Task 5 (v2): ghép cảnh mới + gia cố ----

# Trì hoãn tải glTF (fetch) để thấy thanh tải giữa chừng
SLOW_GLTF_JS = """(() => {
  const f = window.fetch.bind(window);
  window.fetch = (u, ...a) => /\\.gltf/.test(String(u && u.url || u))
    ? new Promise((r) => setTimeout(r, 2500)).then(() => f(u, ...a)) : f(u, ...a);
})();"""


def test_loading_overlay(page):
    page.add_init_script(SLOW_GLTF_JS)
    open_card(page, wait=False)
    ov = page.locator("smarthome-3d-card .loading")
    ov.wait_for(state="visible", timeout=10000)
    page.wait_for_function("""() => /Đang tải mô hình… \\d+\\/\\d+/.test(
      card.shadowRoot.querySelector('.loading').textContent)""", timeout=20000)
    page.evaluate("card.ready")
    assert not ov.is_visible()
    assert not page.locator("smarthome-3d-card .note").is_visible()   # không thiếu gì
    assert page.errors == []


def test_assets_missing_note(page):
    page.route("**/assets/manifest.json*", lambda r: r.fulfill(status=404, body="x"))
    open_card(page)
    note = page.locator("smarthome-3d-card .note")
    assert note.is_visible()
    assert "Thiếu 1 tài nguyên, dùng hình đơn giản" in note.inner_text()
    assert not page.locator("smarthome-3d-card .loading").is_visible()
    tap(page, "living")                                              # vẫn dùng được với hình đơn giản
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_den_phong_khach"}]]
    assert [e for e in page.errors if "404" not in e] == []


# PointerEvent tổng hợp gửi thẳng vào .stage (nơi thẻ nghe), không qua canvas của OrbitControls
# ngón tay trên huy hiệu/nhãn (nút DOM) -> bắn vào nút, nổi bọt lên sân khấu như sự kiện thật; còn lại bắn vào sân khấu
# (canvas thì OrbitControls gọi setPointerCapture với id giả -> lỗi)
PTR_JS = """([type, id, x, y, primary]) => {
  const st = card.shadowRoot.querySelector('.stage'), el = card.shadowRoot.elementFromPoint(x, y);
  (el && st.contains(el) && el.closest('[data-slug]') ? el : st).dispatchEvent(new PointerEvent(type, { pointerId: id, pointerType: 'touch', isPrimary: primary,
    clientX: x, clientY: y, bubbles: true, composed: true }));
}"""


def test_two_finger_no_toggle(page):
    open_card(page)
    lx, ly = point(page, "living")
    fx, fy = lx, ly + 70                                     # sàn phòng khách, không có thiết bị
    assert page.evaluate("([x, y]) => card._pick(x, y)", [fx, fy]) is None
    page.evaluate(PTR_JS, ["pointerdown", 11, fx, fy, True])     # ngón 1 trên sàn
    page.evaluate(PTR_JS, ["pointerdown", 12, lx, ly, False])    # ngón 2 trên đèn phòng khách
    page.wait_for_timeout(100)                                    # nhả trong 200 ms
    page.evaluate(PTR_JS, ["pointerup", 12, lx, ly, False])
    page.evaluate(PTR_JS, ["pointerup", 11, fx, fy, True])
    settle(page)
    assert calls(page) == []
    assert more_info(page) == []
    # sau khi nhả hết: chạm một ngón vẫn hoạt động
    page.evaluate(PTR_JS, ["pointerdown", 13, lx, ly, True])
    page.evaluate(PTR_JS, ["pointerup", 13, lx, ly, True])
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_den_phong_khach"}]]
    assert page.errors == []


def test_up_far_no_tap(page):
    # nhả xa điểm nhấn >= 6 px (pointermove bị gộp/mất) -> không phải chạm
    open_card(page)
    lx, ly = point(page, "living")
    page.evaluate(PTR_JS, ["pointerdown", 21, lx, ly, True])
    page.evaluate(PTR_JS, ["pointerup", 21, lx + 20, ly, True])
    settle(page)
    assert calls(page) == []
    assert page.errors == []


def test_call_service_reject_silent(page):
    open_card(page)
    page.evaluate("""() => { const h = fakeHass(fullStates());
      h.callService = (d, s, data) => { calls.push([d, s, data]); return Promise.reject(new Error('HA lỗi')); };
      card.hass = h; }""")
    tap(page, "living")
    settle(page)
    page.wait_for_timeout(100)
    assert len(calls(page)) == 1
    assert page.evaluate("window.sceneError || null") is None
    assert page.errors == []


def test_set_config_demo_resets(page):
    open_card(page, "?demo=1")
    tap(page, "door")
    assert page.evaluate("card.debug('door').vis.door") == 1
    page.evaluate("card.setConfig({ demo: false })")
    assert page.evaluate("card.debug('door').vis.door") == 0     # bỏ ghi đè demo, về trạng thái hass
    tap(page, "living")
    assert calls(page) == [["switch", "toggle", {"entity_id": "switch.smarthome_den_phong_khach"}]]
    assert page.errors == []


def test_cutaway_on_preset(page):
    open_card(page)
    assert front_h(page) == 25                     # Toàn cảnh: tường trước hạ
    page.locator("smarthome-3d-card button[data-view=top]").click()
    page.wait_for_function("!card._tween && !card.loopRunning", timeout=20000)
    assert front_h(page) == 135                    # Từ trên: mọi tường cao đủ
    page.locator("smarthome-3d-card button[data-view=overview]").click()
    page.wait_for_function("!card._tween && !card.loopRunning", timeout=20000)
    assert front_h(page) == 25
    assert page.errors == []


def test_phone_budget(browser, server):
    ctx = browser.new_context(viewport={"width": 390, "height": 780}, has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.add_init_script("window.onCard = (c) => c.ready.then(() => { window.readyAt = performance.now(); });")
        pg.goto(f"{HARNESS}?w=390&h=780")
        pg.wait_for_function("window.card && window.fullStates", timeout=20000)
        pg.evaluate("card.hass = fakeHass(fullStates())")
        pg.wait_for_function("window.readyAt", timeout=30000)
        t = pg.evaluate("window.readyAt")
        assert t <= 15000, t
        assert pg.evaluate("card.mobile") is True
        assert pg.evaluate("card.renderer.getPixelRatio()") <= 1.5
        # một khung thật sau khi sẵn sàng: đếm draw call của cả khung
        pg.evaluate("card._kick()")
        pg.wait_for_function("!card.loopRunning", timeout=15000)
        n = pg.evaluate("card.renderer.info.render.calls")
        assert 0 < n <= 450, n
        assert errors == []
    finally:
        ctx.close()
