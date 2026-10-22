// Thiết bị như đồ thật (1 đơn vị = 1 mm mô hình = 20 mm thật): đèn ốp trần, đèn hiên rọi lối đi, dải LED RGB,
// quạt hút có lưới + cánh, cửa gỗ, cảm biến khối trắng nhỏ, còi + đèn xoay đỏ. Không sprite quầng sáng
// (GTAO vẽ chúng thành mảng đen): chỉ vật liệu phát sáng + đèn thật.
// Trục: mặt bằng (x, y) -> three (x, cao, y); tường trước y = 0 (ngoài nhà y < 0).
import { CSS2DObject } from './vendor/CSS2DRenderer.js';

const V = new URL(import.meta.url).search;
const { THREE, softBox } = await import('./kit.js' + V);

const PI = Math.PI;
// KINDS[slug].z đo cho tường bản 1 cao 90; tường bản 2 cao 135 -> độ cao lắp = z × 1,5
export const Z_SCALE = 1.5;
const WARM = 0xffb46b;           // 2700 K
const LAMP_I = 52000;            // cd (đơn vị mm): đèn ốp trần, decay 2
const PORCH_I = 60000;           // đèn hiên (SpotLight)
const RGB_I = 300;               // dải LED RGB ở độ sáng 100 %
const BEACON_I = 90000;          // đèn xoay đỏ của còi
const FIRE_I = 26000;
const noRay = () => {};
const LABEL_Y = 100, LABEL_Y_SENSOR_MOUNT = 95;   // độ cao neo nhãn mức gas / độ cao lắp cảm biến DHT (tường 135)
// Thiết bị gắn tường phóng to so với cỡ thật cho dễ nhìn trên mô hình (thân + viền); đèn trần 1,4
const WALL_SCALE = { fan: 1.65, porch: 1.8, rgb: 1 }, WALL_SCALE_DEF = 2.4, LAMP_SCALE = 1.7;   // khóa: slug rồi loại
const RGB_Y = 85;   // thanh LED RGB trên vách đầu sofa (1,7 m thật)
const SOFA_TOP = 38;   // lưng sofa (furnish.js: cao 35) + 3: thanh LED trượt theo vách hạ không xuống thấp hơn
// Màu trạng thái "bật" (viền vòng sáng + huy hiệu của thẻ dùng chung); cảm biến/còi bật = đang báo -> đỏ
export const ON_COLOR = { lamp: '#f2a900', fan: '#16a34a', door: '#9a6a3e', ldr: '#6d5bd0', buzzer: '#e53935',
  pir: '#e53935', gas: '#e53935', flame: '#e53935' };
const RING_IDLE = 0x38bdf8;   // viền khi tắt: xanh dịu

// ---------- vật liệu dùng chung (không đổi theo trạng thái) ----------
const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0, ...o });
const MAT = {
  plastic: std(0xf4f4f1, { roughness: 0.42, name: 'dev_plastic' }),
  matte: std(0xf1f0ec, { roughness: 0.8, name: 'dev_matte' }),
  black: std(0x1d1e20, { roughness: 0.45, metalness: 0.3, name: 'dev_black' }),
  shroud: std(0x2a2c2f, { roughness: 0.9, name: 'dev_shroud' }),
  alu: std(0xc9ccd1, { roughness: 0.32, metalness: 0.85, name: 'dev_alu' }),
  chrome: std(0xd6d8dc, { roughness: 0.22, metalness: 1, name: 'dev_chrome' }),
  blade: std(0x8f979f, { roughness: 0.5, name: 'dev_blade' }),
  lens: std(0x101114, { roughness: 0.12, metalness: 0.2, name: 'dev_lens' }),
  ldr: std(0xc9632d, { roughness: 0.5, name: 'dev_ldr' }),
  tvBack: std(0x1c1c1e, { roughness: 0.4, metalness: 0.3, name: 'dev_tv_back' }),
};
const GRAY = std(0x9aa0a6, { roughness: 0.9, name: 'dev_unavailable' });

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

// vân gỗ cửa (dọc theo chiều cao cánh), tạo một lần
let woodM = null;
function woodMat() {
  if (woodM) return woodM;
  const map = canvasTex(256, 512, (g, w, h) => {
    g.fillStyle = '#8b5a36'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 140; i++) {
      const x = Math.random() * w, a = 0.05 + Math.random() * 0.12, dark = Math.random() < 0.6;
      g.strokeStyle = dark ? `rgba(60,32,16,${a})` : `rgba(190,130,80,${a})`;
      g.lineWidth = 0.6 + Math.random() * 2.4;
      g.beginPath();
      for (let y = 0; y <= h; y += 16) g.lineTo(x + 5 * Math.sin(y * 0.012 + i) + 2 * Math.sin(y * 0.05 + i * 3), y);
      g.stroke();
    }
  });
  woodM = std(0xffffff, { map, roughness: 0.55, name: 'dev_wood' });
  return woodM;
}

let panelM = null;
const panelMat = () => panelM || (panelM = std(0xdcc4ae, { map: woodMat().map, roughness: 0.6, name: 'dev_wood_panel' }));

// mặt đầu đọc RFID: nền đen + biểu tượng không chạm
let rfidT = null;
const rfidTex = () => rfidT || (rfidT = canvasTex(64, 96, (g, w, h) => {
  g.fillStyle = '#16181b'; g.fillRect(0, 0, w, h);
  g.strokeStyle = '#d9dde2'; g.lineWidth = 3; g.lineCap = 'round';
  for (const r of [8, 15, 22]) { g.beginPath(); g.arc(w / 2 - 10, h * 0.55, r, -0.7, 0.7); g.stroke(); }
}));

