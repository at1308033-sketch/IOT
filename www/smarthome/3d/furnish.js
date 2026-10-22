// Nội thất thật (1 đơn vị = 20 mm thật): model glTF CC0 (sofa, bàn trà, ghế bành, kệ, tủ đầu giường, cây)
// + đồ tự dựng bằng vật liệu PBR (TV, giường đôi, tủ bếp chữ L + bếp gas, tủ lạnh, bàn ăn, thảm).
// Vị trí theo model.furniture (tv / sofa / bed / stove). Đồ gắn tường có userData.mount = {line, y0}
// để house.js ẩn khi tường đó hạ.
const V = new URL(import.meta.url).search;
const { THREE, Batch, pbr, softBox, shadows } = await import('./kit.js' + V);

const PI = Math.PI;
// Kích thước [w, d, h] (mm mô hình) của model glTF — trùng manifest, dùng cho khối dự phòng khi model thiếu
const SIZES = {
  sofa: [90, 41, 35], coffee_table: [60, 30, 20], armchair: [41, 49, 51],
  nightstand: [25, 25, 31], shelf: [54, 19, 78], plant: [35, 33, 42],
};

function mats(assets) {
  const P = (n, k, o) => pbr(assets, n, k, o);
  return {
    walnut: P('walnut', 'floor_wood', { color: 0x9a7356, roughness: 1, tile: 320, aoMap: false }),
    oak: P('oak', 'floor_wood', { color: 0xf0dcc4, roughness: 1, tile: 320, aoMap: false }),
    lacquer: P('lacquer', null, { color: 0xe9e5de, roughness: 0.45 }),
    fronts: P('fronts', null, { color: 0x7d8b7c, roughness: 0.55 }),
    dark: P('dark', null, { color: 0x2b2826, roughness: 0.8 }),
    counter: P('counter', 'countertop', { color: 0xfaf6f0, roughness: 1, tile: 520 }),
    steel: P('steel', null, { color: 0xc9ccd1, metalness: 0.85, roughness: 0.3 }),
    iron: P('iron', null, { color: 0x1b1b1c, metalness: 0.4, roughness: 0.55 }),
    blackGlass: P('black_glass', null, { physical: true, color: 0x08090b, roughness: 0.08, clearcoat: 1, clearcoatRoughness: 0.05 }),
    tvBody: P('tv_body', null, { color: 0x1c1c1e, roughness: 0.35, metalness: 0.3 }),
    linen: P('linen', 'fabric_bed', { use: 'relief', color: 0xf6f3ee, roughness: 1, tile: 14 }),
    duvet: P('duvet', 'fabric_bed', { roughness: 1, tile: 14 }),
    throwF: P('throw', 'fabric_bed', { use: 'relief', color: 0x8c7258, roughness: 1, tile: 8 }),
    uphol: P('uphol', 'fabric_bed', { use: 'relief', color: 0x9b968e, roughness: 1, tile: 9, normalScale: 1.5 }),
    shade: P('shade', 'fabric_bed', { use: 'relief', color: 0xf3e9d8, roughness: 1, tile: 6, side: THREE.DoubleSide }),
    cushion: P('cushion', 'fabric_bed', { use: 'relief', color: 0xc98b5a, roughness: 1, tile: 8 }),
    fallback: P('fallback', null, { color: 0xbdb8b0, roughness: 0.85 }),
  };
}

// Ảnh canvas -> CanvasTexture sRGB
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

// Gạch thẻ trắng ốp tường bếp (7,5 × 15 cm, ron xám nhạt); một ô vân = 4 × 8 viên = 60 × 60 cm thật
let subway = null;
function subwayMat() {
  if (subway) return subway;
  const t = canvasTex(256, 256, (g, w, h) => {
    g.fillStyle = '#c9c4bb'; g.fillRect(0, 0, w, h);
    const rows = 8, cols = 4, bh = h / rows, bw = w / cols;
    for (let r = 0; r < rows; r++) for (let c = -1; c < cols; c++) {
      const x = c * bw + (r % 2 ? bw / 2 : 0), l = 93 + Math.random() * 4;
      g.fillStyle = `hsl(40,12%,${l}%)`;
      g.fillRect(x + 1.5, r * bh + 1.5, bw - 3, bh - 3);
    }
  });
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  subway = new THREE.MeshPhysicalMaterial({ map: t, roughness: 0.25, clearcoat: 0.6, clearcoatRoughness: 0.2 });
  subway.name = 'subway';
  subway.userData.tile = 30;
  return subway;
}

