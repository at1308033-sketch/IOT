# Trang "Mô hình 3D" — kế hoạch thực hiện

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thẻ Lovelace `smarthome-3d-card` vẽ ngôi nhà 3D (cắt nóc, chế độ Ngày/Đêm/Tự động), thao tác thiết bị giống mặt bằng 2D, đặt trên trang mới `mo-hinh-3d` của dashboard `smarthome-doan`.

**Architecture:** `build_dashboard.py` xuất hình học nhà + vị trí thiết bị (mm) ra `model3d.json`. Thẻ JS (three.js r170 chép về máy) đọc file đó, dựng cảnh bằng `3d/scene.js`, quy trạng thái HA thành hình ảnh bằng hàm thuần trong `3d/logic.js`. `tools/push_3d.py` đăng ký resource qua websocket và thêm/thay đúng trang 3D.

**Tech Stack:** three.js 0.170.0 (`three.module.min.js`, `OrbitControls`, `CSS2DRenderer`), ES module trình duyệt, Python 3.13 + PyYAML (có sẵn), `node --test` cho logic, Playwright Chromium headless (SwiftShader WebGL) cho test hiển thị/tương tác.

**Spec:** `/config/smarthome/docs/2026-10-19-dashboard-3d-design.md`

## Global Constraints
- Chỉ ngôi nhà và thiết bị nhìn thấy; KHÔNG vẽ ESP32, relay, dây, mạch.
- 1 đơn vị three.js = 1 mm. Nhà 500 × 355, vách giữa y = 188, vách bếp|ngủ x = 220, tường cao 90, không mái. Trục: mặt bằng (x, y) → three (x, 0, y), cao = trục Y.
- Không chạy `push_dashboard.py --full`; luôn `push_dashboard.py --pull` trước khi build (memory dự án). 4 trang cũ giữ nguyên.
- Không sửa `configuration.yaml`, không khởi động lại HA.
- Chữ hiển thị tiếng Việt có dấu.
- Còi: chạm = more-info (không toggle), giữ quy ước bản 2D.
- Lựa chọn chế độ/góc nhìn chỉ lưu `localStorage`, bọc try/catch.
- Không có git: trước khi sửa file cũ, sao lưu `<file>.bak-20261019`. Không có bước commit.
- File vendor three.js không bao giờ mang `?v=`; file của mình (`logic.js`, `scene.js`, `model3d.json`) được thẻ nạp kèm `?v=` lấy từ `import.meta.url` của thẻ.

## Review Focus
1. `hass` được gán trước khi `model3d.json`/three.js nạp xong → khi cảnh sẵn sàng phải áp ngay trạng thái mới nhất (test ở Task 5: `hass_before_ready`).
2. Chuyển trang HA rồi quay lại (thẻ bị tháo khỏi DOM rồi gắn lại) → vẫn vẽ, không nhân đôi vòng lặp, không rò WebGL context (Task 5: `reconnect`).
3. Kéo để xoay camera mà nhả chuột trên một thiết bị → KHÔNG được bật/tắt (Task 5: `drag_no_toggle`).
4. Đèn RGB `on` nhưng thiếu `rgb_color`/`brightness` (hiệu ứng "Nháy đỏ") → dùng trắng, độ sáng 1, không lỗi (Task 3: `rgb fallback`).
5. Đổi kích thước thẻ (thu sidebar, xoay điện thoại) → canvas theo kích thước mới (Task 5: `resize`).

---

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `/config/www/smarthome/3d/vendor/three.module.min.js` | three r170 (nguyên bản) |
| `/config/www/smarthome/3d/vendor/OrbitControls.js`, `CSS2DRenderer.js` | addon r170, sửa `from 'three'` → `from './three.module.min.js'` |
| `/config/www/smarthome/3d/model3d.json` | sinh bởi `build_dashboard.py`: hình học + thiết bị |
| `/config/www/smarthome/3d/logic.js` | hàm thuần: trạng thái HA → hình ảnh, lệnh chạm, chủ đề, demo |
| `/config/www/smarthome/3d/scene.js` | dựng nhà + vật thể thiết bị, áp hình ảnh, hoạt ảnh |
| `/config/www/smarthome/smarthome-3d-card.js` | custom element: renderer, camera, chạm/giữ, giao diện phủ |
| `/config/smarthome/dashboard_3d.yaml` | trang `mo-hinh-3d` |
| `/config/smarthome/tools/build_dashboard.py` | + ghi `model3d.json`, + chèn trang 3D vào `dashboard.yaml` |
| `/config/smarthome/tools/push_3d.py` | resource + thêm/thay trang 3D |
| `/config/smarthome/tests/3d/` | `logic.test.mjs`, `test_model3d.py`, `harness.html`, `test_card.py` |