// ---------- tiện ích dựng hình ----------
function mesh(geo, mat, x = 0, y = 0, z = 0, cast = true) {
  const m = new THREE.Mesh(geo, mat);
  m.position.set(x, y, z);
  m.castShadow = cast;
  m.receiveShadow = true;
  return m;
}
const B = (w, h, d) => new THREE.BoxGeometry(w, h, d);
// trụ tròn trục z (nhô ra khỏi tường)
const cylZ = (r, h, seg = 24, r2 = r) => new THREE.CylinderGeometry(r2, r, h, seg).rotateX(PI / 2);
const round = (w, h, d, r) => softBox(w, h, d, r, { seg: 3 });
const fx = (m) => { m.userData.fx = true; m.raycast = noRay; m.castShadow = false; return m; };
const glowMat = (color, o = {}) => std(color, { emissive: color, emissiveIntensity: 0, roughness: 0.35, ...o });

// Phòng chứa điểm (x, y) theo mặt bằng
const roomAt = (model, x, y) => (model ? model.rooms.find((r) => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.d) : null);

// Tường / ô cửa / cửa sổ gần nhất (≤ 50) để gắn thiết bị lên mặt tường, mặt quay về phía thiết bị.
// line = khóa đường tường của house.js ('h' + y | 'v' + x) để ẩn theo tường khi tường hạ.
function mountOf(dev, model) {
  if (!model) return { x: dev.x, z: dev.y, rot: PI, line: null, door: false };
  const t = model.house.wall_t, segs = model.walls.map((w) => [...w, false]);
  for (const d of model.doors) segs.push([d.x_free, d.y, d.x_hinge, d.y, true]);
  if (model.window) segs.push([model.window.x1, model.window.y, model.window.x2, model.window.y, false]);
  let best = null;
  for (const [x1, y1, x2, y2, door] of segs) {
    const px = Math.min(Math.max(dev.x, Math.min(x1, x2)), Math.max(x1, x2));
    const py = Math.min(Math.max(dev.y, Math.min(y1, y2)), Math.max(y1, y2));
    const dist = Math.hypot(dev.x - px, dev.y - py);
    if (dist > 50 || (best && dist >= best.dist)) continue;
    const horiz = y1 === y2;
    const nx = horiz ? 0 : Math.sign(dev.x - x1) || 1, nz = horiz ? Math.sign(dev.y - y1) || 1 : 0;
    best = {
      dist, door, line: horiz ? 'h' + y1 : 'v' + x1, out: horiz ? (y1 <= 0 && nz < 0) || (y1 >= model.house.d && nz > 0) : false,
      x: horiz ? dev.x : x1 + (nx * t) / 2, z: horiz ? y1 + (nz * t) / 2 : dev.y, rot: Math.atan2(nx, nz),
    };
  }
  return best || { x: dev.x, z: dev.y, rot: PI, line: null, door: false };
}

// ---------- nhãn CSS2D (mức gas, nhiệt ẩm) ----------
const LABEL_CSS = {
  day: { pill: 'background:rgba(255,255,255,.94);color:#1f2a36;border:1px solid rgba(15,23,42,.12);box-shadow:0 1px 4px rgba(0,0,0,.2)',
    caret: 'rgba(255,255,255,.94)' },
  night: { pill: 'background:rgba(22,28,42,.86);color:#eef2f7;border:1px solid rgba(255,255,255,.16);box-shadow:0 1px 6px rgba(0,0,0,.55)',
    caret: 'rgba(22,28,42,.86)' },
};
const PILL = 'font:600 12px/1.25 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;padding:3px 9px;border-radius:999px;white-space:nowrap;';
const WARN_CSS = ';font:bold 16px sans-serif;color:#f5a524;text-shadow:0 0 2px #000,0 0 5px #000;pointer-events:none';

function css2d(el) { return new CSS2DObject(el); }

