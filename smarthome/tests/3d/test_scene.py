"""Kiểm tra scene.js qua harness ?scene=1: dựng nhà + 14 thiết bị, chụp ảnh Ngày/Đêm."""
import base64
import json
import os

from conftest import HARNESS

MODEL = "/config/www/smarthome/3d/model3d.json"
SHOTS = "/tmp/claude-0/-config/664aa28f-0519-40dc-b3ce-1fa22a90129c/scratchpad/shots"
SLUGS = sorted(["door", "buzzer", "pir", "living", "rgb", "porch", "rfid", "ldr", "gas", "gaslvl",
                "flame", "fan", "dht", "bedroom"])
BG = {"day": (0xC4, 0xDA, 0xEC), "night": (0x0B, 0x14, 0x26)}

# Giải mã PNG ngay trong trình duyệt (venv không có PIL): trả tỉ lệ pixel khác nền + độ sáng TB
STATS_JS = """async ([b64, bg]) => {
  const img = new Image();
  img.src = 'data:image/png;base64,' + b64;
  await img.decode();
  const c = document.createElement('canvas');
  c.width = img.width; c.height = img.height;
  const g = c.getContext('2d');
  g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, c.width, c.height).data;
  let diff = 0, lum = 0;
  const n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) {
    const dd = Math.abs(d[i] - bg[0]) + Math.abs(d[i + 1] - bg[1]) + Math.abs(d[i + 2] - bg[2]);
    if (dd > 30) diff++;
    lum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  }
  return { frac: diff / n, lum: lum / n };
}"""


def open_scene(page, theme="day", extra=""):
    page.goto(f"{HARNESS}?scene=1&theme={theme}{extra}")
    page.wait_for_function("window.sceneReady === true || window.sceneError", timeout=60000)
    assert page.evaluate("window.sceneError || null") is None


def test_scene_builds(page):
    open_scene(page)
    info = page.evaluate("window.sceneInfo")
    model = json.load(open(MODEL, encoding="utf-8"))
    assert page.errors == []
    assert info["failed"] == []
    assert info["walls"] == len(model["walls"])
    assert sorted(info["slugs"]) == SLUGS
    r = page.evaluate("""() => ({
      n: house.userData.walls.length,
      flagged: house.userData.walls.every(w => w.mesh.userData.wall === true),
      coords: house.userData.walls.map(w => [w.x1, w.y1, w.x2, w.y2]),
    })""")
    assert r["n"] == len(model["walls"]) and r["flagged"], r
    assert r["coords"] == model["walls"], r


# Chiều cao hiện tại (theo hình thấy được) của từng tường trong model.walls
HEIGHTS_JS = """() => house.userData.walls.map(w => {
  const b = new THREE.Box3();
  w.mesh.updateWorldMatrix(true, true);
  w.mesh.traverseVisible(o => { if (o.isMesh) b.expandByObject(o); });
  return Math.round(b.max.y * 10) / 10;
})"""
# Đặt camera, gọi updateCutaway với dt 1/60 s tới khi trả false; trả số giây đã chạy
SETTLE_JS = """([p, t]) => {
  camera.position.set(...p); camera.lookAt(...t); camera.updateMatrixWorld();
  let steps = 0;
  const first = S.updateCutaway(house, camera, 1 / 60);
  while (S.updateCutaway(house, camera, 1 / 60) && steps < 600) steps++;
  return { first, secs: (steps + 1) / 60 };
}"""


def _walls(model, pred):
    return [i for i, w in enumerate(model["walls"]) if pred(*w)]


