// Vỏ nhà thật (1 đơn vị = 1 mm mô hình = 20 mm thật): móng, sàn, tường hai mặt có ô cửa, cửa sổ kính,
// sân cỏ + lối đi lát đá, tường tự hạ kiểu The Sims (updateCutaway). Nội thất dựng ở furnish.js.
// Trục: mặt bằng (x, y) -> three (x, cao, y); tường trước y = 0 (ngoài nhà y < 0).
const V = new URL(import.meta.url).search;
const { THREE, Batch, pbr, softBox } = await import('./kit.js' + V);
const { furnish } = await import('./furnish.js' + V);

export const CUT = 25;          // chiều cao tường khi hạ
const CUT_TIME = 0.25;          // giây cho một lần hạ / nâng hết
const TOP_DEG = 25;             // camera gần thẳng đứng hơn góc này -> mọi tường cao đủ
const CREAM = 0xe6dcc6;         // màu đỉnh tường (lát cắt)
const GROUND_Y = -8;            // mặt cỏ thấp hơn sàn nhà 16 cm

// Vật liệu của vỏ nhà (cache theo assets)
function mats(assets) {
  const P = (n, k, o) => pbr(assets, n, k, o);
  return {
    // sơn nước trong nhà: bỏ ảnh màu xám của vữa, chỉ giữ độ nhám + vân nổi; đỉnh tường tô màu kem (vertex color)
    plaster: P('plaster', 'wall_plaster', { use: 'relief', color: 0xf3eee6, roughness: 1, normalScale: 0.35, vertexColors: true }),
    exterior: P('exterior', 'wall_exterior', { color: 0xf1e8da, roughness: 1, normalScale: 0.8 }),
    plinth: P('plinth', 'wall_exterior', { color: 0x9c958b, roughness: 1, tile: 60 }),
    wood: P('floor_wood', 'floor_wood', { roughness: 1 }),
    tile: P('floor_tile', 'floor_tile_kitchen', { roughness: 1 }),
    grass: P('grass', 'grass', { color: 0xffffff, roughness: 1, vertexColors: true }),
    hedge: P('hedge', 'grass', { color: 0x6f9550, roughness: 1, tile: 40, normalScale: 2 }),
    paving: P('paving', 'paving', { color: 0xd8d0c6, roughness: 1 }),
    trim: P('trim', null, { color: 0xf6f4ef, roughness: 0.45 }),
    frame: P('win_frame', null, { color: 0xf2f2f0, roughness: 0.35 }),
    sill: P('win_sill', 'countertop', { color: 0xf2efe8, roughness: 0.6, tile: 120, use: 'relief' }),
    glass: P('glass', null, {
      // kính trong suốt phản chiếu môi trường; KHÔNG dùng transmission (three vẽ lại toàn bộ vật đục
      // vào render target mỗi khung khi cửa sổ trong khung nhìn: +~95 draw call, nhìn gần như không khác)
      physical: true, color: 0xeaf4f8, roughness: 0.04, metalness: 0, ior: 1.5, specularIntensity: 1,
      transparent: true, opacity: 0.2, envMapIntensity: 1.4, depthWrite: false,
    }),
  };
}

const lo = Math.min, hi = Math.max;

// Bãi cỏ lớn chia lưới: màu đỉnh loang (vệt sáng/tối vài mét) để vân lặp 2 m không lộ thành ô
function lawn(mat, W, D) {
  const S = 4200, n = 60, geo = new THREE.PlaneGeometry(S, S, n, n);
  geo.rotateX(-Math.PI / 2);
  geo.translate(W / 2, GROUND_Y, D / 2);
  const p = geo.attributes.position, uv = geo.attributes.uv, col = new Float32Array(p.count * 3);
  const tile = mat.userData.tile || 100;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i);
    uv.setXY(i, x / tile, -z / tile);
    const k = 0.5 + 0.25 * Math.sin(x * 0.011 + 1.3) * Math.cos(z * 0.009) + 0.25 * Math.sin((x + z) * 0.004 + 0.7);
    // xanh tươi hơn ảnh gốc (cỏ lá khô), loang sáng tối
    col[i * 3] = 0.5 + 0.14 * k; col[i * 3 + 1] = 0.8 + 0.16 * k; col[i * 3 + 2] = 0.42 + 0.1 * k;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const m = new THREE.Mesh(geo, mat);
  m.name = 'ground';
  m.receiveShadow = true;
  return m;
}

