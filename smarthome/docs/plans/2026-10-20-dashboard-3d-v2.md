# Trang "Mô hình 3D" bản 2 (nhà thật) — kế hoạch thực hiện

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm lại phần hình của thẻ `smarthome-3d-card` thành nhà thật tỉ lệ 1:20 (PBR, nội thất glTF CC0, tường tự hạ, đêm thật tường đặc), giữ nguyên thao tác và cách triển khai.

**Architecture:** Tài nguyên (vân, model) tải một lần bằng script có manifest về `www/smarthome/3d/assets/`. `scene.js` thành mặt tiền mỏng, nạp các module con (`house.js`, `furnish.js`, `devices.js`) bằng dynamic import kèm `?v=` của chính nó. Thẻ gọi thêm `loadAssets()` (thanh tải) và `updateCutaway()` khi camera đổi.

**Tech Stack:** three.js 0.170.0 (+ GLTFLoader, RoomEnvironment, EffectComposer/RenderPass/GTAOPass/OutputPass chép về máy), Poly Haven CC0 (1k), pytest + Playwright, node --test.

**Spec:** `/config/smarthome/docs/2026-10-19-dashboard-3d-design.md` — phần "Bản 2" thay phần Mô hình/chế độ của bản 1.

## Global Constraints
- Chỉ nhà và thiết bị nhìn thấy; KHÔNG ESP32, relay, dây, mạch.
- 1 đơn vị three = 1 mm mô hình (= 20 mm thật). Mặt bằng: nhà 500 × 355, vách giữa y = 188, vách bếp|ngủ x = 220. **Tường cao 135, cửa đi cao 105, cửa sổ bậu 45 / đỉnh 105.** Trục: (x, y) mặt bằng → three (x, cao, y).
- Không `push_dashboard.py --full`; 4 trang cũ giữ nguyên. Không sửa `configuration.yaml`, không khởi động lại HA.
- Vendor three.js + addons không mang `?v=`. Mọi module của mình (card, `logic.js`, `scene.js`, `house.js`, `furnish.js`, `devices.js`) và `model3d.json`, `assets/manifest.json` được nạp kèm `?v=` lan truyền từ `import.meta.url` (module con: `await import('./x.js' + new URL(import.meta.url).search)`).
- Tài nguyên chỉ từ Poly Haven giấy phép CC0, độ phân giải 1k; tổng `assets/` ≤ 15 MB.
- API giữ tên: `buildHouse`, `createDevice`, `applyTheme`, `alarmGlow`, `setupRenderer` (thẻ hiện dùng các tên này); thêm `loadAssets(onProgress)`, `updateCutaway(root, camera)`.
- Chữ tiếng Việt có dấu; comment tiếng Việt ngắn. Git repo cục bộ `/config`; commit mỗi phần, kết thúc message bằng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Còi: chạm = more-info. Thao tác chạm/giữ/kéo, góc nhìn, thanh trạng thái, nút tắt báo động, demo: giữ nguyên hành vi (test_card.py hiện có phải tiếp tục đạt, trừ chỗ phụ thuộc hình học cũ — sửa test và ghi lý do).

## Review Focus
1. Tài nguyên tải lỗi một phần (404, mạng chậm qua <HA_HOST>) → thẻ vẫn chạy với vật liệu dự phòng, báo lỗi gọn, không treo thanh tải (Task 2: `test_asset_404_fallback`).
2. Tường tự hạ khi người dùng kéo xoay liên tục → không giật, không để tường nào kẹt ở trạng thái giữa (Task 3: `test_cutaway_follows_camera`).
3. Đêm: phòng không bật đèn vẫn đủ sáng để nhận ra đồ vật (Task 4: `test_night_readable`).
4. Điện thoại: draw call và thời gian dựng khung ở 390 px trong ngân sách (Task 5: `test_phone_budget`).
5. Triển khai lại: trình duyệt không giữ bản cũ của module con/tài nguyên (Task 6: hash `?v` gồm mọi file của mình + manifest).

---

### Task 1: Vendor addon + tải tài nguyên CC0