---

### Task 1: Công cụ test + vendor three.js

**Files:**
- Create: `/config/www/smarthome/3d/vendor/{three.module.min.js,OrbitControls.js,CSS2DRenderer.js}`
- Create: `/config/smarthome/tests/3d/harness.html`, `/config/smarthome/tests/3d/conftest.py`, `/config/smarthome/tests/3d/test_vendor.py`

**Interfaces:**
- Produces: venv `$SP/venv` (SP = scratchpad) có `pytest`, `playwright` + Chromium; `node`. Fixture pytest `page` (Chromium args `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`), fixture `server` = `python -m http.server 8765` gốc `/config` (harness ở `http://127.0.0.1:8765/smarthome/tests/3d/harness.html`, thẻ ở `/www/smarthome/...`). Fixture `page` gom `console` lỗi + `pageerror` vào `page.errors`.
- Produces: `harness.html?demo=0|1` tạo `<smarthome-3d-card>` 900×600, `window.fakeHass(states)` dựng `hass = {states, callService(d,s,data){window.calls.push([d,s,data])}, language:'vi'}`, `window.calls=[]`, `window.moreInfo=[]` (nghe `hass-more-info` trên `document`), `window.card`.

- [ ] **Step 1:** `apt-get install -y nodejs`; `python3 -m venv $SP/venv && $SP/venv/bin/pip install pytest playwright && $SP/venv/bin/playwright install --with-deps chromium`. Kiểm tra: `node --version` ≥ 18, `$SP/venv/bin/python -c "import playwright"` thành công.
- [ ] **Step 2:** Tải 3 file từ `https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.min.js` và `.../examples/jsm/{controls/OrbitControls.js,renderers/CSS2DRenderer.js}`; thay `from 'three'` bằng `from './three.module.min.js'`. Kiểm tra: `grep -c "from 'three'"` = 0 ở cả hai addon.
- [ ] **Step 3: test thất bại** `test_vendor.py::test_three_loads` — trang harness tối giản `evaluate` `import('/www/smarthome/3d/vendor/OrbitControls.js')` và `import('/www/smarthome/3d/vendor/three.module.min.js')`, assert `REVISION === '170'`, `typeof OrbitControls === 'function'`, tạo `WebGLRenderer` không ném lỗi, `page.errors == []`. Chạy trước khi tải file → FAIL (404).
- [ ] **Step 4:** Chạy `$SP/venv/bin/pytest /config/smarthome/tests/3d/test_vendor.py -v` → PASS.

---

### Task 2: `model3d.json` + trang `mo-hinh-3d` trong build

**Files:**
- Modify: `/config/smarthome/tools/build_dashboard.py` (sau khối SVG và cuối file nơi chèn trang Điều khiển, dòng ~488)
- Create: `/config/smarthome/dashboard_3d.yaml`
- Test: `/config/smarthome/tests/3d/test_model3d.py`