// Tranh treo tường: khung gỗ mảnh + tranh trừu tượng vẽ bằng canvas (mảng màu đất, đường cong)
function artMat(seed) {
  const pal = [['#e9e1d3', '#c46f4a', '#2f4858', '#d9a95b'], ['#efe9df', '#7d8b7c', '#c9a27e', '#3b3a36']][seed % 2];
  const t = canvasTex(256, 320, (g, w, h) => {
    g.fillStyle = pal[0]; g.fillRect(0, 0, w, h);
    g.fillStyle = pal[1]; g.beginPath(); g.arc(w * 0.38, h * 0.42, w * 0.26, 0, Math.PI * 2); g.fill();
    g.fillStyle = pal[2]; g.fillRect(w * 0.5, h * 0.48, w * 0.32, h * 0.36);
    g.strokeStyle = pal[3]; g.lineWidth = 7; g.beginPath();
    g.moveTo(w * 0.1, h * 0.8); g.bezierCurveTo(w * 0.4, h * 0.55, w * 0.6, h * 0.95, w * 0.92, h * 0.68); g.stroke();
  });
  const m = new THREE.MeshStandardMaterial({ map: t, roughness: 0.85 });
  m.name = 'art' + seed;
  return m;
}

// Thảm dệt: ảnh vẽ bằng canvas (viền + hoa văn trám kiểu Berber) phủ đúng một lần lên thảm w × d,
// thêm vân nổi vải. UV của softBox theo mm (tile = 1).
const rugCache = new WeakMap();
function rugMat(assets, name, w, d, [base, line, border]) {
  const key = assets || rugCache;
  let mm = rugCache.get(key);
  if (!mm) { mm = new Map(); rugCache.set(key, mm); }
  if (mm.has(name)) return mm.get(name);
  const c = document.createElement('canvas');
  c.width = 512; c.height = Math.round((512 * d) / w);
  const g = c.getContext('2d'), W = c.width, H = c.height;
  g.fillStyle = base; g.fillRect(0, 0, W, H);
  // sợi ngẫu nhiên cho mặt thảm bớt phẳng
  for (let i = 0; i < 9000; i++) {
    g.fillStyle = `rgba(${Math.random() < 0.5 ? '255,255,255' : '0,0,0'},${0.03 + Math.random() * 0.04})`;
    g.fillRect(Math.random() * W, Math.random() * H, 1 + Math.random() * 2, 1);
  }
  g.strokeStyle = border; g.lineWidth = W * 0.022;
  g.strokeRect(W * 0.04, H * 0.06, W * 0.92, H * 0.88);
  g.strokeStyle = line; g.lineWidth = W * 0.006;
  const step = W / 9, x0 = W * 0.1, x1 = W * 0.9, y0 = H * 0.15, y1 = H * 0.85;
  g.save(); g.beginPath(); g.rect(x0, y0, x1 - x0, y1 - y0); g.clip();
  for (let k = -12; k < 24; k++) {
    g.beginPath(); g.moveTo(x0 + k * step, y0); g.lineTo(x0 + k * step + (y1 - y0), y1); g.stroke();
    g.beginPath(); g.moveTo(x0 + k * step, y1); g.lineTo(x0 + k * step + (y1 - y0), y0); g.stroke();
  }
  g.restore();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  t.repeat.set(1 / w, -1 / d);
  t.offset.set(0.5, 0.5);
  const m = new THREE.MeshStandardMaterial({ map: t, roughness: 1 });
  const f = assets && assets.textures && assets.textures.fabric_bed;
  if (f && f.normalMap) {
    m.normalMap = f.normalMap.clone();
    m.normalMap.repeat.set(1 / 5, 1 / 5);
    m.normalMap.needsUpdate = true;
    m.normalScale.setScalar(1.4);
  }
  m.name = name;
  mm.set(name, m);
  return m;
}

// Gom các Batch thành một Group có tên
function group(name, ...batches) {
  const g = new THREE.Group();
  g.name = name;
  for (const b of batches) for (const m of b.build()) g.add(m);
  return g;
}