def test_cutaway_follows_camera(page):
    open_scene(page)
    model = json.load(open(MODEL, encoding="utf-8"))
    front = _walls(model, lambda x1, y1, x2, y2: y1 == y2 == 0)
    back = _walls(model, lambda x1, y1, x2, y2: y1 == y2 == 355)
    sides = _walls(model, lambda x1, y1, x2, y2: x1 == x2 and x1 in (0, 500))
    # Toàn cảnh (camera phía trước): tường trước thấp, tường sau + hai bên cao đủ
    page.evaluate(SETTLE_JS, [[250, 700, -340], [250, 0, 178]])
    h = page.evaluate(HEIGHTS_JS)
    assert all(h[i] <= 30 for i in front), h
    assert all(h[i] == 135 for i in back + sides), h
    assert all(v in (25, 135) for v in h), h
    # camera phía sau: ngược lại, có hoạt ảnh ~0,25 s
    r = page.evaluate(SETTLE_JS, [[250, 700, 700], [250, 0, 178]])
    assert r["first"] is True and 0.15 <= r["secs"] <= 0.4, r
    h = page.evaluate(HEIGHTS_JS)
    assert all(h[i] <= 30 for i in back), h
    assert all(h[i] == 135 for i in front + sides), h
    assert all(v in (25, 135) for v in h), h
    # nhìn gần như thẳng từ trên xuống: mọi tường cao đủ (đọc như mặt bằng)
    page.evaluate(SETTLE_JS, [[250, 1000, 238], [250, 0, 178]])
    h = page.evaluate(HEIGHTS_JS)
    assert all(v == 135 for v in h), h
    # camera bên trái: tường trái + tường ngăn bếp|ngủ (x = 220) hạ, tường phải cao
    page.evaluate(SETTLE_JS, [[-420, 640, 178], [250, 0, 178]])
    h = page.evaluate(HEIGHTS_JS)
    left = _walls(model, lambda x1, y1, x2, y2: x1 == x2 == 0)
    right = _walls(model, lambda x1, y1, x2, y2: x1 == x2 == 500)
    mid = _walls(model, lambda x1, y1, x2, y2: x1 == x2 == 220)
    assert all(h[i] == 25 for i in left + mid), h
    assert all(h[i] == 135 for i in right), h
    # camera bên phải: tường phải + x = 220 hạ, tường trái cao
    page.evaluate(SETTLE_JS, [[920, 640, 178], [250, 0, 178]])
    h = page.evaluate(HEIGHTS_JS)
    assert all(h[i] == 25 for i in right + mid), h
    assert all(h[i] == 135 for i in left + back + front), h
    # chéo trước-trái: trước, trái, giữa (y = 188), x = 220 hạ; sau + phải cao
    page.evaluate(SETTLE_JS, [[-300, 700, -300], [250, 0, 178]])
    h = page.evaluate(HEIGHTS_JS)
    middle = _walls(model, lambda x1, y1, x2, y2: y1 == y2 == 188)
    assert all(h[i] == 25 for i in front + left + middle + mid), h
    assert all(h[i] == 135 for i in back + right), h
    # đổi camera giữa chừng (đang hạ thì quay ngược): vẫn dừng đúng 25 / 135
    r = page.evaluate("""() => {
      camera.position.set(250, 700, 700); camera.lookAt(250, 0, 178); camera.updateMatrixWorld();
      for (let i = 0; i < 6; i++) S.updateCutaway(house, camera, 1 / 60);
      const mid = house.userData.walls.map(w => w.mesh.userData.h);
      camera.position.set(250, 700, -340); camera.lookAt(250, 0, 178); camera.updateMatrixWorld();
      let n = 0; while (S.updateCutaway(house, camera, 1 / 60) && n < 600) n++;
      return { mid, n };
    }""")
    assert any(25 < v < 135 for v in r["mid"]) and r["n"] < 600, r
    h = page.evaluate(HEIGHTS_JS)
    assert all(h[i] <= 30 for i in front) and all(h[i] == 135 for i in back + sides), h
    assert all(v in (25, 135) for v in h), h
    # đứng yên: gọi lại không chuyển động
    assert page.evaluate("S.updateCutaway(house, camera, 1 / 60)") is False
    assert page.errors == []


def test_cut_wall_ends_closed(page):
    # Tường trước hạ (camera Toàn cảnh): đầu tường bên cạnh (x = 0, x = 500) và đầu tường x = 220
    # (sát tường giữa đã hạ) lộ ra -> phải có mặt đầu tường, không nhìn xuyên qua được.
    open_scene(page, "day", "&nodev=1")
    r = page.evaluate("""() => {
      camera.position.set(250, 700, -340); camera.lookAt(250, 0, 178); camera.updateMatrixWorld();
      for (let i = 0; i < 100 && S.updateCutaway(house, camera, 0.05); i++);
      house.updateMatrixWorld(true);
      const rc = new THREE.Raycaster(), out = {};
      const isWall = (o) => { for (; o; o = o.parent) if (o.userData.wall) return true; return false; };
      for (const x of [0, 500, 220]) {
        rc.set(new THREE.Vector3(x, 80, -100), new THREE.Vector3(0, 0, 1));
        const hit = rc.intersectObject(house, true).find(h => {
          for (let o = h.object; o; o = o.parent) if (!o.visible) return false;
          return true;
        });
        out[x] = hit ? [Math.round(hit.point.z * 10) / 10, isWall(hit.object)] : null;
      }
      return out;
    }""")
    assert r["0"] == [3, True] and r["500"] == [3, True], r
    assert r["220"] == [191, True], r
    assert page.errors == []