**Interfaces:**
- Produces `model3d.json` (UTF-8, `ensure_ascii=False`):
  ```
  {"house":{"w":500,"d":355,"wall_h":90,"wall_t":6},
   "walls":[[x1,y1,x2,y2],...],            # đúng danh sách `walls` của build_dashboard
   "rooms":[{"name":"PHÒNG KHÁCH","x":0,"y":0,"w":500,"d":188,"color":"#f1f6ee"},...],
   "window":{"x1":201,"x2":321,"y":0,"sill":30,"top":70},
   "doors":[{"x_free":45,"x_hinge":105,"y":0,"main":true},{"x_free":55,"x_hinge":105,"y":188},{"x_free":235,"x_hinge":285,"y":188}],
   "furniture":[{"kind":"tv"|"sofa"|"bed"|"stove","x":..,"y":..,"w":..,"d":..},...],  # từ các hình chữ nhật nội thất SVG
   "devices":{"<slug>":{"entity":..,"x":..,"y":..,"tap":"toggle"|"more-info","title":..},...}}
  ```
  `devices` lấy từ `DEV` đã áp `positions.json`; `title` = cột tên của `DEV` (chuỗi "Tên · chân") cắt phần trước " · " đầu tiên. Bỏ chân/relay khỏi `title` (Global Constraints).
- `dashboard_3d.yaml`: `title: Mô hình 3D`, `path: mo-hinh-3d`, `icon: mdi:cube-outline`, `type: panel`, một thẻ `type: custom:smarthome-3d-card`. `build_dashboard.py` chèn trang này ngay sau trang Điều khiển (index 2).

- [ ] **Step 1:** Sao lưu `build_dashboard.py.bak-20261019`.
- [ ] **Step 2: test thất bại** `test_model3d.py` (chạy `build_dashboard.py` bằng subprocess, rồi đọc file):
  - `test_house_dims`: `house == {"w":500,"d":355,"wall_h":90,"wall_t":6}`, `len(rooms)==3`, `len(doors)==3`.
  - `test_devices_complete`: tập slug == `{"door","buzzer","pir","living","rgb","porch","rfid","ldr","gas","gaslvl","flame","fan","dht","bedroom"}`; `devices["door"]["entity"]=="cover.smarthome_cua"`, `devices["buzzer"]["tap"]=="more-info"`, `devices["living"]["tap"]=="toggle"`.
  - `test_positions_applied`: với `positions.json` hiện tại, `devices["rgb"]` ≈ (`-20+55.6/100*540`, `-55+47.7/100*430`) sai số 0.2.
  - `test_titles_no_pins`: không `title` nào chứa `"IO"` hay `"relay"`.
  - `test_view_inserted`: trong `dashboard.yaml`, `views[2]["path"]=="mo-hinh-3d"`, các path khác vẫn có `tong-quan`, `dieu-khien`, `truy-cap`, `quan-ly`.
- [ ] **Step 3:** Chạy → FAIL (không có file).
- [ ] **Step 4:** Thêm hàm `export_model3d(path: str) -> None` vào `build_dashboard.py` dùng lại `walls`, `rooms`, `DEV`, hằng số nội thất (tách các hình chữ nhật nội thất đang viết thẳng trong `svg += [...]` thành danh sách `FURNITURE` để SVG và JSON dùng chung); gọi với `/config/www/smarthome/3d/model3d.json`. Tạo `dashboard_3d.yaml`; chèn trang ở cuối file.
- [ ] **Step 5:** Chạy pytest → PASS; `diff` `floorplan.svg` mới với bản trước khi sửa → giống hệt.

---

### Task 3: `logic.js` — hàm thuần

**Files:**
- Create: `/config/www/smarthome/3d/logic.js`
- Test: `/config/smarthome/tests/3d/logic.test.mjs`