// ---------- bộ dựng theo loại ----------
// ctx: {slug, dev, model, object, y (độ cao lắp), wall(y) -> {mount, body}}; trả
// {paint(vis, night, first), tick?(dt, time, vis) -> boolean, warn: [parent, x, y, z], pin?: [parent, x, y, z], room?}
// pin = điểm mũi huy hiệu chạm (thẻ đặt huy hiệu ngay trên điểm này); nhãn (label) không có pin
const BUILD = {
  lamp(ctx) {
    const room = roomAt(ctx.model, ctx.dev.x, ctx.dev.y);
    return room || !ctx.model ? ceilingLamp(ctx, room) : porchLamp(ctx);
  },

  rgb(ctx) {
    // thanh LED nhôm gắn vách ngay trên đầu sofa (hắt màu lên tường), theo sofa của furnish.js; model chỉ ghi
    // vị trí LED trên mô hình
    const sofa = ctx.model && ctx.model.furniture.find((f) => f.kind === 'sofa');
    const at = sofa ? { x: sofa.x + sofa.w / 2, y: sofa.y + sofa.d } : ctx.dev;
    const { body } = ctx.wall(RGB_Y, at, sofa ? SOFA_TOP : 0);
    const L = sofa ? Math.min(80, sofa.w * 0.6) : 60;
    body.add(mesh(B(L, 2.4, 1.6), MAT.alu, 0, 0, 0.8));
    const ledM = glowMat(0x222222, { roughness: 0.3, name: 'dev_led' });
    body.add(mesh(B(L - 1.2, 1.1, 0.3), ledM, 0, -0.3, 1.66, false));
    // quầng màu dịu trên vách phía trên thanh, tầm ngắn, sát vách (không rọi cháy lưng sofa ngay dưới);
    // nằm trong thân: tường hạ thì trượt theo
    const light = new THREE.PointLight(0xffffff, 0, 75, 2);
    light.position.set(0, 12, 6);
    body.add(light);
    const c = new THREE.Color();
    return {
      warn: [body, 0, 8, 2],
      pin: [body, 0, 3, 1],
      paint(v, night) {
        const on = v.on && v.color;
        if (on) c.setRGB(v.color[0] / 255, v.color[1] / 255, v.color[2] / 255, THREE.SRGBColorSpace);
        const b = on ? v.brightness : 0;
        if (on) ledM.emissive.copy(c);
        ledM.emissiveIntensity = (night ? 0.9 : 0.6) * b;   // thanh hiện rõ màu, không cháy sáng
        if (on) light.color.copy(c);
        light.intensity = RGB_I * (night ? 1 : 0.3) * b;   // ban ngày quầng màu gần như chìm trong nắng (thật)
      },
    };
  },

  fan(ctx) {
    // quạt hút âm tường 40 cm thật: khung vuông, lưới tròn, 5 cánh quay phía sau lưới
    const { body } = ctx.wall(ctx.y);
    const S = 20, R = 8;
    const shape = new THREE.Shape();
    shape.moveTo(-S / 2, -S / 2); shape.lineTo(S / 2, -S / 2); shape.lineTo(S / 2, S / 2); shape.lineTo(-S / 2, S / 2);
    const hole = new THREE.Path();
    hole.absarc(0, 0, R, 0, 2 * PI, true);
    shape.holes.push(hole);
    const fg = new THREE.ExtrudeGeometry(shape, { depth: 1.4, bevelEnabled: true, bevelThickness: 0.3, bevelSize: 0.3, bevelSegments: 2, curveSegments: 32 });
    body.add(mesh(fg, MAT.plastic, 0, 0, 0.3));
    // lòng quạt tối + ống
    body.add(mesh(cylZ(R, 0.4, 32), MAT.shroud, 0, 0, 0.2, false));
    // cánh quạt
    const rotor = new THREE.Group();
    rotor.position.z = 1.1;
    rotor.add(mesh(cylZ(1.7, 1, 18), MAT.blade));
    const bg = new THREE.BoxGeometry(2.6, 6.4, 0.25);
    bg.translate(0, 4.4, 0);
    for (let i = 0; i < 5; i++) {
      const bl = mesh(bg, MAT.blade, 0, 0, 0, false);
      bl.rotation.set(0, 0.5, (i * 2 * PI) / 5, 'ZYX');
      rotor.add(bl);
    }
    body.add(rotor);
    // lưới: vòng tròn đồng tâm + nan hướng tâm, phía trước cánh
    const gz = 2.1;
    for (const r of [2.4, 4.4, 6.4]) body.add(mesh(new THREE.TorusGeometry(r, 0.18, 6, 40), MAT.plastic, 0, 0, gz, false));
    for (let i = 0; i < 4; i++) {
      const bar = mesh(B(R * 2, 0.36, 0.36), MAT.plastic, 0, 0, gz, false);
      bar.rotation.z = (i * PI) / 4;
      body.add(bar);
    }
    let speed = 0, target = 0;
    return {
      warn: [body, 0, S / 2 + 6, 3],
      pin: [body, 0, S / 2 + 1, 2],
      paint(v, night, first) {
        target = v.on ? 5 * PI : 0;
        if (first) speed = target;
      },
      tick(dt) {
        speed += (target - speed) * Math.min(1, dt * 2.5);
        if (target === 0 && speed < 0.05) { speed = 0; return false; }
        rotor.rotation.z -= speed * dt;
        return true;
      },
    };
  },

  buzzer(ctx) {
    // còi báo động: hộp trắng + chóa đỏ; đèn xoay đỏ (SpotLight quay) khi bật
    const { mount, body, sc } = ctx.wall(ctx.y);
    body.add(mesh(round(8, 8, 3, 0.8), MAT.plastic, 0, 0, 1.5));
    for (let i = -2; i <= 2; i++) body.add(mesh(B(5, 0.3, 0.2), MAT.shroud, 0, -2.6 + i * 0.5 - 0.2, 3.05, false));
    const domeM = new THREE.MeshPhysicalMaterial({ color: 0xc8141c, roughness: 0.2, clearcoat: 1, emissive: 0xff1a1a, emissiveIntensity: 0, name: 'dev_beacon' });
    const dg = new THREE.SphereGeometry(2.6, 24, 12, 0, 2 * PI, 0, PI / 2).rotateX(PI / 2);
    const dome = mesh(dg, domeM, 0, 1.3, 3, false);
    body.add(dome, mesh(cylZ(2.9, 0.6, 24), MAT.plastic, 0, 1.3, 3, false));
    // gương xoay trong chóa
    const refl = new THREE.Group();
    refl.position.set(0, 1.3, 4.2);
    refl.add(mesh(B(2.6, 1.6, 0.2), MAT.chrome, 0, 0, 0, false));
    body.add(refl);
    const spot = new THREE.SpotLight(0xff1a1a, 0, 520, 0.32, 0.55, 2);
    spot.position.set(0, 1.3 * sc, 4.5 * sc);
    mount.add(spot, spot.target);
    let ang = 0;
    const show = (on, dt) => {
      ang += on ? dt * 2 * PI * 1.1 : 0;
      refl.rotation.y = ang;
      // gương quay đủ vòng; tia chỉ quét nửa vòng phía trong phòng (sau lưng là tường), chúc xuống ~60°
      // để vệt đỏ rơi trên sàn gần còi (tường không chắn đèn này: không có bóng)
      const a = 1.0 * Math.sin(ang);
      spot.target.position.set(Math.sin(a) * 40, 1.3 * sc - 70, 4.5 * sc + Math.cos(a) * 40);
      spot.intensity = on ? BEACON_I : 0;
      domeM.emissiveIntensity = on ? 1.2 + 1.6 * Math.max(0, Math.cos(ang)) : 0;
    };
    return {
      warn: [body, 0, 8, 3],
      pin: [body, 0, 5, 3],
      paint(v) { show(v.on, 0); },
      tick(dt, time, v) { show(v.on, dt); return v.on; },
    };
  },

  pir(ctx) {
    // cảm biến chuyển động: hộp trắng + mắt Fresnel trắng sữa, LED đỏ chớp khi có người
    const { body } = ctx.wall(ctx.y);
    body.add(mesh(round(5, 6.5, 2.6, 0.6), MAT.plastic, 0, 0, 1.3));
    const eye = new THREE.SphereGeometry(1.9, 20, 10, 0, 2 * PI, 0, PI / 2).rotateX(PI / 2);
    body.add(mesh(eye, std(0xf7f6f2, { roughness: 0.3, name: 'dev_fresnel' }), 0, 0.6, 2.6, false));
    const ledM = glowMat(0xff2a1a);
    body.add(mesh(new THREE.SphereGeometry(0.35, 8, 6), ledM, 1.5, -2.3, 2.6, false));
    const show = (on, time) => { ledM.emissiveIntensity = on ? (Math.sin(time * 9) > 0 ? 4 : 0.3) : 0; };
    return {
      warn: [body, 0, 7, 3],
      pin: [body, 0, 4, 2],
      paint(v) { show(v.on, 0.1); },
      tick(dt, time, v) { show(v.on, time); return v.on; },
    };
  },

  gas: (ctx) => detector(ctx, false),
  flame: (ctx) => detector(ctx, true),

  ldr(ctx) {
    // quang trở ngoài mặt tiền: hộp trắng nhỏ, đĩa quang trở cam dưới nắp trong
    const { body } = ctx.wall(ctx.y);
    body.add(mesh(round(3.6, 4.6, 1.8, 0.4), MAT.plastic, 0, 0, 0.9));
    body.add(mesh(cylZ(1, 0.3, 16), MAT.ldr, 0, 0.6, 1.9, false));
    const ledM = glowMat(0x46ff6a);
    body.add(mesh(new THREE.SphereGeometry(0.25, 8, 6), ledM, 1, -1.6, 1.85, false));
    return { warn: [body, 0, 5, 2], pin: [body, 0, 3, 1], paint(v) { ledM.emissiveIntensity = v.on ? 3 : 0.4; } };
  },

  rfid(ctx) {
    // đầu đọc thẻ cạnh cửa (ngoài nhà): vỏ trắng, mặt đen có biểu tượng không chạm, đèn xanh chớp khi quẹt
    const { body } = ctx.wall(ctx.y);
    body.add(mesh(round(5.2, 8, 1.4, 0.5), MAT.plastic, 0, 0, 0.7));
    body.add(mesh(B(4.4, 6.2, 0.1), std(0xffffff, { map: rfidTex(), roughness: 0.25, name: 'dev_rfid_face' }), 0, -0.5, 1.42, false));
    const ledM = glowMat(0x2fe07a);
    body.add(mesh(B(3, 0.4, 0.2), ledM, 0, 3.3, 1.45, false));
    let last, flash = 0;
    const show = () => {
      const k = flash > 0 ? Math.abs(Math.sin((1.5 - flash) * PI * 3)) : 0;
      ledM.emissiveIntensity = 0.25 + k * 4;
    };
    return {
      warn: [body, 0, 7, 2],
      pin: [body, 0, 4.5, 1],
      paint(v) {
        // unavailable/unknown/rỗng: không chớp, giữ id cũ (HA khởi động lại không tính là quẹt thẻ)
        if (v.unavailable || v.text == null || v.text === 'unknown' || v.text === '') { flash = 0; show(); return; }
        if (last !== undefined && v.text !== last) flash = 1.5;
        last = v.text;
        show();
      },
      tick(dt) {
        if (flash <= 0) return false;
        flash = Math.max(0, flash - dt);
        show();
        return flash > 0;
      },
    };
  },

  label(ctx) {
    const { slug, object, dev } = ctx;
    const el = document.createElement('div');
    el.dataset.slug = slug;
    el.style.cssText = 'pointer-events:auto;cursor:pointer;display:flex;flex-direction:column;align-items:center';
    const pill = document.createElement('div'), caret = document.createElement('div');
    el.append(pill, caret);
    const o = css2d(el);
    o.center.set(0.5, 1);   // mũi nhọn chạm đúng điểm neo
    // nhãn neo trong phòng, thấp hơn đỉnh tường (KINDS.z × 1,5 = 165 nổi trên tường -> bỏ):
    // DHT: ngay trên cảm biến gắn tường; mức gas: giữa bếp cao 100
    const m = mountOf(dev, ctx.model);
    const sensor = !!m.line && slug === 'dht';
    let wp = object;
    if (sensor) {
      // nhãn ngay trên cảm biến, là con của thân -> tường hạ thì trượt theo cảm biến
      const { body } = ctx.wall(LABEL_Y_SENSOR_MOUNT);
      body.add(mesh(round(4.6, 7, 2, 0.6), MAT.plastic, 0, 0, 1));
      for (let i = 0; i < 4; i++) body.add(mesh(B(3, 0.25, 0.2), MAT.shroud, 0, 1.6 - i * 0.9, 2.02, false));
      o.position.set(0, 7.5, 1.5);
      body.add(o);
      wp = body;
    } else {
      o.position.set(dev.x, LABEL_Y, dev.y);
      object.add(o);
    }
    return {
      warn: [wp, o.position.x, o.position.y + (sensor ? 11 : 26), o.position.z],
      paint(v, night) {
        const c = LABEL_CSS[night ? 'night' : 'day'];
        pill.textContent = v.text ?? '—';
        pill.style.cssText = PILL + c.pill;
        caret.style.cssText = `width:0;height:0;border:5px solid transparent;border-top-color:${c.caret};border-bottom:0;margin-top:-1px`;
      },
    };
  },

  door({ object, model, dev }) {
    // cửa gỗ pano: 6 ô nổi hai mặt, tay nắm gạt inox hai phía, 3 bản lề; xoay vào trong nhà
    const H = (model && model.house) || { wall_h: 135, wall_t: 6 };
    const d = (model && model.doors.find((q) => q.main)) || { x_free: dev.x - 30, x_hinge: dev.x + 30, y: 0 };
    const t = H.wall_t, dh = H.door_h || Math.round(H.wall_h * 0.78);
    const s = d.x_free < d.x_hinge ? 1 : -1;   // dấu góc để cánh xoay vào trong (+y)
    const jamb = 1.2, gap = 0.3, th = 2.2;
    const w = Math.abs(d.x_hinge - d.x_free) - 2 * jamb - 2 * gap, lh = dh - jamb - gap * 2;
    const pivot = new THREE.Group();
    pivot.position.set(d.x_hinge - s * (jamb + gap), gap, d.y + t / 2);
    const wood = woodMat(), panel = panelMat(), cx = (-s * w) / 2, cz = -th / 2;
    pivot.add(mesh(B(w, lh, th), wood, cx, lh / 2, cz));
    // ô pano: 2 cột × 3 hàng mỗi mặt, mặt pano đậm hơn + nẹp chỉ quanh ô
    const pw = (w - 3 * 6) / 2, rows = [[8, 40], [45, 74], [79, lh - 7]], e = 0.7;
    for (const [y0, y1] of rows) for (const k of [-1, 1]) {
      const px = cx + k * (pw / 2 + 3), py = (y0 + y1) / 2, ph = y1 - y0;
      for (const sg of [-1, 1]) {
        const zz = cz + sg * (th / 2 + 0.15);
        pivot.add(mesh(B(pw - 2 * e, ph - 2 * e, 0.3), panel, px, py, zz, false));
        const zm = cz + sg * (th / 2 + 0.3);
        pivot.add(mesh(B(pw, e, 0.6), wood, px, y0 + e / 2, zm, false), mesh(B(pw, e, 0.6), wood, px, y1 - e / 2, zm, false));
        pivot.add(mesh(B(e, ph, 0.6), wood, px - pw / 2 + e / 2, py, zm, false), mesh(B(e, ph, 0.6), wood, px + pw / 2 - e / 2, py, zm, false));
      }
    }
    // tay nắm gạt (cao 1 m thật = 50) + đế tròn, hai mặt
    const hx = -s * (w - 4.5), hy = 50;
    for (const k of [-1, 1]) {
      const zf = cz + k * (th / 2 + 0.3);
      pivot.add(mesh(cylZ(1.3, 0.6, 20), MAT.chrome, hx, hy, zf));
      pivot.add(mesh(cylZ(0.45, 1.6, 10), MAT.chrome, hx, hy, zf + k * 0.8));
      pivot.add(mesh(B(5.5, 0.8, 0.8), MAT.chrome, hx + s * 2.6, hy, zf + k * 1.6));
      pivot.add(mesh(cylZ(0.5, 0.4, 12), MAT.black, hx, hy - 6, zf));
    }
    // bản lề
    for (const y of [12, lh / 2, lh - 12]) pivot.add(mesh(new THREE.CylinderGeometry(0.45, 0.45, 5, 10), MAT.chrome, 0, y, 0.2));
    object.add(pivot);
    let cur = 0, target = 0;
    return {
      warn: [object, (d.x_free + d.x_hinge) / 2, dh + 14, d.y],
      pin: [object, (d.x_free + d.x_hinge) / 2, dh + 1, d.y - t],   // trên đỉnh cánh, không che cánh cửa
      paint(v, night, first) {
        if (v.unavailable) return;
        target = s * v.door * (PI / 2);
        if (first) cur = target;
        pivot.rotation.y = cur;
      },
      tick(dt) {
        const diff = target - cur;
        if (Math.abs(diff) < 1e-4) { cur = target; pivot.rotation.y = cur; return false; }
        cur += Math.sign(diff) * Math.min(Math.abs(diff), (PI / 2 / 1.2) * dt);
        pivot.rotation.y = cur;
        return cur !== target;
      },
    };
  },
};