def test_furniture_present(page):
    open_scene(page)
    r = page.evaluate("""() => {
      const names = ['sofa', 'bed', 'kitchen', 'tv'];
      const inHouse = Object.fromEntries(names.map(n => [n, !!house.getObjectByName(n)]));
      const f = S.furnish(model, assets);
      const inF = Object.fromEntries(names.map(n => [n, !!f.getObjectByName(n)]));
      // kích thước thật 1:20 (mm mô hình)
      const size = (n) => new THREE.Box3().setFromObject(house.getObjectByName(n)).getSize(new THREE.Vector3());
      const sofa = size('sofa'), bed = size('bed'), tv = house.getObjectByName('tv');
      const panel = tv.getObjectByName('tv_panel');
      const pb = new THREE.Box3().setFromObject(panel);
      return { inHouse, inF, sofaH: sofa.y, bedW: bed.x, bedD: bed.z, panelBottom: pb.min.y,
               panelW: pb.max.x - pb.min.x };
    }""")
    assert all(r["inHouse"].values()) and all(r["inF"].values()), r
    assert 28 <= r["sofaH"] <= 45, r
    assert 110 <= r["bedW"] <= 130 and 95 <= r["bedD"] <= 125, r
    assert 30 <= r["panelBottom"] <= 50 and 60 <= r["panelW"] <= 85, r
    assert page.errors == []


# Ảnh xem thử bản 2 (Ngày; ánh sáng do applyTheme)
V2_SHOTS = {"v2_living": "&cam=living", "v2_bed": "&cam=bed", "v2_kitchen": "&cam=kitchen",
            "v2_top": "&cam=top"}


def test_screenshot_v2(page):
    os.makedirs(SHOTS, exist_ok=True)
    for name, q in V2_SHOTS.items():
        open_scene(page, "day", q)
        png = page.locator("#scene").screenshot(path=f"{SHOTS}/{name}.png")
        st = page.evaluate(STATS_JS, [base64.b64encode(png).decode(), list(BG["day"])])
        assert st["frac"] > 0.5, (name, st)
        assert page.errors == []


def test_screenshot_day_night(page):
    os.makedirs(SHOTS, exist_ok=True)
    stats = {}
    for theme in ("day", "night"):
        open_scene(page, theme)
        png = page.locator("#scene").screenshot(path=f"{SHOTS}/{theme}.png")
        stats[theme] = page.evaluate(STATS_JS, [base64.b64encode(png).decode(), list(BG[theme])])
        assert page.errors == []
    assert stats["day"]["frac"] > 0.2, stats
    assert stats["night"]["frac"] > 0.2, stats
    assert stats["night"]["lum"] < stats["day"]["lum"], stats


def test_theme_switch_and_animation(page):
    open_scene(page)
    r = page.evaluate("""() => {
      const count = () => { let n = 0; scene.traverse(() => n++); return n; };
      const n0 = count();
      S.applyTheme(scene, 'night'); const n1 = count();
      S.applyTheme(scene, 'day'); S.applyTheme(scene, 'night'); const n2 = count();
      S.applyTheme(scene, 'day');
      // cửa đang mở -> đóng: xoay hết ~1,2 s
      const v = { unavailable: false, on: false, color: null, brightness: 0, door: 0, moving: true, text: null };
      devs.door.update(v);
      let t = 0; while (devs.door.tick(0.05) && t < 5) t += 0.05;
      const doorStill = devs.door.tick(0.05);
      // RFID chớp 1,5 s khi giá trị đổi
      devs.rfid.update({ ...v, door: 0, moving: false, text: 'NEW-CARD' });
      let tr = 0; while (devs.rfid.tick(0.05) && tr < 5) tr += 0.05;
      // mọi mesh của thiết bị mang slug
      const badSlug = Object.entries(devs).filter(([s, d]) => {
        let bad = false; d.object.traverse(o => { if (o.isMesh && o.userData.slug !== s) bad = true; }); return bad;
      }).map(([s]) => s);
      return { n0, n1, n2, t, doorStill, tr, fan: devs.fan.tick(0.05), lamp: devs.living.tick(0.05), badSlug,
               bg: scene.background.name };
    }""")
    assert r["n0"] == r["n1"] == r["n2"], r
    assert 1.0 <= r["t"] <= 1.3 and r["doorStill"] is False, r
    assert 1.3 <= r["tr"] <= 1.6, r
    assert r["fan"] is True and r["lamp"] is False, r
    assert r["badSlug"] == [] and r["bg"] == "sky_day", r
    assert page.errors == []


def test_rfid_flash_only_on_real_change(page):
    open_scene(page)
    r = page.evaluate("""async () => {
      const L = await import('/www/smarthome/3d/logic.js');
      const d = S.createDevice('rfid', L.KINDS.rfid, { x: 128, y: -12 }, null);
      const step = (state) => { d.update(L.visualState('rfid', [{ state, attributes: {} }])); return d.tick(0.05); };
      return {
        first: step('12-34-56-78'),        // lần đầu: chỉ ghi nhớ
        unavailable: step('unavailable'),
        unknown: step('unknown'),
        back: step('12-34-56-78'),         // unknown -> id cũ: không chớp
        empty: step(''),
        change: step('AA-BB-CC-DD'),       // id đổi thật: chớp
      };
    }""")
    assert r == {"first": False, "unavailable": False, "unknown": False, "back": False,
                 "empty": False, "change": True}, r
    assert page.errors == []