**Interfaces (export):**
- `KINDS: {[slug]: {kind, z, entities?}}` — `kind` ∈ `door|buzzer|pir|lamp|rgb|rfid|ldr|gas|flame|fan|label`; `z` = độ cao gắn (mm): living/bedroom 86, porch 70, rgb 80, buzzer 70, pir 80, rfid 45, ldr 75, gas 60, flame 40, fan 75, gaslvl/dht 110 (nhãn nổi), door 0. `dht.entities = ["sensor.smarthome_nhiet_do_phong_ngu","sensor.smarthome_do_am_phong_ngu"]` (thay `sensor.smarthome_dht11`).
- `STATUS = {link:"binary_sensor.smarthome_ket_noi", temp:"sensor.smarthome_nhiet_do_phong_ngu", hum:"sensor.smarthome_do_am_phong_ngu", gas:"sensor.smarthome_muc_khi_gas", power:"sensor.smarthome_cong_suat_tieu_thu", dark:"binary_sensor.smarthome_troi_toi", alarmButton:"button.smarthome_tat_bao_dong", alarms:["binary_sensor.smarthome_bao_chay_bep","binary_sensor.smarthome_bao_khi_gas_bep","binary_sensor.smarthome_bao_dong_dot_nhap"], intrusion:"binary_sensor.smarthome_bao_dong_dot_nhap"}`
- `isUnavailable(st) -> boolean` — `true` khi `st` undefined hoặc `st.state === "unavailable"`.
- `visualState(kind, sts: stateObj[]) -> {unavailable, on, color:[r,g,b]|null, brightness, door, moving, text}` — `sts[0]` là entity chính.
- `tapCall(dev: {entity,tap}, st) -> {domain, service, data} | {moreInfo: entityId}`
- `alarmActive(states) -> boolean`, `resolveTheme(mode: "day"|"night"|"auto", states) -> "day"|"night"`
- `demoNext(entityId, st) -> stateObj`
- `fmtState(st) -> string` — `"23 °C"` từ `state` + `attributes.unit_of_measurement`, `"—"` khi unavailable/unknown.

- [ ] **Step 1: test thất bại** (`node:test` + `node:assert/strict`), import `../../../www/smarthome/3d/logic.js`:
  - `unavailable`: `isUnavailable(undefined)`, `isUnavailable({state:"unavailable"})` true; `{state:"unknown"}` false.
  - `lamp on/off`: `visualState("lamp",[{state:"on"}]).on === true`; `"off"` → false.
  - `rgb color`: `{state:"on",attributes:{rgb_color:[255,0,0],brightness:128}}` → `color` `[255,0,0]`, `brightness` ≈ 0.502.
  - `rgb fallback`: `{state:"on",attributes:{}}` → `color [255,255,255]`, `brightness 1`.
  - `door`: `open`→`door 1, moving false`; `opening`→`1, true`; `closing`→`0, true`; `closed`→`0, false`.
  - `label dht`: hai st `{state:"28",attributes:{unit_of_measurement:"°C"}}`, `{state:"70",…"%"}` → `text "28 °C · 70 %"`; một st unavailable → `"— · 70 %"`.
  - `tap toggle`: `tapCall({entity:"switch.smarthome_den_hien",tap:"toggle"},{state:"off"})` deepEqual `{domain:"switch",service:"toggle",data:{entity_id:"switch.smarthome_den_hien"}}`; `cover.smarthome_cua` → domain `cover`.
  - `tap more-info`: `tap:"more-info"` → `{moreInfo:"switch.smarthome_coi"}`; `tap:"toggle"` khi unavailable → `{moreInfo:…}`.
  - `theme`: `resolveTheme("auto",{[STATUS.dark]:{state:"on"}})==="night"`; dark unavailable → `"day"`; `"night"` luôn night.
  - `alarm`: một trong `STATUS.alarms` `on` → true; tất cả off/thiếu → false.
  - `demo`: `demoNext("switch.x",{state:"on"}).state==="off"`; `demoNext("switch.x",undefined).state==="on"`; `cover` `closed`→`open`→`closed`; `light` on giữ `attributes.rgb_color`; `sensor.smarthome_the_vua_quet` → `state` khác giá trị cũ.
- [ ] **Step 2:** `node --test /config/smarthome/tests/3d/` → FAIL (thiếu module).
- [ ] **Step 3:** Viết `logic.js` (không import gì).
- [ ] **Step 4:** `node --test /config/smarthome/tests/3d/` → PASS toàn bộ.

---

### Task 4: `scene.js` — nhà và vật thể thiết bị

**Files:**
- Create: `/config/www/smarthome/3d/scene.js` (import `./vendor/three.module.min.js`)
- Test: `/config/smarthome/tests/3d/test_scene.py` (harness: `?scene=1` chỉ dựng scene, camera cố định, render một khung)