**Files:**
- Create: `/config/www/smarthome/3d/vendor/{GLTFLoader.js, RoomEnvironment.js, EffectComposer.js, RenderPass.js, ShaderPass.js, MaskPass.js, Pass.js, GTAOPass.js, OutputPass.js, ...}` (đủ đồ thị import, sửa `'three'` → `'./three.module.min.js'`, đường dẫn `../shaders/X.js` / `../utils/X.js` → `./X.js`)
- Create: `/config/smarthome/tools/fetch_3d_assets.py`, `/config/www/smarthome/3d/assets/manifest.json`, `/config/www/smarthome/3d/assets/LICENSE.md`
- Test: `/config/smarthome/tests/3d/test_vendor.py` (thêm), `/config/smarthome/tests/3d/test_assets.py`

**Interfaces:**
- Produces `manifest.json`: `{"textures": {"<key>": {"diff": "textures/…_diff_1k.jpg", "nor": "…_nor_gl_1k.jpg", "rough"|"arm": "…", "repeat_mm": <kích thước một ô vân, mm mô hình>}}, "models": {"<key>": {"gltf": "models/<id>/<id>_1k.gltf", "size_mm": [w, d, h] (kích thước mục tiêu, mm mô hình)}}, "source": "Poly Haven", "license": "CC0"}`.
- Texture keys (bắt buộc): `floor_wood`, `floor_tile_kitchen`, `wall_plaster`, `wall_exterior`, `paving`, `grass`, `countertop`, `fabric_bed`. Model keys (bắt buộc): `sofa` (sofa_02 hoặc sofa_03), `coffee_table` (modern_coffee_table_01), `armchair` (modern_arm_chair_01 hoặc mid_century_lounge_chair), `nightstand` (painted_wooden_nightstand), `shelf` (wooden_display_shelves_01 hoặc modern_wooden_cabinet), `plant` (một cây trong chậu thuộc nhóm `plants`). Tên asset Poly Haven chọn bằng API `https://api.polyhaven.com/assets?t=…` + `/files/<id>`; script ghi id đã chọn vào manifest.
- `fetch_3d_assets.py`: idempotent (bỏ qua file đã có đúng kích thước), in tổng dung lượng.

- [ ] **Step 1: test thất bại** `test_assets.py`: `test_manifest_complete` (đủ key ở trên, mọi file tồn tại, tổng `assets/` ≤ 15 MB, `license == "CC0"`); `test_vendor.py::test_addons_load` (import trong trình duyệt GLTFLoader, RoomEnvironment, EffectComposer, GTAOPass, OutputPass → là function, `page.errors == []`); `test_assets.py::test_gltf_loads` (GLTFLoader nạp từng model trong manifest, mỗi cái có ≥ 1 mesh). Chạy → FAIL.
- [ ] **Step 2:** Viết script, tải, vendor addon. Chạy → PASS. Commit.

---

### Task 2: `model3d.json` bản 2 + nạp tài nguyên

**Files:**
- Modify: `/config/smarthome/tools/build_dashboard.py` (`export_model3d`: `wall_h` 135, `window.sill` 45, `window.top` 105, thêm `house.door_h` 105)
- Create: `/config/www/smarthome/3d/assets.js` — `loadAssets(onProgress: (done, total) => void) -> Promise<{textures: {[key]: {map, normalMap, roughnessMap?, aoMap?, repeat_mm}}, models: {[key]: THREE.Object3D (đã scale về size_mm, đặt đáy y = 0, tâm x/z = 0)}, failed: string[]}>`
- Test: `test_model3d.py` (sửa giá trị), `/config/smarthome/tests/3d/test_assets.py` (thêm)

**Interfaces:**
- `loadAssets` không bao giờ reject: file lỗi → ghi key vào `failed`, texture thiếu → `null`, model thiếu → `null`; gọi `onProgress` sau mỗi file. Cache trong module (gọi lần 2 trả cùng Promise).

- [ ] **Step 1: test thất bại:** `test_house_dims` mới (`wall_h` 135, `door_h` 105, `window` sill 45 / top 105); `test_load_assets_all` (đủ key, `failed == []`, progress cuối `done == total`); `test_asset_404_fallback` (chặn 1 texture + 1 model bằng `page.route` → resolve, `failed` có đúng 2 key, không `pageerror`). Chạy → FAIL.
- [ ] **Step 2:** Sửa build + viết `assets.js`. Chạy build, kiểm tra `floorplan.svg` byte-identical. Chạy → PASS. Commit.

---

### Task 3: Nhà thật + nội thất + tường tự hạ

**Files:**
- Create: `/config/www/smarthome/3d/house.js`, `/config/www/smarthome/3d/furnish.js`
- Modify: `/config/www/smarthome/3d/scene.js` (mặt tiền: re-export; bỏ code nhà/nội thất cũ)
- Test: `/config/smarthome/tests/3d/test_scene.py`, `harness.html` (`?scene=1` dùng `loadAssets`)