# ---------------- Bản 2: thiết bị thật + Ngày/Đêm thật ----------------

ALL_OFF = "&off=living,bedroom,porch,rgb"
# Độ sáng (0..1, luma sRGB) trong hình chữ nhật màn hình bao hộp sàn [x0,x1]×[z0,z1] cao 0..60
REGION_JS = """([x0, x1, z0, z1, y0 = 0, y1 = 60]) => {
  redraw();
  const cv = renderer.domElement, W = cv.width, H = cv.height;
  let a = [W, H], b = [0, 0];
  for (const x of [x0, x1]) for (const z of [z0, z1]) for (const y of [y0, y1]) {
    const p = new THREE.Vector3(x, y, z).project(camera);
    const sx = (p.x + 1) / 2 * W, sy = (1 - p.y) / 2 * H;
    a = [Math.min(a[0], sx), Math.min(a[1], sy)]; b = [Math.max(b[0], sx), Math.max(b[1], sy)];
  }
  const X0 = Math.max(0, Math.floor(a[0])), Y0 = Math.max(0, Math.floor(a[1]));
  const X1 = Math.min(W, Math.ceil(b[0])), Y1 = Math.min(H, Math.ceil(b[1]));
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d'); g.drawImage(cv, 0, 0);
  const d = g.getImageData(X0, Y0, X1 - X0, Y1 - Y0).data;
  let s = 0, s2 = 0, clip = 0, r = 0, bl = 0; const n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) {
    const l = (0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]) / 255;
    s += l; s2 += l * l; r += d[i]; bl += d[i + 2];
    if (Math.max(d[i], d[i + 1], d[i + 2]) >= 250) clip++;
  }
  const mean = s / n;
  return { mean, std: Math.sqrt(Math.max(0, s2 / n - mean * mean)), rect: [X0, Y0, X1, Y1], clip: clip / n,
           rb: r / Math.max(1, bl) };
}"""
LIVING = [0, 500, 0, 188]
HOUSE = [0, 500, 0, 355]
BEDROOM = [220, 500, 188, 355]
KITCHEN = [0, 220, 188, 355]
BED_FLOOR = [226, 494, 240, 349, 0, 0]   # chỉ mặt sàn phòng ngủ, phần không bị lưng sofa/tường giữa che trên ảnh
SOFA_WALL = [345, 455, 150, 188, 0, 135]   # sofa + vách phía trên sofa (thanh LED RGB; vách hạ -> thanh ngồi thấp)
PROGS_JS = "() => { redraw(); return renderer.info.programs.length; }"
ON = ("{ unavailable: false, on: true, color: null, brightness: 1, door: 0, moving: false, text: null }")
OFF = ("{ unavailable: false, on: false, color: null, brightness: 0, door: 0, moving: false, text: null }")
GLASS_JS = "() => house.userData.windows.map(w => w.mesh.material.emissiveIntensity)"
LIGHTS_JS = """() => {
  const out = [];
  scene.traverse(o => { if (o.isLight) out.push({ type: o.type, shadow: !!o.castShadow, i: o.intensity,
    slug: o.userData.slug || null, map: o.shadow ? o.shadow.mapSize.x : 0 }); });
  return out;
}"""
# mesh có hiện thật không (mọi tổ tiên visible)
SHOWN_JS = """(slug) => {
  const o = devs[slug].object; let any = false;
  o.traverse(m => {
    if (!m.isMesh || m.userData.fx) return;
    for (let p = m; p; p = p.parent) if (!p.visible) return;
    any = true;
  });
  return any;
}"""