// Đèn ốp trần tròn Ø 32 cm ở tâm phòng (đèn trần thật nằm giữa phòng; model chỉ ghi vị trí LED trên mô hình).
// Nhà không có trần: ĐÊM + BẬT là đĩa sáng ấm (đổ bóng trăng xuống sàn -> thấy treo trên cao); NGÀY + BẬT chỉ vành
// sáng ấm; TẮT chỉ còn vành mảnh nhạt (không thành "cái đĩa trắng" nằm trên sofa/giường). Tầm ≈ nửa đường chéo phòng.
function ceilingLamp({ object, dev, y }, room) {
  const x = room ? room.x + room.w / 2 : dev.x, z = room ? room.y + room.d / 2 : dev.y;
  const reach = room ? Math.round(Math.hypot(room.w, room.d) * 0.5) : 300;
  const g = new THREE.Group();
  g.position.set(x, y, z);
  g.scale.setScalar(LAMP_SCALE);
  object.add(g);
  const body = new THREE.Group();
  g.add(body);
  const baseM = glowMat(0xfbe3c4, { color: 0xfbe3c4, emissive: WARM, roughness: 0.7, name: 'dev_lamp_base' });
  const difM = glowMat(0xffe2bd, { color: 0xffe2bd, emissive: WARM, roughness: 0.45, name: 'dev_lamp_diffuser' });
  body.add(mesh(new THREE.CylinderGeometry(8.4, 8.4, 1.2, 40), baseM, 0, 4, 0));
  const dg = new THREE.SphereGeometry(8, 40, 10, 0, 2 * PI, PI / 2, PI / 2);
  dg.scale(1, 0.32, 1);
  body.add(mesh(dg, difM, 0, 3.3, 0));
  // vành mảnh luôn thấy (đèn tắt: chỉ còn vành này, màu gần trần)
  const ringM = glowMat(0xd7d9dc, { color: 0xd7d9dc, emissive: WARM, roughness: 0.5, name: 'dev_lamp_ring' });
  g.add(mesh(new THREE.TorusGeometry(8.1, 0.3, 6, 48).rotateX(PI / 2), ringM, 0, 3.3, 0, false));
  // đĩa chạm nhỏ Ø 8 (không vẽ) để chạm được cả khi tắt, không lấn sang ô cửa bên dưới
  const hit = mesh(new THREE.CircleGeometry(4, 16).rotateX(-PI / 2), new THREE.MeshBasicMaterial({ visible: false }), 0, 3.3, 0, false);
  hit.userData.keepMat = true;
  g.add(hit);
  const light = new THREE.PointLight(WARM, 0, reach, 2);
  light.position.set(x, y - 6, z);
  shadowSetup(light, 512, reach);
  object.add(light);
  return {
    room: room ? room.name : null,
    warn: [g, 0, -12, 0],
    pin: [g, 0, 2, 0],
    paint(v, night) {
      // Ngày: đèn bật khó thấy ngoài trời sáng -> chỉ vành sáng ấm (đĩa đặc lúc ngày trông như cái đĩa trên đồ đạc);
      // Đêm: đĩa phát sáng
      body.visible = (v.on && night) || v.unavailable;
      ringM.emissiveIntensity = v.on ? (night ? 1.5 : 3) : 0;
      difM.emissiveIntensity = v.on ? (night ? 2.6 : 1.0) : 0;
      baseM.emissiveIntensity = v.on ? (night ? 1.2 : 0.6) : 0;
      light.intensity = v.on ? LAMP_I : 0;
      lampShadow(light, v.on);
    },
  };
}