// Model Poly Haven không cùng hướng: xoay gốc để mặt trước nhìn +z và cạnh dài theo x (đo từ ảnh gallery)
const BASE_ROT = { coffee_table: PI / 2, shelf: PI / 2 };

// Đặt bản sao model (hoặc khối dự phòng cùng cỡ) tại (x, z), quay rot quanh trục đứng (mặt trước ban đầu +z)
function place(assets, M, key, x, z, rot = 0, scale = 1) {
  const src = assets && assets.models ? assets.models[key] : null;
  const [w, d, h] = SIZES[key];
  const o = new THREE.Group();
  if (src) {
    // xoay gốc rồi co đều để lọt khung w × d × h (assets.js chỉ khớp trục lớn nhất, chưa biết hướng)
    const inner = new THREE.Group();
    inner.add(src.clone());
    inner.rotation.y = BASE_ROT[key] || 0;
    inner.updateMatrixWorld(true);
    const b = new THREE.Box3().setFromObject(inner), sz = b.getSize(new THREE.Vector3());
    const k = Math.min(w / sz.x, d / sz.z, h / sz.y);
    inner.scale.setScalar(k);
    inner.position.set(-(b.min.x + b.max.x) / 2 * k, -b.min.y * k, -(b.min.z + b.max.z) / 2 * k);
    o.add(inner);
  } else {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), M.fallback);
    m.position.y = h / 2;
    o.add(m);
    o.userData.fallback = true;
    shadows(o);
  }
  o.name = key;
  o.position.set(x, 0, z);
  o.rotation.y = rot;
  o.scale.setScalar(scale);
  return o;
}

// softBox đặt sẵn vị trí/góc (tâm cx, cy, cz)
function soft(w, h, d, r, at, o = {}) {
  const g = softBox(w, h, d, r, o);
  if (o.rz) g.rotateZ(o.rz);
  if (o.rx) g.rotateX(o.rx);
  g.translate(...at);
  return g;
}

/**
 * furnish(model, assets?) -> THREE.Group 'furniture' với các node tên: tv (con tv_panel), sofa, coffee_table,
 * armchair, shelf, rug_living, bed, nightstand(×2), rug_bed, kitchen (con kitchen_upper), plant(×2),
 * decor (tủ giày, góc làm việc, bàn ăn 4 ghế, đèn ngủ gộp chung).
 */