def test_lamp_lights_room(page):
    # Đêm, mọi đèn tắt -> bật đèn phòng khách: vùng phòng khách sáng hơn ≥ 15 %, ánh sáng ấm
    open_scene(page, "night", ALL_OFF)
    n0 = len(page.evaluate(LIGHTS_JS))
    off = page.evaluate(REGION_JS, LIVING)
    glass0 = page.evaluate(GLASS_JS)
    page.evaluate(f"() => devs.living.update({ON})")
    on = page.evaluate(REGION_JS, LIVING)
    glass1 = page.evaluate(GLASS_JS)
    lights = page.evaluate(LIGHTS_JS)
    assert on["mean"] >= off["mean"] * 1.15, (off, on)
    # ánh sáng ấm (R/B tăng)
    assert on["rb"] > off["rb"] * 1.05, (off, on)
    # cửa sổ phòng khách phát sáng ban đêm khi bật đèn, tắt khi sang Ngày
    assert glass0 == [0] and glass1[0] > 1, (glass0, glass1)
    assert page.evaluate("() => { S.applyTheme(scene, 'day'); const g = house.userData.windows[0].mesh.material.emissiveIntensity;"
                         " S.applyTheme(scene, 'night'); return g; }") == 0
    # bật/tắt đèn (sau một lượt làm nóng) không biên dịch lại shader
    for slug in ("living", "bedroom", "porch"):
        page.evaluate(f"() => devs.{slug}.update({OFF})"); page.evaluate(PROGS_JS)
        page.evaluate(f"() => devs.{slug}.update({ON})"); page.evaluate(PROGS_JS)
    p0 = page.evaluate(PROGS_JS)
    for slug in ("living", "bedroom", "porch", "living"):
        page.evaluate(f"() => devs.{slug}.update({OFF})")
        assert page.evaluate(PROGS_JS) == p0, slug
        page.evaluate(f"() => devs.{slug}.update({ON})")
        assert page.evaluate(PROGS_JS) == p0, slug
    assert page.evaluate("() => devs.living.object.getObjectsByProperty('isPointLight', true)[0].color.getHexString()") == "ffb46b"
    # không tràn sang phòng ngủ đang tắt: Toàn cảnh (tường hạ), chỉ vùng sàn phòng ngủ
    page.evaluate(f"() => {{ devs.living.update({OFF}); devs.bedroom.update({OFF}); devs.porch.update({OFF}); }}")
    bed0 = page.evaluate(REGION_JS, BED_FLOOR)
    page.evaluate(f"() => devs.living.update({ON})")
    bed1 = page.evaluate(REGION_JS, BED_FLOOR)
    assert bed1["mean"] < bed0["mean"] * 1.03, (bed0, bed1)
    # đèn luôn có sẵn (không đổi số đèn -> không biên dịch lại shader)
    assert len(lights) == n0, lights
    lamp = [x for x in lights if x["slug"] == "living" and x["type"] == "PointLight"]
    assert len(lamp) == 1 and lamp[0]["i"] > 0, lights
    assert page.errors == []


def test_night_readable(page):
    # Đêm, mọi đèn tắt: vẫn nhìn rõ nhà (đủ sáng + có tương phản), tường đặc
    open_scene(page, "night", ALL_OFF)
    st = page.evaluate(REGION_JS, HOUSE)
    assert st["mean"] >= 0.12 and st["std"] >= 0.04, st
    r = page.evaluate("""() => {
      const bad = [];
      house.traverse(o => {
        if (!o.isMesh) return;
        let w = false; for (let p = o; p; p = p.parent) if (p.userData.wall) w = true;
        if (w && (o.material.transparent || o.material.opacity < 1)) bad.push(o.material.name);
      });
      return { bad, bg: '#' + scene.background.getHexString(), env: scene.environmentIntensity,
               hasEnv: !!scene.environment };
    }""")
    assert r["bad"] == [] and r["bg"] == "#0b1426", r
    assert r["hasEnv"] and 0.1 <= r["env"] <= 0.3, r
    assert page.errors == []


def test_no_neon(page):
    open_scene(page, "night")
    for theme in ("night", "day", "night"):
        r = page.evaluate("""(th) => {
          S.applyTheme(scene, th);
          const bad = [];
          scene.traverse(o => {
            if (o.userData.nightOnly) bad.push('nightOnly:' + o.name);
            if (o.geometry && o.geometry.type === 'EdgesGeometry') bad.push('edges:' + o.name);
            if (o.isLineSegments || o.isSprite) bad.push(o.type + ':' + o.name);
          });
          return bad;
        }""", theme)
        assert r == [], (theme, r)
    assert page.errors == []


