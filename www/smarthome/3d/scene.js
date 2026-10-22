// Mặt tiền cảnh 3D: nhà thật (house.js, furnish.js) + thiết bị (devices.js) + ánh sáng Ngày / Đêm thật.
// Trục: mặt bằng (x, y) -> three (x, cao, y); 1 đơn vị = 1 mm mô hình (= 20 mm thật); tường trước y = 0.
import * as THREE from './vendor/three.module.min.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

// Module con nạp động kèm ?v của chính scene.js (vendor thì import tĩnh, không ?v).
const V = new URL(import.meta.url).search;
const HOUSE = await import('./house.js' + V);
const FURN = await import('./furnish.js' + V);
const DEV = await import('./devices.js' + V);
// buildHouse(model, assets?) -> Group 'house' gồm cả nội thất; updateCutaway(root, camera, dt?) -> boolean
export const buildHouse = HOUSE.buildHouse;
export const updateCutaway = HOUSE.updateCutaway;
export const CUT = HOUSE.CUT;   // chiều cao tường đã hạ
export const furnish = FURN.furnish;
// createDevice(slug, kindInfo, dev, model?, assets?) -> {object, update(vis), tick(dt), setTheme(theme)}
export const createDevice = DEV.createDevice;
export const ON_COLOR = DEV.ON_COLOR;   // màu trạng thái bật (viền thiết bị, huy hiệu thẻ)

const PI = Math.PI;

// ---------- renderer ----------
// setupRenderer ghi nhớ renderer (PMREM cho môi trường) + chế độ điện thoại (bóng 1024, không bóng đèn điểm/rọi)
let R = null, MOBILE = false;

export function setupRenderer(renderer, { mobile = false } = {}) {
  R = renderer;
  MOBILE = !!mobile;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
}

// ---------- Ngày / Đêm ----------
// Thông số ánh sáng theo chế độ (đơn vị three: lux/cd; nhà tính bằng mm)
const LOOK = {
  day: { env: 0.7, sun: 3.0, sunC: 0xfff0dc, hemi: 0.15, sky: 0xdfeaff, ground: 0x8a7a62, fog: 0xd3e2ee },
  night: { env: 0.15, sun: 0.4, sunC: 0x9fb8ff, hemi: 0.22, sky: 0x3a4f7c, ground: 0x10141e, fog: 0x0b1426 },
};
const NIGHT_BG = 0x0b1426;

// Trời ngày: dải xanh nhạt dọc màn hình
function skyTex() {
  const c = document.createElement('canvas');
  c.width = 2; c.height = 256;
  const g = c.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 256);
  gr.addColorStop(0, '#9cc3e6');
  gr.addColorStop(0.6, '#c9def0');
  gr.addColorStop(1, '#e4edf4');
  g.fillStyle = gr;
  g.fillRect(0, 0, 2, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.name = 'sky_day';
  return t;
}

// Đèn chung tạo một lần: nắng/trăng (một DirectionalLight có bóng), bán cầu, 2 đèn đỏ báo động
function makeLights(root) {
  const sun = new THREE.DirectionalLight();
  sun.position.set(-130, 620, -260);
  sun.target.position.set(250, 0, 178);
  sun.castShadow = true;
  const s = sun.shadow;
  s.mapSize.set(MOBILE ? 1024 : 2048, MOBILE ? 1024 : 2048);
  Object.assign(s.camera, { left: -480, right: 480, top: 480, bottom: -480, near: 50, far: 1600 });
  s.bias = -0.0006;
  s.normalBias = 0.8;
  const hemi = new THREE.HemisphereLight();
  // một đèn đỏ dùng chung cho hai phạm vi báo động (đột nhập ưu tiên): bớt một đèn điểm cho shader
  const alarm = new THREE.PointLight(0xff2a1a, 0, 520, 2);
  alarm.name = 'alarm';
  alarm.userData.active = {};
  root.add(alarm);
  root.add(sun, sun.target, hemi);
  const L = { sun, hemi, alarm, fog: new THREE.Fog(0xd3e2ee, 1500, 3800), sky: skyTex(), night: new THREE.Color(NIGHT_BG) };
  root.userData.lights = L;
  return L;
}