// Đèn hiên: đèn tường ống trụ đen chiếu xuống, gắn trên lanh tô cửa chính phía ngoài; SpotLight rọi lối đi
function porchLamp(ctx) {
  const m = mountOf(ctx.dev, ctx.model);
  const H = ctx.model.house, y = m.door ? (H.door_h || 105) + 14 : ctx.y;
  const { mount, body, sc } = ctx.wall(y);
  body.add(mesh(B(4, 7, 0.8), MAT.black, 0, 0, 0.4));
  body.add(mesh(B(1, 1, 3), MAT.black, 0, 0, 2));
  body.add(mesh(new THREE.CylinderGeometry(2.4, 2.4, 9, 24), MAT.black, 0, 0, 5.2));
  const lensM = glowMat(0xfff4e0, { color: 0xfff4e0, emissive: WARM, name: 'dev_porch_lens' });
  body.add(mesh(new THREE.CylinderGeometry(2, 2, 0.3, 24), lensM, 0, -4.55, 5.2, false));
  const spot = new THREE.SpotLight(WARM, 0, 640, 0.9, 0.75, 2);
  spot.position.set(0, -4.7 * sc - 0.4, 5.2 * sc);   // ngay dưới mặt kính (thân phóng to)
  spot.target.position.set(0, -y + 2, 70);   // rọi xuống bậc thềm + lối đi
  shadowSetup(spot, 1024, 640);
  Object.assign(spot.shadow, { bias: -0.0008, normalBias: 0.6 });
  spot.shadow.camera.near = 4;
  mount.add(spot, spot.target);
  return {
    warn: [body, 0, 8, 3],
    pin: [body, 0, 4, 5],
    paint(v, night) {
      lensM.emissiveIntensity = v.on ? (night ? 3 : 1.6) : 0;
      spot.intensity = v.on ? PORCH_I : 0;
      lampShadow(spot, v.on);
    },
  };
}