**Interfaces (export):**
- `buildHouse(model) -> THREE.Group` — sàn từng phòng (màu `rooms[].color`), tường hộp dày `wall_t` cao `wall_h` theo `walls`, bậu + lanh tô + kính cửa sổ, khung cửa trong, nội thất khối (`tv|sofa|bed|stove`), nền đất/thảm cỏ quanh nhà; nhãn tên phòng nằm trên sàn. Mỗi tường có `userData.wall = true`.
- `createDevice(slug, kindInfo, dev) -> {object: THREE.Object3D, update(vis), tick(dt) -> boolean, setTheme(theme)}` — `object.userData.slug = slug` trên mọi mesh con (để raycast). `tick` trả `true` khi còn hoạt ảnh (quạt quay, cửa đang xoay tới đích, nhấp nháy báo động/còi/PIR, chớp RFID 1,5 s, ngọn lửa). Hình dáng:
  - `door`: cánh cửa xoay quanh bản lề (`x_hinge`), góc = `vis.door × 90°` vào trong, nội suy ~1,2 s/90°.
  - `lamp`: chụp đèn + bóng emissive + `PointLight` (cường độ 0 khi off); `porch` gắn mặt ngoài tường trước.
  - `rgb`: dải đèn dài 80 mm emissive màu `vis.color × brightness` + `PointLight` cùng màu.
  - `fan`: khung tròn + 4 cánh quay ~2 vòng/s khi on.
  - `buzzer`: hộp nhỏ; on → vòng sóng lan ra.
  - `pir`: mắt cầu + nón vùng quét trong suốt, sáng lên (đỏ cam) khi on.
  - `rfid`: hộp phẳng ngoài tường trước, chớp xanh khi `vis.text` đổi.
  - `ldr`: biểu tượng mặt trời/mặt trăng ngoài nhà theo `vis.on`.
  - `gas`/`flame`: đầu dò trên tường bếp; on → đèn đỏ nhấp nháy, `flame` thêm ngọn lửa động trên bếp.
  - `label`: `CSS2DObject` hiển thị `vis.text`.
  - `vis.unavailable` → vật liệu xám + nhãn CSS2D `⚠`.
- `applyTheme(root, theme)` — Ngày: nền `#e9edf2`, Hemisphere + Directional đổ bóng, tường đặc màu kem. Đêm: nền `#0a0f1e`, ambient yếu, tường `opacity 0.25` + viền `EdgesGeometry` màu `#38e1ff`, sàn tối, đèn thiết bị mạnh hơn.
- `alarmGlow(root, rooms, active: boolean, t)` — phủ đỏ nhấp nháy lên sàn bếp (gas/lửa) hoặc cả nhà (đột nhập).

- [ ] **Step 1: test thất bại** `test_scene.py`:
  - `test_scene_builds`: `page.errors == []`; `window.sceneInfo.walls === model.walls.length`; `window.sceneInfo.slugs` sắp xếp == 14 slug của Task 2.
  - `test_screenshot_day_night`: chụp `$SP/shots/day.png`, `$SP/shots/night.png`; tỉ lệ pixel không phải màu nền > 20% (ảnh không trống); độ sáng trung bình night < day.
- [ ] **Step 2:** Chạy → FAIL.
- [ ] **Step 3:** Viết `scene.js`; phần `?scene=1` của harness dựng scene, mỗi thiết bị `update(visualState(...))` với trạng thái mẫu (đèn on, RGB đỏ, quạt on, cửa open) và đặt `window.sceneInfo`.
- [ ] **Step 4:** Chạy → PASS. Mở 2 ảnh chụp bằng Read, tự đánh giá bằng mắt: tường đúng chỗ, cửa mở vào trong, đèn sáng, đêm có viền neon. Sửa cho tới khi đạt.

---

### Task 5: `smarthome-3d-card.js` — thẻ hoàn chỉnh

**Files:**
- Create: `/config/www/smarthome/smarthome-3d-card.js`
- Test: `/config/smarthome/tests/3d/test_card.py`