/**
 * applyTheme(root, theme) -> {shadows}: 'day' | 'night'. Gọi lại nhiều lần được (đèn/môi trường tạo một lần).
 * Ngày: môi trường RoomEnvironment (PMREM), nắng ấm bóng mềm, trời xanh nhạt.
 * Đêm: trời #0b1426, trăng xanh nhạt yếu, môi trường thấp; tường giữ nguyên vật liệu (đặc), không viền.
 */
export function applyTheme(root, theme) {
  const night = theme === 'night', P = LOOK[night ? 'night' : 'day'];
  const L = root.userData.lights || makeLights(root);
  if (root.isScene) {
    if (!root.userData.env && R) {
      const pm = new THREE.PMREMGenerator(R);
      const room = new RoomEnvironment();
      root.userData.env = pm.fromScene(room, 0.04).texture;   // thẻ dispose root.userData.env khi gỡ
      room.dispose();
      pm.dispose();
    }
    if (root.userData.env) root.environment = root.userData.env;
    root.environmentIntensity = P.env;
    root.background = night ? L.night : L.sky;
    L.fog.color.set(P.fog);
    root.fog = L.fog;
  }
  L.sun.color.set(P.sunC);
  L.sun.intensity = P.sun;
  L.hemi.color.set(P.sky);
  L.hemi.groundColor.set(P.ground);
  L.hemi.intensity = P.hemi;
  root.userData.theme = theme;
  root.traverse((o) => {
    // bóng đèn trần/đèn hiên: chỉ máy tính; cố định (không đổi khi bật/tắt -> không biên dịch lại shader)
    if (o.isLight && o.userData.shadowOK) o.castShadow = !MOBILE;
    if (o.userData.device) o.userData.device.setTheme(theme);
  });
  DEV.syncWindows(root);
  return { shadows: true };
}

/**
 * alarmGlow(root, rooms, active, t, scope = 'kitchen' | 'house') -> boolean (true khi đang báo).
 * Ánh đỏ nhấp nhô nhẹ trong phòng bị báo (đèn điểm đỏ, không phủ đỏ cả màn hình); t tính bằng giây.
 */
export function alarmGlow(root, rooms, active, t, scope = 'kitchen') {
  const L = root.userData.lights || makeLights(root);
  const lt = L.alarm, on = lt.userData.active;
  on[scope] = !!active;
  // phạm vi đang hiển thị: đột nhập (cả nhà) ưu tiên hơn bếp
  const show = on.house ? 'house' : on.kitchen ? 'kitchen' : null;
  if (show && lt.userData.at !== show) {
    let r = rooms.find((x) => /BẾP/i.test(x.name)) || rooms[0];
    if (show === 'house') {
      // cả mặt bằng: tâm nhà, tầm phủ hết nhà
      const x0 = Math.min(...rooms.map((q) => q.x)), z0 = Math.min(...rooms.map((q) => q.y));
      const x1 = Math.max(...rooms.map((q) => q.x + q.w)), z1 = Math.max(...rooms.map((q) => q.y + q.d));
      r = { x: x0, y: z0, w: x1 - x0, d: z1 - z0 };
    }
    lt.position.set(r.x + r.w / 2, 110, r.y + r.d / 2);
    // bếp: tầm ≈ cỡ bếp để đỏ không lan sang phòng ngủ
    lt.distance = Math.round(Math.hypot(r.w, r.d) * (show === 'house' ? 0.75 : 0.6));
    lt.userData.at = show;
  }
  if (show === scope || !show) {
    const k = 0.5 + 0.5 * Math.sin(t * 2 * PI * 1.2);
    const night = root.userData.theme === 'night';
    lt.intensity = show ? (night ? 14000 : 45000) * (0.25 + 0.75 * k) * (show === 'house' ? 2.2 : 1) : 0;
  }
  return !!active;
}