**Interfaces:**
- `buildHouse(model, assets) -> THREE.Group` (`userData.walls: Array<{mesh, x1,y1,x2,y2}>`, mỗi tường `userData.wall = true`). Tường hai mặt: trong `wall_plaster`, ngoài `wall_exterior`, đỉnh tường màu kem. Cửa sổ có khung + kính vật lý (`MeshPhysicalMaterial`, transmission nhẹ). Ô cửa trong có khung. Sàn theo phòng (`floor_wood`, bếp `floor_tile_kitchen`), ngoài nhà `grass` + lối đi `paving` từ cửa chính ra. Vân lặp theo `repeat_mm` (không giãn).
- `furnish(model, assets) -> THREE.Group`: phòng khách sofa + bàn trà + ghế bành + kệ + TV phẳng treo tường trước (vị trí theo `model.furniture` tv/sofa); phòng ngủ giường đôi tự dựng (khung gỗ, nệm, chăn `fabric_bed`, 2 gối) theo `model.furniture` bed + 2 tủ đầu giường; bếp tủ bếp chữ L mặt `countertop` + bếp nấu theo `model.furniture` stove; 1–2 cây cảnh. Model thiếu (`null`) → khối dự phòng cùng kích thước, vật liệu trung tính.
- `updateCutaway(root, camera) -> boolean` (true khi còn đang chuyển): tường mà pháp tuyến hướng về camera và nằm giữa camera và tâm nhà (250, 178) → chiều cao đích 25; còn lại 135; nội suy ~0,25 s; chỉ đổi `scale.y`/vị trí, không dựng lại hình học.

- [ ] **Step 1: test thất bại:** `test_scene_builds` (số tường = `model.walls.length`, 14 slug, không lỗi); `test_cutaway_follows_camera` (camera Toàn cảnh → tường trước (y = 0) thấp ≤ 30 và tường sau (y = 355) = 135; đặt camera phía sau → ngược lại; gọi `updateCutaway` lặp tới khi false → mọi tường ở đúng 25 hoặc 135); `test_furniture_present` (có node tên `sofa`, `bed`, `kitchen`, `tv`); chụp `shots/v2_day.png`. Chạy → FAIL.
- [ ] **Step 2:** Viết `house.js`, `furnish.js`, sửa `scene.js`. Chạy → PASS. Xem ảnh bằng Read, chỉnh tới khi trông như nhà thật (tỉ lệ đồ đạc hợp lý so với tường 2,7 m, vân không giãn, bóng mềm). Commit.

---

### Task 4: Thiết bị thật + Ngày/Đêm thật

**Files:**
- Create: `/config/www/smarthome/3d/devices.js` (thay phần thiết bị trong scene.js cũ)
- Modify: `/config/www/smarthome/3d/scene.js` (`applyTheme`, `alarmGlow`, `setupRenderer` mới; re-export `createDevice`)
- Test: `/config/smarthome/tests/3d/test_scene.py`

**Interfaces:**
- `createDevice(slug, kindInfo, dev, model)` giữ hợp đồng cũ (`{object, update(vis), tick(dt)->boolean, setTheme(theme)}`, `userData.slug` trên mọi mesh, mesh hiệu ứng tắt raycast, lần update đầu không hoạt ảnh, RFID bỏ qua unavailable/unknown/'' như bản 1). Hình mới theo spec bản 2: đèn ốp trần (PointLight ấm 2700 K, có bóng ở đèn khách/ngủ), đèn hiên (SpotLight rọi xuống lối đi), dải RGB hắt trần (RectAreaLight hoặc PointLight + emissive), quạt hút có lưới + cánh, cửa gỗ có tay nắm + bản lề như bản 1, PIR/gas/lửa/LDR/RFID là khối trắng nhỏ đúng cỡ, còi + báo động = đèn xoay đỏ (SpotLight quay). Unavailable: xám + ⚠ như bản 1. Độ cao lắp `KINDS[slug].z` nhân 1,5 (tường cao hơn) — ghi rõ trong code.
- `applyTheme(root, theme)`: Ngày — `RoomEnvironment` PMREM làm `scene.environment`, nắng ấm có bóng mềm, trời xanh nhạt. Đêm — trời xanh thẫm `#0b1426`, trăng (Directional xanh nhạt cường độ thấp), `environmentIntensity` thấp, tường đặc, cửa sổ phòng có đèn bật phát sáng; KHÔNG viền neon, KHÔNG tường trong suốt. Idempotent.
- `setupRenderer(renderer, {mobile})`: tone mapping AgX hoặc ACES, sRGB, bóng PCFSoft (mobile: map 1024, desktop 2048).