**Interfaces:**
- Consumes: `logic.js` (Task 3), `buildHouse/createDevice/applyTheme/alarmGlow` (Task 4), `model3d.json` (Task 2).
- Custom element `smarthome-3d-card` (đăng ký `window.customCards` để hiện trong trình chọn thẻ): `setConfig({demo?: boolean, height?: string = "calc(100vh - 120px)"})`, `set hass(h)`, `getCardSize() -> 8`. Nạp `logic.js`, `scene.js`, `model3d.json` bằng dynamic import/fetch kèm `?v=` của `import.meta.url`.
- Thuộc tính test: `card.ready: Promise<void>`; `card.debug(slug) -> {screen:[x,y], vis}` (tọa độ px trong thẻ của tâm vật thể, `vis` cuối cùng đã áp); `card.loopRunning: boolean`; `card.renderer`.
- Tương tác: `pointerdown` → hẹn 500 ms; nhả trước 500 ms và di chuyển < 6 px → **chạm** (raycast lấy `userData.slug` → `tapCall` → `hass.callService(domain, service, data)` hoặc sự kiện `hass-more-info` `{detail:{entityId}, bubbles:true, composed:true}`); đủ 500 ms không di chuyển → **giữ** = more-info; di chuyển ≥ 6 px → huỷ cả hai. `demo: true` → chạm ghi đè trạng thái cục bộ bằng `demoNext`, không gọi `callService`.
- Giao diện phủ (shadow DOM, CSS biến HA `--primary-text-color`, `--card-background-color`): nhóm nút `☀️ Ngày · 🌙 Đêm · Tự động`; nút góc nhìn `Toàn cảnh · Phòng khách · Bếp · Phòng ngủ · Từ trên` (camera nội suy 0,8 s); thanh trạng thái: chấm kết nối, nhiệt độ, độ ẩm, gas, công suất (`fmtState`); nút đỏ "Tắt báo động" chỉ khi `alarmActive` → `button.press` `STATUS.alarmButton`; tên thiết bị hiện khi rê chuột / 2 s sau khi chạm; WebGL không khả dụng → thông báo "Trình duyệt không hỗ trợ WebGL".
- Hiệu năng: chỉ chạy `requestAnimationFrame` khi có thiết bị `tick()` true, camera đang nội suy, hoặc `controls.update()` true; dừng khi không. `disconnectedCallback` dừng vòng lặp; `connectedCallback` chạy lại (dùng lại renderer). `ResizeObserver` → `setSize`. `pixelRatio = min(devicePixelRatio, 2)`; bóng đổ chỉ ở chế độ Ngày. OrbitControls: damping, `maxPolarAngle = 0.47π`, `minDistance 250`, `maxDistance 1400`, tâm (250, 0, 178).
- `localStorage` khoá `smarthome3d.mode`, `smarthome3d.view`.

- [ ] **Step 1: test thất bại** `test_card.py` (trạng thái giả gồm mọi entity của Task 2/`STATUS`):
  - `test_tap_toggle`: chạm `debug("living").screen` → `calls == [["switch","toggle",{"entity_id":"switch.smarthome_den_phong_khach"}]]`.
  - `test_tap_buzzer_more_info`: chạm `buzzer` → `calls == []`, `moreInfo == ["switch.smarthome_coi"]`.
  - `test_hold_more_info`: nhấn giữ 700 ms trên `fan` → `moreInfo == ["switch.smarthome_quat_hut_phong_ngu"]`, `calls == []`.
  - `drag_no_toggle`: nhấn trên `living`, kéo 80 px, nhả trên `rgb` → `calls == []`, `moreInfo == []`.
  - `hass_before_ready`: gán hass (đèn ngủ `on`) ngay sau khi tạo thẻ, chưa chờ `ready` → sau `ready`, `debug("bedroom").vis.on === true`.
  - `test_state_update`: đổi `light.smarthome_den_rgb` sang `{state:"on",attributes:{rgb_color:[0,0,255],brightness:255}}` → `debug("rgb").vis.color == [0,0,255]`.
  - `test_alarm_button`: `binary_sensor.smarthome_bao_khi_gas_bep` `on` → nút "Tắt báo động" hiện; bấm → `calls[-1] == ["button","press",{"entity_id":"button.smarthome_tat_bao_dong"}]`; trở về off → nút ẩn.
  - `test_demo`: `?demo=1`, chạm `door` hai lần → `calls == []`, `debug("door").vis.door` lần lượt 1 rồi 0.
  - `test_idle_stops_loop`: mọi thiết bị tĩnh, chờ 2 s → `loopRunning === false`.
  - `reconnect`: tháo thẻ khỏi DOM, gắn lại, chạm `living` → đúng 1 lần gọi; `loopRunning` không nhân đôi (đếm số lần `requestAnimationFrame` gọi trong 1 khung ≤ 1).
  - `resize`: đổi thẻ sang 500×400 → `renderer.domElement.clientWidth == 500` trong 500 ms.
  - `test_mode_persist`: bấm "🌙 Đêm", tải lại trang → chế độ vẫn là night.
  - Mọi test: `page.errors == []`.