export function furnish(model, assets) {
  const M = mats(assets);
  const F = Object.fromEntries((model.furniture || []).map((f) => [f.kind, f]));
  const out = new THREE.Group();
  out.name = 'furniture';
  const add = (o) => { out.add(o); return o; };
  const decor = new Batch();   // tủ giày, góc làm việc, bàn ăn, đèn ngủ: gộp chung theo vật liệu

  // ---------- phòng khách ----------
  const tvF = F.tv || { x: 345, y: 4, w: 100, d: 6 };
  const sofaF = F.sofa || { x: 340, y: 140, w: 120, d: 45 };
  {
    // kệ TV thấp (gỗ óc chó, cánh sơn mờ) + TV 65" đứng trên chân đế
    const cx = tvF.x + tvF.w / 2, z0 = tvF.y - 0.5, b = new Batch();
    const x0 = cx - 46, x1 = cx + 46, top = 22;
    b.add(M.dark, [x0 + 2, x1 - 2], [0, 3], [z0 + 2, z0 + 16]);
    b.add(M.walnut, [x0, x1], [3, top], [z0, z0 + 19]);
    const n = 3, pw = (x1 - x0) / n;
    for (let i = 0; i < n; i++) b.add(M.lacquer, [x0 + i * pw + 0.3, x0 + (i + 1) * pw - 0.3], [4, top - 1], [z0 + 19, z0 + 19.5], { nz: false });
    const tv = group('tv', b);
    // tấm màn hình: thân đen + mặt kính bóng
    const p = new Batch(), sd = new Batch(), py0 = 36, pw2 = 72, ph = 41.5, pz = z0 + 7;
    sd.add(M.iron, [cx - 10, cx + 10], [top, top + 0.6], [z0 + 4, z0 + 13]);
    sd.add(M.iron, [cx - 1.5, cx + 1.5], [top + 0.6, py0 + 4], [pz - 1.2, pz]);
    tv.add(group('tv_stand', sd));
    p.add(M.tvBody, [cx - pw2 / 2, cx + pw2 / 2], [py0, py0 + ph], [pz, pz + 1.4]);
    p.add(M.blackGlass, [cx - pw2 / 2 + 0.4, cx + pw2 / 2 - 0.4], [py0 + 0.9, py0 + ph - 0.4], [pz + 1.4, pz + 1.45], { only: ['pz'] });
    const panel = group('tv_panel', p);
    tv.add(panel);
    add(tv);
  }
  {
    const cx = sofaF.x + sofaF.w / 2, cz = sofaF.y + sofaF.d / 2 + 1;
    const g = new THREE.Group();
    g.name = 'sofa';
    g.add(place(assets, M, 'sofa', cx, cz, PI));
    add(g);
    const tz = sofaF.y - 32;
    add(place(assets, M, 'coffee_table', cx, tz, 0));
    add(place(assets, M, 'armchair', sofaF.x - 22, tz - 4, PI / 2));
    // gối tựa trên sofa da (2 gối kem + 1 gối cam đất)
    const cu = new Batch();
    cu.geo(M.linen, soft(17, 15, 5, 2.4, [cx - 24, 27, cz + 4], { seg: 6, tile: 14, rx: 0.3 }));
    cu.geo(M.cushion, soft(15, 13, 5, 2.4, [cx - 10, 26.5, cz + 3.5], { seg: 6, tile: 8, rx: 0.34 }));
    cu.geo(M.linen, soft(17, 15, 5, 2.4, [cx + 24, 27, cz + 4], { seg: 6, tile: 14, rx: 0.3 }));
    g.add(...cu.build());
    // thảm dệt dưới bàn trà
    const r = new Batch(), rw = 140, rd = 84;
    r.geo(rugMat(assets, 'rug_living', rw, rd, ['#cfc5b5', '#6d6359', '#4a433d']), soft(rw, 0.6, rd, 0.3, [cx, 0.3, tz + 2], { seg: 2, tile: 1 }));
    const rug = group('rug_living', r);
    shadows(rug, false, true);
    add(rug);
  }
  add(place(assets, M, 'shelf', 165, 188 - 3 - 10, PI));
  // lối vào: tủ giày thấp sát tường trước (giữa cửa chính và cửa sổ)
  {
    const b = decor, a = 112, e = 192, z0 = 3, z1 = 19;
    for (const lx of [a + 2, e - 4]) for (const lz of [z0 + 2, z1 - 4]) b.add(M.iron, [lx, lx + 1.2], [0, 8], [lz, lz + 1.2]);
    b.add(M.lacquer, [a, e], [8, 40], [z0, z1]);
    b.add(M.oak, [a - 0.5, e + 0.5], [40, 41.5], [z0, z1 + 0.5]);
    for (let i = 0; i < 2; i++) b.add(M.oak, [a + i * 40 + 0.3, a + (i + 1) * 40 - 0.3], [8.5, 39.5], [z1, z1 + 0.5], { nz: false });
  }
  // góc làm việc sát tường trái: bàn gỗ, ghế, đèn bàn, laptop
  {
    const b = decor, x0 = 3, x1 = 33, z0 = 40, z1 = 112, ty = 37.5;
    b.add(M.oak, [x0, x1], [ty - 1.6, ty], [z0, z1]);
    for (const lz of [z0 + 2, z1 - 3.4]) {
      b.add(M.iron, [x0 + 2, x1 - 2], [0, 1.2], [lz, lz + 1.4]);
      b.add(M.iron, [x1 - 4, x1 - 2.6], [0, ty - 1.6], [lz, lz + 1.4]);
      b.add(M.iron, [x0 + 2, x0 + 3.4], [0, ty - 1.6], [lz, lz + 1.4]);
    }
    b.add(M.tvBody, [x0 + 12, x0 + 28], [ty, ty + 0.6], [z0 + 30, z0 + 52]);
    b.add(M.tvBody, [x0 + 12, x0 + 13], [ty, ty + 14], [z0 + 30, z0 + 52]);
    b.geo(M.lacquer, new THREE.CylinderGeometry(2.5, 2.5, 0.8, 16).translate(x0 + 8, ty + 0.4, z0 + 12));
    b.geo(M.iron, new THREE.CylinderGeometry(0.4, 0.4, 16, 8).translate(x0 + 8, ty + 8, z0 + 12));
    b.geo(M.shade, new THREE.CylinderGeometry(2.5, 4.5, 6, 18, 1, true).translate(x0 + 9, ty + 15, z0 + 12));
    // ghế xoay: chân sao, đệm, lưng
    const cx = x1 + 12, cz = (z0 + z1) / 2, sb = decor;
    for (let k = 0; k < 5; k++) sb.geo(M.iron, new THREE.BoxGeometry(11, 1.2, 1.6).translate(5.5, 1.5, 0).rotateY((k * 2 * PI) / 5).translate(cx, 0, cz));
    sb.geo(M.steel, new THREE.CylinderGeometry(0.9, 0.9, 20, 10).translate(cx, 11, cz));
    sb.geo(M.uphol, soft(22, 3.4, 22, 1.4, [cx, 22, cz], { seg: 4, tile: 9 }));
    sb.geo(M.uphol, soft(3, 22, 20, 1.4, [cx + 10, 36, cz], { seg: 4, tile: 9, rz: -0.12 }));
  }
  add(place(assets, M, 'plant', 474, 27, 0.6));

  // ---------- phòng ngủ: giường đôi đầu giường tựa tường phải ----------
  const bedF = F.bed || { x: 375, y: 215, w: 120, d: 100 };
  {
    const x0 = bedF.x, x1 = bedF.x + bedF.w, z0 = bedF.y, z1 = bedF.y + bedF.d;
    const zc = (z0 + z1) / 2, hb = x1 - 5;           // đầu giường dày 10 cm sát tường
    const wood = new Batch(), fab = new Batch();
    for (const [lx, lz] of [[x0 + 3, z0 + 3], [x0 + 3, z1 - 6], [hb - 6, z0 + 3], [hb - 6, z1 - 6]]) wood.add(M.walnut, [lx, lx + 3], [0, 4], [lz, lz + 3]);
    wood.add(M.walnut, [x0 + 1, hb], [4, 15], [z0 + 1, z1 - 1]);
    fab.geo(M.uphol, soft(5, 56, bedF.d + 4, 1.6, [hb + 2.5, 30, zc], { seg: 6, tile: 9 }));
    // nệm
    fab.geo(M.linen, soft(hb - x0 - 4, 11, bedF.d - 6, 2.5, [(x0 + 2 + hb - 2) / 2, 20.5, zc], { seg: 8, tile: 14 }));
    // chăn phủ 2/3 giường rủ xuống hai bên + mép gấp trắng
    const dx1 = hb - 26;
    fab.geo(M.duvet, soft(dx1 - x0 + 1, 15, bedF.d - 1, 3, [(x0 - 0.5 + dx1) / 2, 21.5, zc], { seg: 10, tile: 14, puff: 0.05 }));
    fab.geo(M.linen, soft(9, 4, bedF.d - 1.5, 1.8, [dx1 + 3, 28, zc], { seg: 6, tile: 14 }));
    // khăn choàng cuối giường
    fab.geo(M.throwF, soft(18, 1.8, bedF.d + 0.5, 0.8, [x0 + 12, 29.6, zc], { seg: 6, tile: 8 }));
    // 2 gối tựa đầu giường
    for (const pzc of [zc - 23, zc + 23]) fab.geo(M.linen, soft(14, 7, 40, 3.2, [hb - 9, 31.5, pzc], { seg: 8, tile: 14, puff: 0.55, rz: -0.38 }));
    const bed = group('bed', wood, fab);
    add(bed);
    // tủ đầu giường + đèn ngủ
    const lampB = decor;
    for (const nz of [z0 - 12.5, z1 + 13]) {
      const ns = add(place(assets, M, 'nightstand', hb - 12, nz, -PI / 2, 0.92));
      ns.name = 'nightstand';
      const ty = SIZES.nightstand[2] * 0.92;
      const base = new THREE.CylinderGeometry(2.2, 3, 7, 16).translate(hb - 13, ty + 3.5, nz);
      lampB.geo(M.lacquer, base);
      lampB.geo(M.shade, new THREE.CylinderGeometry(4.5, 6, 8, 20, 1, true).translate(hb - 13, ty + 10, nz));
    }
    // thảm cạnh giường
    const r = new Batch();
    r.geo(rugMat(assets, 'rug_bed', 84, 130, ['#b8aa98', '#8d7f6f', '#e9e1d4']), soft(84, 0.6, 130, 0.3, [x0 + 12, 0.3, zc], { seg: 2, tile: 1 }));
    const rug = group('rug_bed', r);
    shadows(rug, false, true);
    add(rug);
  }
  add(place(assets, M, 'plant', 240, 337, 2.1, 0.85));

  // ---------- bếp: tủ chữ L (tường sau + tường trái), mặt đá, bếp gas âm, chậu rửa, tủ lạnh ----------
  const st = F.stove || { x: 60, y: 305, w: 70, d: 47 };
  {
    const D = model.house.d, T = model.house.wall_t, back = D - T / 2, left = T / 2;
    const dep = 30, top = 43, ct = 2, kick = 4;
    const fz = back - dep, lx = left + dep - 1;   // mặt trước dãy sau (z) / dãy trái (x)
    const kx1 = 200, kz0 = 228;                    // đầu dãy sau / đầu dãy trái
    const c = new Batch(), fr = c, mt = c;   // một bộ gom: mỗi vật liệu một draw call
    // chân tủ lùi vào, thân tủ, mặt đá nhô 2 cm
    c.add(M.dark, [left, kx1 - 1], [0, kick], [fz + 2, back]);
    c.add(M.dark, [left, lx - 2], [0, kick], [kz0 + 1, fz + 2]);
    c.add(M.lacquer, [left, kx1], [kick, top], [fz, back], { ny: false });
    c.add(M.lacquer, [left, lx], [kick, top], [kz0, fz], { ny: false });
    c.add(M.counter, [left, kx1 + 1], [top, top + ct], [fz - 1, back], { ny: false });
    c.add(M.counter, [left, lx + 1], [top, top + ct], [kz0 - 1, fz - 1], { ny: false });
    // cánh tủ dãy sau: chia ô, chừa chỗ lò nướng dưới bếp
    const cx = st.x + st.w / 2, ow = 36;
    const cuts = [lx, cx - ow / 2 - 22, cx - ow / 2, cx + ow / 2, cx + ow / 2 + 28.5, cx + ow / 2 + 57, kx1];
    for (let i = 0; i < cuts.length - 1; i++) {
      const a = cuts[i] + 0.25, b = cuts[i + 1] - 0.25;
      if (i === 2) {
        // lò nướng: mặt kính đen + tay nắm inox
        c.add(M.blackGlass, [a, b], [kick + 1, top - 1], [fz - 0.6, fz], { pz: false });
        mt.add(M.steel, [a + 3, b - 3], [top - 5, top - 4.2], [fz - 2, fz - 1.2]);
        continue;
      }
      fr.add(M.fronts, [a, b], [kick + 0.5, top - 0.5], [fz - 0.6, fz], { pz: false });
      mt.add(M.steel, [(a + b) / 2 - 5, (a + b) / 2 + 5], [top - 4, top - 3.3], [fz - 1.6, fz - 0.6]);
    }
    // cánh dãy trái (mặt hướng +x)
    const zc = [kz0, kz0 + 31, kz0 + 63, fz];
    for (let i = 0; i < zc.length - 1; i++) {
      const a = zc[i] + 0.25, b = zc[i + 1] - 0.25;
      fr.add(M.fronts, [lx, lx + 0.6], [kick + 0.5, top - 0.5], [a, b], { nx: false });
      mt.add(M.steel, [lx + 0.6, lx + 1.6], [top - 4, top - 3.3], [(a + b) / 2 - 5, (a + b) / 2 + 5]);
    }
    // bếp gas đôi âm mặt đá: mặt kính đen, 2 họng đốt + kiềng gang
    const by = top + ct, bz = fz + dep / 2;
    c.add(M.blackGlass, [cx - 19, cx + 19], [by, by + 0.5], [bz - 11, bz + 11], { ny: false });
    for (const bx of [cx - 9.5, cx + 9.5]) {
      mt.geo(M.steel, new THREE.CylinderGeometry(3.4, 3.6, 0.7, 24).translate(bx, by + 0.85, bz - 1));
      mt.geo(M.iron, new THREE.CylinderGeometry(2.2, 2.2, 0.6, 20).translate(bx, by + 1.4, bz - 1));
      for (let k = 0; k < 4; k++) {
        const bar = new THREE.BoxGeometry(6.5, 0.8, 0.8).translate(4.6, by + 1.6, 0).rotateY((k * PI) / 2 + PI / 4);
        mt.geo(M.iron, bar.translate(bx, 0, bz - 1));
      }
      mt.geo(M.iron, new THREE.TorusGeometry(7.2, 0.45, 6, 28).rotateX(PI / 2).translate(bx, by + 1.6, bz - 1));
      mt.geo(M.steel, new THREE.CylinderGeometry(1.1, 1.1, 1, 14).translate(bx, by + 0.9, bz + 8.5));
    }
    // chậu rửa inox + vòi ở dãy trái
    const sz = kz0 + 42;
    mt.add(M.steel, [left + 6, lx - 3], [by, by + 0.25], [sz - 15, sz + 15], { ny: false });
    c.add(M.iron, [left + 8, lx - 5], [by + 0.25, by + 0.3], [sz - 13, sz + 13], { only: ['py'] });
    mt.add(M.steel, [left + 3, left + 5], [by, by + 13], [sz - 1, sz + 1]);
    mt.add(M.steel, [left + 3, left + 12], [by + 11.5, by + 13], [sz - 0.8, sz + 0.8]);
    // tủ lạnh inox 2 cánh (cao 1,84 m) ở đầu dãy trái
    const kr = (model.rooms || []).find((r) => /BẾP/i.test(r.name));
    const fz0 = (kr ? kr.y : 188) + T / 2 + 0.5;
    mt.add(M.steel, [left, left + 33], [0, 92], [fz0, fz0 + 33]);
    c.add(M.dark, [left + 33, left + 33.2], [62, 62.4], [fz0 + 0.5, fz0 + 32.5], { only: ['px'] });
    mt.add(M.iron, [left + 33, left + 34.2], [48, 60], [fz0 + 28, fz0 + 29.2]);
    mt.add(M.iron, [left + 33, left + 34.2], [66, 80], [fz0 + 28, fz0 + 29.2]);
    const k = group('kitchen', c);
    // gạch ốp tường sau và tường trái từ mặt đá tới tủ trên (ẩn theo tường khi tường hạ)
    const bs = new Batch(), sub = subwayMat();
    bs.add(sub, [left, kx1], [top + ct, 78], [back - 0.4, back], { only: ['nz'] });
    const bsb = group('backsplash_back', bs);
    bsb.userData.mount = { line: 'h' + D, y0: top + ct };
    k.add(bsb);
    const bl = new Batch();
    bl.add(sub, [left, left + 0.4], [top + ct, 70], [kz0, back - 0.4], { only: ['px'] });
    const bsl = group('backsplash_left', bl);
    bsl.userData.mount = { line: 'v0', y0: top + ct };
    k.add(bsl);
    // tủ trên + máy hút mùi treo tường sau: ẩn khi tường sau hạ
    const u = new Batch(), uy0 = 78, uy1 = 116, ud = 16;
    for (const [a, b] of [[left, cx - 22], [cx + 22, kx1]]) {
      u.add(M.lacquer, [a, b], [uy0, uy1], [back - ud, back]);
      const n = Math.max(1, Math.round((b - a) / 26)), w = (b - a) / n;
      for (let i = 0; i < n; i++) u.add(M.fronts, [a + i * w + 0.25, a + (i + 1) * w - 0.25], [uy0 + 0.5, uy1 - 0.5], [back - ud - 0.6, back - ud], { pz: false });
    }
    u.add(M.steel, [cx - 19, cx + 19], [uy0 + 4, uy0 + 9], [back - 24, back]);
    u.add(M.steel, [cx - 7, cx + 7], [uy0 + 9, model.house.wall_h - 0.5], [back - 13, back]);
    const upper = group('kitchen_upper', u);
    upper.userData.mount = { line: 'h' + D, y0: uy0 };
    k.add(upper);
    add(k);
  }
  // bàn ăn 4 ghế giữa bếp
  {
    const cx = 128, cz = 258, b = decor, s = decor;
    b.add(M.oak, [cx - 30, cx + 30], [36, 37.6], [cz - 20, cz + 20]);
    for (const [x, z] of [[cx - 27, cz - 17], [cx + 25, cz - 17], [cx - 27, cz + 15], [cx + 25, cz + 15]]) b.add(M.walnut, [x, x + 2], [0, 36], [z, z + 2]);
    for (const [x, dz] of [[cx - 14, -1], [cx + 14, -1], [cx - 14, 1], [cx + 14, 1]]) {
      const z = cz + dz * 26;
      for (const [lx, lz] of [[-8, -8], [6.6, -8], [-8, 6.6], [6.6, 6.6]]) b.add(M.walnut, [x + lx, x + lx + 1.4], [0, 22], [z + lz, z + lz + 1.4]);
      s.geo(M.uphol, soft(19, 2.2, 19, 0.9, [x, 23, z], { seg: 4, tile: 9 }));
      const bz = z + dz * 8.6;
      b.add(M.walnut, [x - 8, x + 8], [24, 42], [bz - 0.8, bz + 0.8]);
    }
  }
  // tranh: trên đầu giường (tường phải) và cạnh bàn ăn (mặt bếp của tường x = 220)
  const W = model.house.w, T = model.house.wall_t;
  const art = (seed, line, X, Y, Z, face) => {
    const b = new Batch(), mt = artMat(seed);
    mt.userData.tile = 1;
    b.add(M.walnut, X, Y, Z);
    const [ax, s] = face;   // trục pháp tuyến + dấu: mặt tranh nhô 0,1 khỏi khung
    const X2 = X.slice(), Z2 = Z.slice();
    if (ax === 'x') X2[s > 0 ? 1 : 0] += s * 0.1; else Z2[s > 0 ? 1 : 0] += s * 0.1;
    const inset = (r) => [r[0] + 1.2, r[1] - 1.2];
    const meshes = b.build();
    const pic = new Batch();
    pic.add(mt, ax === 'x' ? X2 : inset(X), inset(Y), ax === 'z' ? Z2 : inset(Z), { only: [(s > 0 ? 'p' : 'n') + ax] });
    const g = new THREE.Group();
    g.name = 'art';
    g.add(...meshes, ...pic.build({ cast: false }));
    // UV tranh: phủ đúng một lần
    const pm = g.children[g.children.length - 1], uv = pm.geometry.attributes.uv;
    let u0 = Infinity, u1 = -Infinity, v0 = Infinity, v1 = -Infinity;
    for (let i = 0; i < uv.count; i++) { u0 = Math.min(u0, uv.getX(i)); u1 = Math.max(u1, uv.getX(i)); v0 = Math.min(v0, uv.getY(i)); v1 = Math.max(v1, uv.getY(i)); }
    for (let i = 0; i < uv.count; i++) uv.setXY(i, (uv.getX(i) - u0) / (u1 - u0), (uv.getY(i) - v0) / (v1 - v0));
    g.userData.mount = { line, y0: Y[0] };
    add(g);
  };
  const bz = bedF.y + bedF.d / 2;
  art(0, 'v' + W, [W - T / 2 - 1.6, W - T / 2], [64, 100], [bz - 34, bz - 4], ['x', -1]);
  art(1, 'v' + W, [W - T / 2 - 1.6, W - T / 2], [64, 100], [bz + 4, bz + 34], ['x', -1]);
  art(1, 'v220', [220 - T / 2 - 1.6, 220 - T / 2], [56, 96], [243, 273], ['x', -1]);
  // đèn sàn cạnh sofa
  {
    const lx = sofaF.x + sofaF.w - 8, lz = sofaF.y + sofaF.d - 12;
    decor.geo(M.iron, new THREE.CylinderGeometry(6, 6.5, 1.2, 24).translate(lx, 0.6, lz));
    decor.geo(M.iron, new THREE.CylinderGeometry(0.5, 0.5, 70, 8).translate(lx, 35, lz));
    decor.geo(M.shade, new THREE.CylinderGeometry(6, 8, 11, 24, 1, true).translate(lx, 72, lz));
  }
  add(group('decor', decor));
  return out;
}