// Đầu báo gas (hộp trắng có khe thoát khí) / đầu báo lửa (hộp trắng mắt hồng ngoại đen):
// LED đỏ chớp khi báo; lửa có thêm ngọn lửa trên bếp + ánh lửa
function detector(ctx, flame) {
  const { body } = ctx.wall(ctx.y);
  if (flame) {
    body.add(mesh(round(5.4, 5.4, 2.2, 0.6), MAT.plastic, 0, 0, 1.1));
    const lg = new THREE.SphereGeometry(1.4, 16, 8, 0, 2 * PI, 0, PI / 2).rotateX(PI / 2);
    body.add(mesh(lg, MAT.lens, 0, 0.3, 2.2, false));
  } else {
    body.add(mesh(round(6.4, 8.6, 2.6, 0.7), MAT.plastic, 0, 0, 1.3));
    for (let i = 0; i < 5; i++) body.add(mesh(B(4.4, 0.35, 0.2), MAT.shroud, 0, 1.8 - i * 0.9, 2.62, false));
  }
  const ledM = glowMat(0xff2020), pwrM = glowMat(0x34e06a);
  body.add(mesh(new THREE.SphereGeometry(0.35, 8, 6), ledM, -1.3, flame ? -1.9 : -3.3, flame ? 2.2 : 2.6, false));
  body.add(mesh(new THREE.SphereGeometry(0.3, 8, 6), pwrM, 1.3, flame ? -1.9 : -3.3, flame ? 2.2 : 2.6, false));
  let fire = null, fl = null;
  const flames = [];
  const st = ctx.model && ctx.model.furniture.find((f) => f.kind === 'stove');
  if (flame && st) {
    // họng đốt của bếp gas đôi (furnish.js: tâm bếp ± 9,5, mặt đá cao 45, sâu giữa dãy tủ)
    const D = ctx.model.house.d, T = ctx.model.house.wall_t, cx = st.x + st.w / 2, bz = D - T / 2 - 15 - 1;
    fire = new THREE.Group();
    ctx.object.add(fire);
    const mk = (r, h, c, x, z) => {
      const g = new THREE.ConeGeometry(r, h, 14, 1, true);
      g.translate(0, h / 2, 0);
      const m = fx(mesh(g, new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.8, depthWrite: false,
        side: THREE.DoubleSide, blending: THREE.AdditiveBlending }), x, 47, z, false));
      fire.add(m);
      flames.push(m);
    };
    for (const bx of [cx - 9.5, cx + 9.5]) { mk(4.5, 14, 0xff6a1f, bx, bz); mk(2.6, 9, 0xffc23f, bx, bz); }
    fl = new THREE.PointLight(0xff7a2a, 0, 300, 2);
    fl.position.set(cx, 62, bz - 6);
    ctx.object.add(fl);
  }
  const show = (on, time) => {
    const k = on ? (Math.sin(time * 2 * PI * 2.5) > 0 ? 1 : 0.1) : 0;
    ledM.emissiveIntensity = k * 4;
    pwrM.emissiveIntensity = 0.6;
    if (!fire) return;
    fire.visible = on;
    flames.forEach((m, i) => m.scale.set(1 + 0.12 * Math.sin(time * 17 + i), 1 + 0.3 * Math.sin(time * 13 + i * 2.1), 1));
    fl.intensity = on ? FIRE_I * (0.8 + 0.2 * Math.sin(time * 23)) : 0;
  };
  return {
    warn: [body, 0, 8, 3],
    pin: [body, 0, 4.5, 2],
    paint(v) { show(v.on, 0.1); },
    tick(dt, time, v) { show(v.on, time); return v.on; },
  };
}