/**
 * buildHouse(model, assets?) -> THREE.Group 'house' (gồm cả nội thất của furnish).
 * userData.walls: [{mesh, x1, y1, x2, y2}] theo đúng thứ tự model.walls; mỗi mesh.userData.wall = true,
 * mesh.userData.h = chiều cao hiện tại. userData.cutaway: trạng thái cho updateCutaway.
 */
export function buildHouse(model, assets) {
  const H = model.house, T = H.wall_t, WH = H.wall_h, DH = H.door_h || Math.round(WH * 0.78);
  const W = H.w, D = H.d, t2 = T / 2;
  const M = mats(assets);
  const g = new THREE.Group();
  g.name = 'house';
  g.userData.house = true;
  g.userData.mats = [];   // giữ tương thích applyTheme bản 1 (không đổi màu vật liệu PBR)

  // ---- các "đường tường" (cùng phương + cùng tọa độ) chia chung trạng thái hạ ----
  const lines = new Map();
  const lineOf = (horiz, c) => {
    const key = (horiz ? 'h' : 'v') + c;
    if (!lines.has(key)) {
      const ext = horiz ? (c <= 0 ? -1 : c >= D ? 1 : 0) : (c <= 0 ? -1 : c >= W ? 1 : 0);
      const up = new THREE.Group();          // phần trên CUT của ô cửa/lanh tô/cửa sổ, co theo scale.y
      up.name = 'upper_' + key;
      up.position.y = CUT;
      g.add(up);
      lines.set(key, { key, horiz, c, ext, H: WH, target: WH, walls: [], uppers: [up], mounted: [], extra: new Batch() });
    }
    return lines.get(key);
  };

  // mặt của tường theo phía: ngoài nhà -> vữa ngoài, trong -> sơn; đỉnh màu kem
  const top = [M.plaster, CREAM];
  const sideFaces = (horiz, ext) => {
    const inner = M.plaster, f = { py: top, ny: false };
    if (horiz) { f.nz = ext < 0 ? M.exterior : inner; f.pz = ext > 0 ? M.exterior : inner; } else { f.nx = ext < 0 ? M.exterior : inner; f.px = ext > 0 ? M.exterior : inner; }
    return f;
  };
  // dựng hộp tường [a,b] dọc đường, cao [y0,y1]; tách phần dưới CUT (cố định) và phần trên (co giãn)
  const span = (horiz, c, a, b) => (horiz ? [[a, b], [c - t2, c + t2]] : [[c - t2, c + t2], [a, b]]);
  function wallPiece(low, up, horiz, c, ext, a, b, y0, y1, ends) {
    const [X, Z] = span(horiz, c, a, b);
    const f = { ...sideFaces(horiz, ext), ...ends };
    if (y0 < CUT) low.add(M.plaster, X, [y0, lo(y1, CUT)], Z, f);   // đỉnh kem luôn có: lộ ra khi phần trên ẩn
    if (y1 > CUT) up.add(M.plaster, X, [hi(y0, CUT), y1], Z, { ...f, ny: y0 >= CUT ? f.ny : false });
  }

  // ---- tường theo model.walls (đầu tường: nối góc chữ L kéo dài, chữ T thu lại như bản 1) ----
  const walls = model.walls;
  const hor = walls.filter((w) => w[1] === w[3]), ver = walls.filter((w) => w[0] === w[2]);
  const hEnd = (x, y) => {
    for (const v of ver) {
      if (v[0] !== x || y < lo(v[1], v[3]) || y > hi(v[1], v[3])) continue;
      return y === v[1] || y === v[3] ? 1 : -1;
    }
    return 0;
  };
  const vEnd = (x, y) => (hor.some((h) => h[1] === y && x >= lo(h[0], h[2]) && x <= hi(h[0], h[2])) ? 1 : 0);
  const stat = new Batch();      // phần cố định: sàn, móng, chân tường, nẹp, bậu dưới CUT
  const skirt = (horiz, c, ext, a, b) => {
    // len chân tường (cao 10 cm, dày 1,6 cm) ở mặt trong
    for (const s of [-1, 1]) {
      if (ext === s) continue;
      const f = c + s * t2;
      const Z = [lo(f, f + s * 0.8), hi(f, f + s * 0.8)];
      if (horiz) stat.add(M.trim, [a, b], [0, 5], Z, { ny: false });
      else stat.add(M.trim, Z, [0, 5], [a, b], { ny: false });
    }
  };
  g.userData.walls = [];
  for (const w of walls) {
    const [x1, y1, x2, y2] = w;
    const horiz = y1 === y2, c = horiz ? y1 : x1;
    const L = lineOf(horiz, c);
    let a, b, ends = {};
    if (horiz) {
      const ea = hEnd(lo(x1, x2), y1), eb = hEnd(hi(x1, x2), y1);
      a = lo(x1, x2) - (ea * T) / 2; b = hi(x1, x2) + (eb * T) / 2;
      // đầu tường ở góc nhà -> mặt ngoài; giữa nhà (ô cửa) -> sơn; chỗ nối tường khác -> mặt cắt màu kem.
      // Mặt nối luôn dựng: khi tường bên cạnh hạ, đầu tường này lộ ra (không có mặt sẽ nhìn xuyên qua).
      // Mặt này úp vào mặt tường bên cạnh, ngược chiều -> bị cull, không z-fight.
      ends.nx = ea === -1 ? top : a <= -t2 + 0.01 ? M.exterior : M.plaster;
      ends.px = eb === -1 ? top : b >= W + t2 - 0.01 ? M.exterior : M.plaster;
    } else {
      const ea = vEnd(x1, lo(y1, y2)), eb = vEnd(x1, hi(y1, y2));
      a = lo(y1, y2) + (ea * T) / 2; b = hi(y1, y2) - (eb * T) / 2;
      ends.nz = ea ? top : M.plaster;
      ends.pz = eb ? top : M.plaster;
    }
    const low = new Batch(), up = new Batch();
    wallPiece(low, up, horiz, c, L.ext, a, b, 0, WH, ends);
    const grp = new THREE.Group();
    grp.name = 'wall';
    grp.userData.wall = true;
    grp.userData.h = WH;
    for (const m of low.build()) grp.add(m);
    const upG = new THREE.Group();
    upG.position.y = CUT;
    for (const m of up.build()) { m.geometry.translate(0, -CUT, 0); upG.add(m); }
    grp.add(upG);
    g.add(grp);
    L.walls.push(grp);
    L.uppers.push(upG);
    g.userData.walls.push({ mesh: grp, x1, y1, x2, y2 });
    skirt(horiz, c, L.ext, a, b);
  }

  // ---- ô cửa đi: lanh tô + khuôn cửa sơn trắng (đố + nẹp hai mặt) ----
  const trimSplit = (L, X, Y, Z, faces) => {
    if (Y[0] < CUT) stat.add(M.trim, X, [Y[0], lo(Y[1], CUT)], Z, faces);
    if (Y[1] > CUT) L.extra.add(M.trim, X, [hi(Y[0], CUT), Y[1]], Z, faces);
  };
  for (const d of model.doors) {
    const L = lineOf(true, d.y), a = lo(d.x_free, d.x_hinge), b = hi(d.x_free, d.x_hinge), c = d.y;
    wallPiece(stat, L.extra, true, c, L.ext, a, b, DH, WH, { nx: false, px: false, ny: M.plaster });
    const Zj = [c - t2 - 0.3, c + t2 + 0.3];
    trimSplit(L, [a, a + 1.2], [0, DH], Zj, { ny: false });
    trimSplit(L, [b - 1.2, b], [0, DH], Zj, { ny: false });
    trimSplit(L, [a, b], [DH - 1.2, DH], Zj);
    for (const s of [-1, 1]) {
      // nẹp khuôn (architrave) 6 cm, nhô 1,6 cm ở mỗi mặt tường
      const f = c + s * t2, Z = [lo(f, f + s * 0.8), hi(f, f + s * 0.8)];
      trimSplit(L, [a - 3, a], [0, DH + 3], Z, { ny: false });
      trimSplit(L, [b, b + 3], [0, DH + 3], Z, { ny: false });
      trimSplit(L, [a, b], [DH, DH + 3], Z);
    }
  }

  // ---- cửa sổ: tường dưới bậu, lanh tô, bậu đá, khung nhôm trắng 2 cánh + kính ----
  const win = model.window;
  if (win) {
    const L = lineOf(true, win.y), c = win.y, a = win.x1, b = win.x2;
    wallPiece(stat, L.extra, true, c, L.ext, a, b, 0, win.sill, { nx: false, px: false });
    wallPiece(stat, L.extra, true, c, L.ext, a, b, win.top, WH, { nx: false, px: false, ny: M.plaster });
    const s = L.ext || -1;   // phía ngoài nhà
    // bậu trong (nhô vào phòng) + bậu ngoài (thấp hơn, nhô ra)
    L.extra.add(M.sill, [a - 3, b + 3], [win.sill, win.sill + 1.4], [lo(c, c - s * (t2 + 2.5)), hi(c, c - s * (t2 + 2.5))]);
    L.extra.add(M.sill, [a - 1, b + 1], [win.sill - 1.6, win.sill + 0.2], [lo(c, c + s * (t2 + 2.5)), hi(c, c + s * (t2 + 2.5))]);
    // khung: viền 3 cm quanh ô, đố giữa
    const fy0 = win.sill + 1.4, fy1 = win.top, Zf = [c - 1.6, c + 1.6], fw = 2.2, mid = (a + b) / 2;
    const fr = (X, Y) => L.extra.add(M.frame, X, Y, Zf);
    fr([a, a + fw], [fy0, fy1]); fr([b - fw, b], [fy0, fy1]);
    fr([a, b], [fy0, fy0 + fw]); fr([a, b], [fy1 - fw, fy1]);
    fr([mid - fw / 2, mid + fw / 2], [fy0, fy1]);
    // cánh: khung cánh mảnh + kính
    for (const [x0, x1] of [[a + fw, mid - fw / 2], [mid + fw / 2, b - fw]]) {
      const Zs = [c - 1.1, c + 1.1], k = 1.2;
      L.extra.add(M.frame, [x0, x0 + k], [fy0 + fw, fy1 - fw], Zs);
      L.extra.add(M.frame, [x1 - k, x1], [fy0 + fw, fy1 - fw], Zs);
      L.extra.add(M.frame, [x0, x1], [fy0 + fw, fy0 + fw + k], Zs);
      L.extra.add(M.frame, [x0, x1], [fy1 - fw - k, fy1 - fw], Zs);
      L.extra.add(M.glass, [x0 + k, x1 - k], [fy0 + fw + k, fy1 - fw - k], [c - 0.2, c + 0.2], { only: ['pz', 'nz'] });
    }
  }

  // phần trên của từng đường (lanh tô, cửa sổ) -> một nhóm co giãn
  // userData.windows: [{mesh, room, opacity}] kính cửa sổ (vật liệu riêng) để devices.js cho phát sáng khi phòng bật đèn
  g.userData.windows = [];
  for (const L of lines.values()) {
    const up = L.uppers[0];
    for (const m of L.extra.build()) {
      m.geometry.translate(0, -CUT, 0);
      if (m.material === M.glass) {
        m.castShadow = false;
        m.renderOrder = 1;
        m.material = M.glass.clone();
        const r = win && model.rooms.find((q) => (win.x1 + win.x2) / 2 >= q.x && (win.x1 + win.x2) / 2 <= q.x + q.w
          && win.y + 1 >= q.y && win.y + 1 <= q.y + q.d);
        g.userData.windows.push({ mesh: m, room: r ? r.name : null, opacity: m.material.opacity });
      }
      up.add(m);
    }
    delete L.extra;
  }

  // ---- sàn theo phòng (gỗ; bếp lát gạch), móng, sân ----
  for (const r of model.rooms) {
    const m = /BẾP/i.test(r.name) ? M.tile : M.wood;
    stat.add(m, [r.x, r.x + r.w], [-1, 0], [r.y, r.y + r.d], { only: ['py'] });
  }
  // móng nhà: gờ bê tông lộ 16 cm quanh nhà
  stat.add(M.plinth, [-t2 - 3, W + t2 + 3], [GROUND_Y, -0.4], [-t2 - 3, D + t2 + 3], { ny: false });
  // bậc thềm + lối đi lát đá từ cửa chính ra trước
  const main = model.doors.find((d) => d.main) || model.doors[0];
  if (main) {
    const a = lo(main.x_free, main.x_hinge), b = hi(main.x_free, main.x_hinge);
    stat.add(M.paving, [a - 14, b + 14], [GROUND_Y, -3], [-t2 - 3 - 34, -t2 - 3], { ny: false });
    stat.add(M.paving, [a - 4, b + 4], [GROUND_Y, GROUND_Y + 0.8], [-420, -t2 - 3 - 34], { ny: false, pz: false });
  }
  for (const m of stat.build()) {
    m.name = 'static_' + m.material.name;
    // sàn/sân chỉ nhận bóng
    if ([M.wood, M.tile, M.paving].includes(m.material)) m.castShadow = false;
    g.add(m);
  }
  g.add(lawn(M.grass, W, D));
  // hàng rào cây bụi thấp (40 cm) trước mặt tiền, chừa lối đi
  if (main) {
    const b = hi(main.x_free, main.x_hinge) + 18, z = -t2 - 3 - 9;
    const hedge = new Batch();
    for (const [a1, b1] of [[b, W + t2 + 3]]) {
      for (let x = a1; x < b1 - 1; x += 46) {
        const x2 = Math.min(b1, x + 46);
        hedge.geo(M.hedge, softBox(x2 - x + 4, 20, 14, 5, { seg: 6, tile: 30, puff: 0.15 }).translate((x + x2) / 2, GROUND_Y + 9, z));
      }
    }
    for (const m of hedge.build()) { m.name = 'hedge'; g.add(m); }
  }

  // ---- nội thất (furnish) + đồ gắn tường ẩn theo tường ----
  const fur = furnish(model, assets);
  g.add(fur);
  fur.traverse((o) => {
    const mt = o.userData.mount;
    if (mt && lines.has(mt.line)) lines.get(mt.line).mounted.push({ o, y0: mt.y0 ?? CUT });
  });

  const cx = W / 2, cz = D / 2;
  g.userData.cutaway = { lines: [...lines.values()], cx, cz, WH, T, started: false, last: null };
  return g;
}