def test_renderer_and_lights(page):
    # Ngày: môi trường PMREM, nắng có bóng; ngân sách đèn; máy tính bóng 2048
    open_scene(page, "day")
    r = page.evaluate("""() => ({
      tm: renderer.toneMapping, ok: [THREE.ACESFilmicToneMapping, THREE.AgXToneMapping],
      cs: renderer.outputColorSpace, sm: renderer.shadowMap.enabled, st: renderer.shadowMap.type,
      pcf: THREE.PCFSoftShadowMap, env: scene.environmentIntensity, hasEnv: !!scene.environment,
    })""")
    assert r["tm"] in r["ok"] and r["cs"] == "srgb" and r["sm"] and r["st"] == r["pcf"], r
    assert r["hasEnv"] and 0.6 <= r["env"] <= 1.0, r
    lights = page.evaluate(LIGHTS_JS)
    dirs = [x for x in lights if x["type"] == "DirectionalLight"]
    assert len(dirs) == 1 and dirs[0]["shadow"] and dirs[0]["map"] == 2048, lights
    assert len([x for x in lights if x["type"] == "PointLight"]) <= 6, lights
    assert len([x for x in lights if x["type"] == "SpotLight" and x["shadow"]]) <= 1, lights
    porch = [x for x in lights if x["slug"] == "porch"]
    assert len(porch) == 1 and porch[0]["type"] == "SpotLight" and porch[0]["i"] > 0, lights
    day = page.evaluate("() => { const s = scene.userData.lights.sun; return [s.intensity, s.color.r, s.color.b]; }")
    page.evaluate("S.applyTheme(scene, 'night')")
    moon = page.evaluate("() => { const s = scene.userData.lights.sun; return [s.intensity, s.color.r, s.color.b]; }")
    assert moon[0] < day[0] * 0.5 and moon[2] > moon[1] and day[1] > day[2], (day, moon)
    # điện thoại: bóng 1024, không đèn điểm/đèn rọi nào có bóng
    open_scene(page, "day", "&mobile=1")
    lights = page.evaluate(LIGHTS_JS)
    dirs = [x for x in lights if x["type"] == "DirectionalLight"]
    assert len(dirs) == 1 and dirs[0]["map"] == 1024, lights
    assert not any(x["shadow"] for x in lights if x["type"] != "DirectionalLight"), lights
    assert len([x for x in lights if x["type"] == "PointLight"]) <= 6, lights
    assert page.errors == []


def test_devices_realistic(page):
    # Cỡ thật 1:20, độ cao lắp = KINDS.z × 1,5; mọi mesh mang slug; mesh hiệu ứng tắt raycast
    open_scene(page, "day")
    r = page.evaluate("""() => {
      // nhìn từ trên: mọi tường cao đủ -> thiết bị gắn tường ở đúng chỗ lắp (không trượt theo tường hạ)
      camera.position.set(250, 1000, 238); camera.lookAt(250, 0, 178); camera.updateMatrixWorld();
      for (let i = 0; i < 100 && S.updateCutaway(scene, camera, 0.05); i++);
      const box = (s, pred) => {
        const b = new THREE.Box3();
        devs[s].object.updateWorldMatrix(true, true);
        devs[s].object.traverse(o => { if (o.isMesh && !o.userData.fx && (!pred || pred(o))) b.expandByObject(o); });
        const z = b.getSize(new THREE.Vector3()), c = b.getCenter(new THREE.Vector3());
        return { size: [z.x, z.y, z.z].map(v => Math.round(v * 10) / 10), c: [c.x, c.y, c.z].map(v => Math.round(v)) };
      };
      const out = {};
      for (const s of Object.keys(devs)) out[s] = box(s);
      let rayBad = [];
      for (const [s, d] of Object.entries(devs)) d.object.traverse(o => {
        if (o.isMesh && o.userData.fx && o.raycast === THREE.Mesh.prototype.raycast) rayBad.push(s);
      });
      return { out, rayBad };
    }""")
    o = r["out"]
    assert r["rayBad"] == [], r
    # đèn ốp trần sát mặt trần (125..135)
    for s in ("living", "bedroom"):
        assert 125 <= o[s]["c"][1] <= 135 and max(o[s]["size"]) <= 30, (s, o[s])
    # thiết bị gắn tường phóng to cho dễ nhìn (kèm viền vòng sáng): cảm biến 14..26 mm mô hình, không chạm đỉnh
    # tường 135; độ cao lắp KINDS.z × 1,5
    for s, z in (("pir", 120), ("gas", 90), ("flame", 60), ("ldr", 112.5), ("rfid", 67.5)):
        assert 20 <= max(o[s]["size"]) <= 34, (s, o[s])
        assert abs(o[s]["c"][1] - z) <= 8 and o[s]["c"][1] + o[s]["size"][1] / 2 <= 134.5, (s, o[s])
    # quạt hút: khung 36..44 mm, cửa gỗ cao gần bằng ô cửa 105
    assert 36 <= max(o["fan"]["size"]) <= 44 and abs(o["fan"]["c"][1] - 112.5) <= 8, o["fan"]
    assert o["fan"]["c"][1] + o["fan"]["size"][1] / 2 <= 134.5, o["fan"]
    # LED RGB: thanh dài trên vách giữa (y = 188, mặt phòng khách), phía trên sofa (x 340..460), cao ~85
    assert 360 <= o["rgb"]["c"][0] <= 440 and 178 <= o["rgb"]["c"][2] <= 188 and abs(o["rgb"]["c"][1] - 85) <= 8, o["rgb"]
    assert o["rgb"]["size"][0] >= 50, o["rgb"]
    assert 100 <= o["door"]["size"][1] <= 106, o["door"]
    assert page.errors == []