/**
 * Bóng đèn trần / đèn hiên. castShadow do applyTheme đặt MỘT lần theo nền tảng (máy tính có, điện thoại không) và
 * không bao giờ đổi khi bật/tắt (đổi castShadow = three biên dịch lại mọi shader). Đèn tắt chỉ ngừng vẽ lại
 * bản đồ bóng (autoUpdate = false). Tường đang hạ không chắn ánh đèn: đèn ở tâm phòng, tầm ≈ nửa đường chéo phòng.
 */
function shadowSetup(light, size, far) {
  light.userData.shadowOK = true;
  const sh = light.shadow;
  sh.mapSize.set(size, size);
  sh.camera.near = 2;
  sh.camera.far = far;
  sh.bias = -0.004;
  sh.normalBias = 0.5;
  sh.autoUpdate = false;
  sh.needsUpdate = true;   // vẽ một lần lúc đầu: biên dịch sẵn vật liệu bóng
}
function lampShadow(light, on) {
  light.shadow.autoUpdate = !!on;
  if (on) light.shadow.needsUpdate = true;
}

// Viền vòng sáng trên mặt tường quanh thân thiết bị gắn tường (khung chữ nhật bo góc, cách thân 1,6, dày 0,95;
// tọa độ thân = cỡ thật nên viền phóng to theo thân). Nhận chạm như thân -> vùng chạm trên hình rộng hơn.
function ring(body) {
  const parent = body.parent;
  body.removeFromParent();   // thân tách riêng (biến đổi đơn vị) -> khung bao theo tọa độ thân
  const sc = body.scale.x;
  body.scale.setScalar(1);
  body.updateMatrixWorld(true);
  const b = new THREE.Box3().setFromObject(body);
  body.scale.setScalar(sc);
  parent.add(body);
  const M = 1.6, T = 0.95, cx = (b.min.x + b.max.x) / 2, cy = (b.min.y + b.max.y) / 2;
  const hw = (b.max.x - b.min.x) / 2 + M, hh = (b.max.y - b.min.y) / 2 + M;
  const rr = (shape, w, h, r) => {
    shape.moveTo(-w + r, -h); shape.lineTo(w - r, -h); shape.quadraticCurveTo(w, -h, w, -h + r);
    shape.lineTo(w, h - r); shape.quadraticCurveTo(w, h, w - r, h); shape.lineTo(-w + r, h);
    shape.quadraticCurveTo(-w, h, -w, h - r); shape.lineTo(-w, -h + r); shape.quadraticCurveTo(-w, -h, -w + r, -h);
    return shape;
  };
  const r0 = Math.min(hw, hh) * 0.45;
  const shape = rr(new THREE.Shape(), hw + T, hh + T, r0 + T);
  shape.holes.push(rr(new THREE.Path(), hw, hh, r0));
  const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: RING_IDLE, emissiveIntensity: 0.5,
    roughness: 0.5, name: 'dev_ring' });
  const m = mesh(new THREE.ShapeGeometry(shape, 6), mat, cx, cy, 0.15, false);
  m.name = 'dev_ring';
  body.add(m);
  body.userData.bottom = Math.min(b.min.y, cy - hh - T);   // đáy thân theo tọa độ thân (cỡ thật)
  return m;
}

const _c = new THREE.Color();
function paintRings(rings, kind, v, night) {
  const rgb = kind === 'rgb' && v.color, on = !v.unavailable && v.on && (ON_COLOR[kind] || rgb);
  for (const m of rings) {
    if (v.unavailable) continue;   // vật liệu xám chung (paint đã thay)
    if (on) { if (rgb) _c.setRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace); else _c.set(ON_COLOR[kind]); }
    m.material.emissive.copy(on ? _c : _c.setHex(RING_IDLE));
    m.material.color.copy(m.material.emissive).multiplyScalar(0.45);   // nền tối hơn: nắng không làm cháy kênh màu
    // ban ngày màu bão hòa (đỏ thuần) cháy kênh màu khi > 0,45 (đo test_rgb_soft_glow): bật 0,4; đêm không cháy
    m.material.emissiveIntensity = on ? (night ? 1.2 : 0.4) : (night ? 0.7 : 0.55);
  }
}