const _p = new THREE.Vector3(), _d = new THREE.Vector3();

// Đường tường có "che" camera không (xem quy tắc ở updateCutaway)
const N_H = [0, 1], N_V = [1, 0];   // pháp tuyến ngang (x, z) của đường tường

function facing(L, px, pz, C) {
  const n = L.horiz ? N_H : N_V;
  const pc = L.horiz ? pz : px;              // tọa độ camera theo pháp tuyến
  if (L.ext) return (pc - L.c) * L.ext > 0;  // tường ngoài: camera ở phía ngoài
  // tường trong: hướng ngang camera -> tâm nhà cắt ngang tường (không song song) và camera không đứng sát tường
  const dx = C.cx - px, dz = C.cz - pz, len = Math.hypot(dx, dz) || 1;
  const dot = Math.abs((dx * n[0] + dz * n[1]) / len);
  return dot > 0.5 && Math.abs(pc - L.c) > C.T;
}

/**
 * updateCutaway(root, camera, dt?) -> boolean (true khi còn tường đang chuyển).
 * Quy tắc: hướng nhìn camera gần thẳng đứng (lệch < 25°) -> mọi tường cao đủ (đọc như mặt bằng).
 * Ngược lại: tường ngoài hạ xuống 25 khi camera ở phía ngoài của tường đó; tường trong hạ khi hướng nhìn ngang
 * của camera tới tâm nhà cắt ngang nó (|cos| > 0,5) — tức nó nằm giữa camera và các phòng phía xa.
 * Nội suy tuyến tính ~0,25 s (dt giây; bỏ trống -> tự đo thời gian thật). Lần gọi đầu đặt ngay, không hoạt ảnh.
 * Chỉ đổi scale.y / visible, không dựng lại hình học.
 */