- [ ] **Step 1: test thất bại:** `test_lamp_lights_room` (độ sáng trung bình vùng phòng khách tăng ≥ 15 % khi `living` on so với off, ở chế độ đêm); `test_night_readable` (đêm, mọi đèn tắt: độ sáng trung bình vùng nhà ≥ 0,12 trên thang 0–1, và có tương phản cạnh tường/đồ vật — độ lệch chuẩn ≥ 0,04); `test_no_neon` (không object nào `userData.nightOnly` hay `EdgesGeometry`); `test_rfid_flash_only_on_real_change` + các test thiết bị cũ vẫn đạt; chụp `shots/v2_day.png`, `v2_night.png`, `v2_night_lamps.png`, `v2_alarm.png`. Chạy → FAIL.
- [ ] **Step 2:** Viết `devices.js`, sửa scene. Chạy → PASS. Xem ảnh, chỉnh. Commit.

---

### Task 5: Ghép vào thẻ

**Files:**
- Modify: `/config/www/smarthome/smarthome-3d-card.js`
- Test: `/config/smarthome/tests/3d/test_card.py`

**Interfaces:**
- Thẻ gọi `loadAssets` (thanh tải "Đang tải mô hình… N/M" phủ giữa thẻ, ẩn khi xong; có `failed` → dòng nhỏ "Thiếu N tài nguyên, dùng hình đơn giản"), `buildHouse(model, assets)` + `furnish` qua `scene.js`, gọi `updateCutaway` trong vòng lặp khi camera đổi (giữ vòng lặp chạy khi nó trả true). Desktop (rộng ≥ 700 px và không `(pointer: coarse)`): EffectComposer + GTAOPass + OutputPass; mobile: render thẳng, pixel ratio ≤ 1,5. Đặt lại camera presets cho tường cao: Toàn cảnh (250, 700, -340) lookAt (250, 0, 178); Từ trên (250, 1000, 238); phòng: gần hơn, từ phía trước.
- Sửa luôn các mục deferred từ bản 1 mà review cuối sẽ chặn: chặn đa điểm chạm (theo dõi tập pointerId đang chạm, ≥ 2 → không bắt đầu/huỷ nhấn), `callService(...).catch(() => {})` (HA tự hiện thông báo lỗi), `setConfig` đổi `demo` → xoá ghi đè demo.

- [ ] **Step 1: test thất bại:** toàn bộ test_card.py hiện có (sửa toạ độ phụ thuộc hình học, ghi lý do) + `test_loading_overlay` (hiện khi đang tải, ẩn sau `ready`); `test_two_finger_no_toggle` (2 pointer, ngón thứ nhất trên sàn, ngón thứ hai trên `living`, nhả trong 200 ms → `calls == []`); `test_phone_budget` (390×780: `renderer.info.render.calls` ≤ 450 mỗi khung, thời gian `ready` ≤ 15 s trong SwiftShader); `test_cutaway_on_preset` (bấm "Từ trên" rồi "Toàn cảnh" → tường trước thấp). Chạy → FAIL.
- [ ] **Step 2:** Sửa thẻ. Chạy toàn bộ `pytest smarthome/tests/3d` + `node --test …/logic.test.mjs` → PASS. Chụp `card_v2_{day,night,phone}.png`, xem, chỉnh. Commit.

---

### Task 6: Triển khai lại + kiểm tra mạch thật

**Files:**
- Modify: `/config/smarthome/tools/push_3d.py` (hash gồm card + mọi `www/smarthome/3d/*.js` + `model3d.json` + `assets/manifest.json`)

- [ ] **Step 1:** `push_dashboard.py --pull` → `build_dashboard.py` → sao lưu `lovelace/config` vào `smarthome/lovelace_backup_20261020_truoc_3d_v2.json` → `push_3d.py`. Kiểm tra: 1 resource với `?v` mới; views không đổi so với bản sao lưu. Commit.
- [ ] **Step 2:** (controller) Nạp trạng thái thật vào harness, chụp ảnh; bật/tắt đèn phòng khách thật; nhờ người dùng xem trên trình duyệt / app.