- [ ] **Step 2:** Chạy `$SP/venv/bin/pytest /config/smarthome/tests/3d/test_card.py -v` → FAIL.
- [ ] **Step 3:** Viết `smarthome-3d-card.js`; harness hoàn chỉnh dùng thẻ thật.
- [ ] **Step 4:** Chạy toàn bộ `$SP/venv/bin/pytest /config/smarthome/tests/3d -v` và `node --test /config/smarthome/tests/3d/` → PASS.
- [ ] **Step 5:** Chụp `$SP/shots/card_{day,night,alarm,phone}.png` (phone = 390×780); xem bằng Read; chỉnh tới khi giao diện phủ không che mô hình, chữ đọc được ở cả hai chế độ.

---

### Task 6: Đưa lên Home Assistant

**Files:**
- Create: `/config/smarthome/tools/push_3d.py` (docstring ghi cách dùng, theo kiểu `add_view_dieu_khien.py`)

**Interfaces:**
- Consumes: `HA`, `URL_PATH` từ `push_dashboard.py`.
- `push_3d.py`: (1) `v` = 8 ký tự md5 của nội dung `smarthome-3d-card.js` + `3d/logic.js` + `3d/scene.js` + `3d/model3d.json`; (2) `lovelace/resources` → tìm resource có URL bắt đầu `/local/smarthome/smarthome-3d-card.js` → `update` (url mới) hoặc `create` (`res_type: "module"`, `url: /local/smarthome/smarthome-3d-card.js?v=<v>`); (3) thay hoặc chèn trang `mo-hinh-3d` từ `dashboard_3d.yaml` vào index 2 (giống `add_view_dieu_khien.py`), không đụng trang khác. In: `"Resource v=<v> · trang: [...]"`.

- [ ] **Step 1:** `python3 tools/push_dashboard.py --pull` rồi `python3 tools/build_dashboard.py` (để `model3d.json` theo vị trí mới nhất). Kiểm tra: in `ok [... 'mo-hinh-3d' ...]`.
- [ ] **Step 2:** Sao lưu cấu hình dashboard hiện tại: `lovelace/config` → `smarthome/lovelace_backup_20261019_truoc_3d.json`.
- [ ] **Step 3:** Viết và chạy `push_3d.py`. Kiểm tra bằng websocket: `lovelace/resources` có đúng 1 URL thẻ 3D; `lovelace/config` views = 4 trang cũ (cùng path, cùng nội dung so với bản sao lưu) + `mo-hinh-3d` ở index 2.
- [ ] **Step 4:** `curl -s http://supervisor/core/local/smarthome/3d/model3d.json` (header `Authorization: Bearer $SUPERVISOR_TOKEN`) hoặc kiểm tra file tồn tại dưới `/config/www` → HTTP 200.
- [ ] **Step 5:** Nhờ người dùng mở trang "Mô hình 3D" trên máy tính và app điện thoại (tải lại cứng 1 lần), xác nhận hiển thị; khi ESP32 thật online, chạm thử từng thiết bị (Kiểm tra 4 trong spec).
- [ ] **Step 6:** Cập nhật memory dự án: trang 3D, `push_3d.py`, nhớ chạy lại `build_dashboard.py` + `push_3d.py` sau khi kéo lại vị trí 2D.