def test_device_rings(page):
    # thiết bị gắn tường có viền vòng sáng trên tường: tắt = xanh dịu, bật = màu trạng thái (sáng hơn), nhận chạm
    open_scene(page, "night", ALL_OFF)
    r = page.evaluate("""() => {
      const ring = (s) => devs[s].object.getObjectsByProperty('name', 'dev_ring')[0];
      const look = (s) => { const m = ring(s); return m ? { c: m.material.emissive.getHexString(), i: m.material.emissiveIntensity,
        slug: m.userData.slug, ray: m.raycast === THREE.Mesh.prototype.raycast } : null; };
      const slugs = ['fan', 'pir', 'gas', 'flame', 'ldr', 'rfid', 'buzzer', 'porch'];
      const st = (on) => ({ unavailable: false, on, color: null, brightness: on ? 1 : 0, door: 0, moving: false, text: null });
      for (const s of slugs) if (s !== 'rfid') devs[s].update(st(false));
      const off = Object.fromEntries(slugs.map((s) => [s, look(s)]));
      devs.fan.update(st(true));
      return { off, fanOn: look('fan'), lamp: ring('living') || null };
    }""")
    for s, v in r["off"].items():
        assert v and v["slug"] == s and v["ray"], (s, v)
        assert v["c"] == r["off"]["fan"]["c"], (s, v)          # cùng màu chờ
    assert r["fanOn"]["c"] != r["off"]["fan"]["c"] and r["fanOn"]["i"] > r["off"]["fan"]["i"], r
    assert r["lamp"] is None, r                                 # đèn trần không có viền tường
    assert page.errors == []


def test_devices_follow_cut_walls(page):
    # Tường hạ -> thiết bị gắn trên đó KHÔNG ẩn mà trượt xuống ngồi trên mép tường (đáy = mép + 1); thiết bị gắn
    # trên ô cửa (đèn hiên) dừng ở đỉnh cánh cửa (cửa không hạ) và vẫn rọi
    open_scene(page, "night")
    r = page.evaluate("""(js) => {
      const shown = eval(js);
      const bottom = (s) => { devs[s].object.updateWorldMatrix(true, true); const b = new THREE.Box3();
        devs[s].object.traverse(o => { if (o.isMesh && !o.userData.fx) b.expandByObject(o); }); return Math.round(b.min.y); };
      const spot = devs.porch.object.getObjectsByProperty('isSpotLight', true)[0];
      const all = ['porch', 'rfid', 'ldr', 'door', 'fan', 'pir', 'rgb', 'dht'];
      const a = Object.fromEntries(all.map((s) => [s, shown(s)]));
      a.spot = !!spot && spot.visible && spot.intensity > 0;
      const ba = { rfid: bottom('rfid'), ldr: bottom('ldr'), porch: bottom('porch'), rgb: bottom('rgb') };
      camera.position.set(250, 700, 700); camera.lookAt(250, 0, 178); camera.updateMatrixWorld();
      for (let i = 0; i < 100 && S.updateCutaway(scene, camera, 0.05); i++);
      const b = Object.fromEntries(all.map((s) => [s, shown(s)]));
      const bb = { rfid: bottom('rfid'), dht: bottom('dht') };
      return { a, ba, b, bb };
    }""", SHOWN_JS)
    assert all(r["a"].values()) and all(r["b"].values()), r
    # Toàn cảnh: tường trước (RFID, quang trở) hạ xuống 25; vách giữa cũng hạ nhưng thanh LED RGB dừng trên lưng
    # sofa (cao 35) để không bị sofa che
    assert 25 <= r["ba"]["rfid"] <= 28 and 25 <= r["ba"]["ldr"] <= 28 and 36 <= r["ba"]["rgb"] <= 42, r
    assert r["ba"]["porch"] >= 105, r
    # nhìn từ sau nhà: tường trước cao lại -> RFID về chỗ lắp; tường sau hạ -> DHT ngồi trên mép
    assert r["bb"]["rfid"] >= 50 and 25 <= r["bb"]["dht"] <= 28, r
    assert page.errors == []


# Ảnh bản 2 có thiết bị + ánh sáng thật: tên -> (theme, query)
V2_LIGHT_SHOTS = {
    "v2_day": ("day", ""),
    "v2_night": ("night", ALL_OFF),
    "v2_night_lamps": ("night", "&off=fan&rgb=150,60,255"),
    "v2_alarm": ("night", "&on=gas,buzzer&off=living,bedroom,rgb&t=0.6"),
    "v2_door": ("day", "&cam=door&off=door"),
    "v2_fan": ("day", "&cam=fan&t=0.3"),
    "v2_fan_night": ("night", "&cam=fan&off=rgb&t=0.3"),
}


def test_screenshot_v2_lighting(page):
    os.makedirs(SHOTS, exist_ok=True)
    for name, (theme, q) in V2_LIGHT_SHOTS.items():
        open_scene(page, theme, q)
        png = page.locator("#scene").screenshot(path=f"{SHOTS}/{name}.png")
        st = page.evaluate(STATS_JS, [base64.b64encode(png).decode(), list(BG[theme])])
        assert st["frac"] > 0.5, (name, st)
        assert page.errors == []