export function updateCutaway(root, camera, dt) {
  let C = root.userData.cutaway;
  if (!C) {
    const h = root.userData._cutRoot || root.getObjectByName('house');
    if (!h || !h.userData.cutaway) return false;
    root.userData._cutRoot = h;
    C = h.userData.cutaway;
  }
  const now = performance.now() / 1000;
  if (dt == null) dt = C.last == null ? 0 : Math.min(0.1, now - C.last);
  C.last = now;
  // thiết bị gắn tường (devices.js: object.userData.mounts = [{o, line, y0, floor}]) là con trực tiếp của root:
  // quét lại khi root hoặc số con đổi
  if (C.scanRoot !== root || C.scanN !== root.children.length) {
    C.scanRoot = root;
    C.scanN = root.children.length;
    const byKey = new Map(C.lines.map((L) => [L.key, L]));
    for (const L of C.lines) L.devMounts = [];
    for (const o of root.children) {
      for (const m of o.userData.mounts || []) if (byKey.has(m.line)) byKey.get(m.line).devMounts.push(m);
    }
  }
  camera.getWorldPosition(_p);
  camera.getWorldDirection(_d);
  const topView = -_d.y > Math.cos((TOP_DEG * Math.PI) / 180);   // hướng nhìn lệch phương thẳng đứng < 25°
  const speed = (C.WH - CUT) / CUT_TIME;
  let moving = false;
  for (const L of C.lines) {
    L.target = topView || !facing(L, _p.x, _p.z, C) ? C.WH : CUT;
    if (!C.started) L.H = L.target;
    else if (L.H !== L.target) {
      const d = L.target - L.H, step = speed * dt;
      L.H = Math.abs(d) <= step ? L.target : L.H + Math.sign(d) * step;
    }
    if (L.H !== L.target) moving = true;
    const s = (L.H - CUT) / (C.WH - CUT);
    for (const u of L.uppers) { u.scale.y = Math.max(1e-4, s); u.visible = s > 1e-3; }
    for (const w of L.walls) w.userData.h = L.H;
    for (const m of L.mounted) m.o.visible = L.H >= m.y0;
    // thiết bị gắn tường (devices.js) không ẩn: trượt xuống cho đáy ngồi trên mép tường (ô cửa: không dưới floor)
    for (const m of L.devMounts) m.o.position.y = Math.min(0, Math.max(L.H, m.floor || 0) + 1 - m.y0);
  }
  C.started = true;
  return moving;
}