// Gốc cây cảnh (scene) chứa object
const rootOf = (o) => { while (o.parent) o = o.parent; return o; };

/**
 * syncWindows(root): kính cửa sổ của phòng có đèn bật phát sáng ấm vào ban đêm.
 * Phòng sáng = api.litRoom của thiết bị là con trực tiếp của root; cửa sổ = house.userData.windows.
 */
export function syncWindows(root) {
  const house = root.userData.house ? root : root.getObjectByName('house');
  if (!house || !house.userData.windows) return;
  const night = root.userData.theme === 'night', lit = new Set();
  for (const o of root.children) { const d = o.userData.device; if (d && d.litRoom) lit.add(d.litRoom); }
  for (const w of house.userData.windows) {
    const m = w.mesh.material, on = night && lit.has(w.room);
    m.emissive.setHex(WARM);
    m.emissiveIntensity = on ? 2.5 : 0;
    m.opacity = on ? 0.85 : w.opacity;
  }
}

/**
 * createDevice(slug, kindInfo, dev, model?, assets?) -> {object, pin, update(vis), tick(dt) -> boolean, setTheme(theme)}
 * kindInfo = KINDS[slug] (độ cao lắp = z × Z_SCALE); dev = model.devices[slug]. object là Group ở gốc tọa độ,
 * mọi con có userData.slug; mesh hiệu ứng có userData.fx và không nhận raycast.
 * pin: Object3D neo huy hiệu chạm của thẻ (null với nhãn).
 * Thiết bị gắn tường khai báo object.userData.mounts (trượt xuống mép tường khi tường hạ) = [{o, line, y0}] -> updateCutaway(scene, …) ẩn khi tường hạ.
 */
export function createDevice(slug, kindInfo, dev, model, assets) {
  const kind = kindInfo.kind;
  const object = new THREE.Group();
  object.name = slug;
  object.userData.mounts = [];
  const bodies = [];
  const ctx = {
    slug, dev, model, assets, object, y: kindInfo.z * Z_SCALE,
    // nhóm gắn tường: mount (vị trí + hướng, chứa đèn), body (hình phóng to sc lần, ẩn theo tường; tọa độ con
    // vẫn tính theo cỡ thật). Đèn trong mount nằm ngoài phần phóng to -> builder tự nhân sc.
    wall(y, at = dev, floor = 0) {
      const m = mountOf(at, model), sc = WALL_SCALE[slug] ?? WALL_SCALE[kind] ?? WALL_SCALE_DEF;
      const mount = new THREE.Group(), body = new THREE.Group();
      mount.position.set(m.x, y, m.z);
      mount.rotation.y = m.rot;
      body.scale.setScalar(sc);
      mount.add(body);
      object.add(mount);
      bodies.push(body);
      // y0 = đáy thân (tính lại sau khi dựng, gồm viền); floor = thấp nhất được trượt tới (ô cửa: đỉnh cánh cửa)
      if (m.line) object.userData.mounts.push({ o: body, line: m.line, y, y0: y, floor: m.door ? (model.house.door_h || 105) : floor });
      return { mount, body, m, sc };
    },
  };
  const ctrl = (BUILD[kind] || BUILD.label)(ctx);
  const rings = bodies.map(ring);
  // đáy thật của thân gắn tường (đã phóng to, gồm viền) -> house.updateCutaway cho trượt xuống mép tường
  for (const mt of object.userData.mounts) mt.y0 = mt.y + mt.o.userData.bottom * mt.o.scale.y;  const warn = css2d(Object.assign(document.createElement('div'), { textContent: '⚠' }));
  warn.element.style.cssText += WARN_CSS;   // giữ position:absolute của CSS2DObject (mất nó -> ⚠ nằm trong luồng, đẩy lệch cả lớp)
  const [wp, wx, wy, wz] = ctrl.warn;
  warn.position.set(wx, wy, wz);
  warn.visible = false;
  wp.add(warn);
  // điểm neo huy hiệu (Object3D rỗng, không vẽ, không raycast)
  let pin = null;
  if (ctrl.pin) {
    const [pp, px, py, pz] = ctrl.pin;
    pin = new THREE.Object3D();
    pin.position.set(px, py, pz);
    pp.add(pin);
  }
  const meshes = [];
  object.traverse((o) => {
    o.userData.slug = slug;
    if (o.isMesh && !o.userData.fx && !o.userData.keepMat) { o.userData.mat0 = o.material; meshes.push(o); }
  });
  let vis = null, theme = 'day', time = 0;
  const paint = (first) => {
    for (const o of meshes) o.material = vis.unavailable ? GRAY : o.userData.mat0;
    warn.visible = vis.unavailable;
    ctrl.paint(vis, theme === 'night', first);
    paintRings(rings, kind, vis, theme === 'night');
    const lit = ctrl.room && vis.on ? ctrl.room : null;
    if (lit !== api.litRoom) { api.litRoom = lit; if (object.parent) syncWindows(rootOf(object)); }
  };
  const api = {
    object,
    pin,
    litRoom: null,
    update(v) { const first = !vis; vis = v; paint(first); },
    tick(dt) {
      if (!vis || !ctrl.tick || (vis.unavailable && kind !== 'door')) return false;
      time += dt;
      return ctrl.tick(dt, time, vis);
    },
    setTheme(th) { theme = th; if (vis) paint(false); },
  };
  object.userData.device = api;
  return api;
}