def test_rgb_soft_glow(page):
    # Thanh LED trên vách đầu sofa: quầng màu dịu trên tường, không cháy sáng. Điểm ảnh cháy DO RGB (bật trừ tắt)
    # ≤ 0,2 % vùng sofa + vách, ở Toàn cảnh / phòng khách / bên trái, Ngày đỏ và Đêm tím
    for theme, rgb in (("day", ""), ("night", "&rgb=150,60,255")):
        for cam in ("", "&cam=living", "&cam=left"):
            clip = {}
            for state in ("on", "off"):
                open_scene(page, theme, rgb + cam + ("&off=rgb" if state == "off" else ""))
                clip[state] = page.evaluate(REGION_JS, SOFA_WALL)["clip"]
            assert clip["on"] - clip["off"] <= 0.002, (theme, cam, clip)
    r = page.evaluate("() => { const l = devs.rgb.object.getObjectsByProperty('isPointLight', true)[0];"
                      " return [l.intensity, l.distance, l.getWorldPosition(new THREE.Vector3()).z]; }")
    assert r[1] <= 100 and 170 <= r[2] <= 188 - 3 - 4, r   # sát trước mặt vách (185), trong phòng khách
    assert page.errors == []


def test_unavailable_state(page):
    # Không khả dụng: mọi mesh (trừ hiệu ứng) xám + ⚠; có lại -> vật liệu cũ
    open_scene(page, "day", "&na=living,door,fan")
    r = page.evaluate("""() => {
      const look = (s) => {
        const names = new Set(); let warn = false;
        devs[s].object.traverse(o => {
          if (o.isMesh && !o.userData.fx && !o.userData.keepMat) names.add(o.material.name);
          if (o.isCSS2DObject && o.element.textContent === '⚠') warn = o.visible;
        });
        return { names: [...names], warn };
      };
      const na = { living: look('living'), door: look('door'), fan: look('fan') };
      devs.living.update({ unavailable: false, on: false, color: null, brightness: 0, door: 0, moving: false, text: null });
      return { na, back: look('living') };
    }""")
    for s in ("living", "door", "fan"):
        assert r["na"][s] == {"names": ["dev_unavailable"], "warn": True}, (s, r)
    assert "dev_unavailable" not in r["back"]["names"] and r["back"]["warn"] is False, r
    assert page.errors == []


def test_alarm_glow(page):
    # Báo gas: bếp đỏ lên, phòng ngủ gần như không đổi; tắt hết -> đèn đỏ 0; còi: tia quét đổi hướng
    open_scene(page, "night", ALL_OFF)
    k0 = page.evaluate(REGION_JS, KITCHEN)
    b0 = page.evaluate(REGION_JS, BEDROOM)
    page.evaluate("() => S.alarmGlow(scene, model.rooms, true, 0.21, 'kitchen')")
    k1 = page.evaluate(REGION_JS, KITCHEN)
    b1 = page.evaluate(REGION_JS, BEDROOM)
    assert k1["rb"] > k0["rb"] * 1.1, (k0, k1)
    assert abs(b1["rb"] - b0["rb"]) < b0["rb"] * 0.05, (b0, b1)
    r = page.evaluate("""() => {
      S.alarmGlow(scene, model.rooms, true, 0.21, 'house');
      const h = scene.getObjectByName('alarm').intensity;
      S.alarmGlow(scene, model.rooms, false, 0.3, 'house'); S.alarmGlow(scene, model.rooms, false, 0.3, 'kitchen');
      const z = scene.getObjectByName('alarm').intensity;
      const sp = devs.buzzer.object.getObjectsByProperty('isSpotLight', true)[0];
      const v = { unavailable: false, on: true, color: null, brightness: 1, door: 0, moving: false, text: null };
      devs.buzzer.update(v); devs.buzzer.tick(0.05); const a = sp.target.position.clone();
      devs.buzzer.tick(0.1); const b = sp.target.position.clone();
      const iOn = sp.intensity;
      devs.buzzer.update({ ...v, on: false }); 
      return { h, z, moved: a.distanceTo(b), iOn, iOff: sp.intensity };
    }""")
    assert r["h"] > 0 and r["z"] == 0 and r["moved"] > 1 and r["iOn"] > 0 and r["iOff"] == 0, r
    assert page.errors == []


def test_porch_lights_path(page):
    open_scene(page, "night", ALL_OFF)
    path = [40, 110, -80, -5, -8, -7]
    off = page.evaluate(REGION_JS, path)
    page.evaluate(f"() => devs.porch.update({ON})")
    on = page.evaluate(REGION_JS, path)
    assert on["mean"] >= off["mean"] * 1.3, (off, on)
    assert page.errors == []
