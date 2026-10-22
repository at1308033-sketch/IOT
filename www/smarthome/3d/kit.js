// Tiện ích dựng hình dùng chung cho house.js / furnish.js: vật liệu PBR, khối hộp UV theo mm, hộp bo góc.
// Quy ước: UV tính theo mm mô hình chia cho kích thước một ô vân (tile) -> texture dùng chung, repeat = 1, không giãn.
import * as THREE from './vendor/three.module.min.js';
import { mergeGeometries } from './vendor/BufferGeometryUtils.js';

export { THREE, mergeGeometries };

const cache = new WeakMap();   // assets -> Map(tên -> vật liệu)

/**
 * pbr(assets, name, texKey, o) -> MeshStandardMaterial (hoặc Physical nếu o.physical)
 * texKey: khóa texture trong assets (hoặc null = chỉ màu). o.use: 'all' | 'relief' (bỏ ảnh màu, giữ nor + rough).
 * userData.tile = mm của một ô vân (repeat_mm hoặc o.tile).
 */
export function pbr(assets, name, texKey, o = {}) {
  let m0 = cache.get(assets || cache);
  if (!m0) { m0 = new Map(); cache.set(assets || cache, m0); }
  if (m0.has(name)) return m0.get(name);
  const t = texKey && assets && assets.textures ? assets.textures[texKey] : null;
  const { physical, use = 'all', tile, normalScale = 1, aoMap = true, ...props } = o;
  const m = new (physical ? THREE.MeshPhysicalMaterial : THREE.MeshStandardMaterial)({ roughness: 0.8, metalness: 0, ...props });
  if (t) {
    if (use === 'all' && t.map) m.map = t.map;
    if (t.normalMap) { m.normalMap = t.normalMap; m.normalScale.setScalar(normalScale); }
    if (t.roughnessMap) m.roughnessMap = t.roughnessMap;
    if (aoMap && use === 'all' && t.aoMap) { m.aoMap = t.aoMap; m.aoMapIntensity = 0.8; }
  }
  m.name = name;
  m.userData.tile = tile || (t && t.repeat_mm) || 100;
  m0.set(name, m);
  return m;
}

// Mặt hộp: chỉ số trục pháp tuyến + dấu
const FACES = {
  px: [0, 1], nx: [0, -1], py: [1, 1], ny: [1, -1], pz: [2, 1], nz: [2, -1],
};

/**
 * Bộ gom hộp theo vật liệu. add(mat, [x0,x1], [y0,y1], [z0,z1], faces?)
 * faces: undefined = cả 6 mặt; hoặc {px: mat | [mat, màuHex] | false, ...} đổi vật liệu từng mặt / bỏ mặt;
 *   {only: ['py', ...]} chỉ dựng các mặt đó. Màu đỉnh chỉ có tác dụng với vật liệu vertexColors.
 * UV theo tọa độ thật / tile của vật liệu (cộng uvOff nếu có). build() -> mảng Mesh (mỗi vật liệu một mesh).
 */
export class Batch {
  constructor() { this.parts = new Map(); }
  add(mat, X, Y, Z, faces) {
    for (const [f, [ax, s]] of Object.entries(FACES)) {
      let m = mat, col = null;
      if (faces && f in faces) m = faces[f];
      else if (faces && faces.only) m = faces.only.includes(f) ? mat : false;
      if (Array.isArray(m)) [m, col] = m;
      if (!m) continue;
      this.quad(m, X, Y, Z, ax, s, col);
    }
    return this;
  }
  quad(mat, X, Y, Z, ax, s, col = null) {
    let p = this.parts.get(mat);
    if (!p) { p = { pos: [], nor: [], uv: [], col: [] }; this.parts.set(mat, p); }
    const cc = new THREE.Color(col ?? 0xffffff);
    const R = [X, Y, Z], tile = mat.userData.tile || 100;
    const fixed = s > 0 ? R[ax][1] : R[ax][0];
    // hai trục trong mặt: u, v (v là trục đứng nếu có)
    const [ua, va] = ax === 1 ? [0, 2] : [ax === 0 ? 2 : 0, 1];
    const corners = [[0, 0], [1, 0], [1, 1], [0, 1]];
    const pts = corners.map(([i, j]) => {
      const q = [0, 0, 0];
      q[ax] = fixed; q[ua] = R[ua][i]; q[va] = R[va][j];
      return q;
    });
    // chiều quay đúng để pháp tuyến hướng ra ngoài
    const n = [0, 0, 0]; n[ax] = s;
    const e1 = pts[1].map((v, k) => v - pts[0][k]), e2 = pts[2].map((v, k) => v - pts[0][k]);
    const c = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    const flip = c[0] * n[0] + c[1] * n[1] + c[2] * n[2] < 0;
    const order = flip ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3];
    for (const k of order) {
      const q = pts[k];
      p.pos.push(...q);
      p.nor.push(...n);
      // mặt ±x đọc u theo -z/+z sao cho vân không bị lật gương
      const u = q[ua] * (ax === 0 ? -s : ax === 2 ? s : 1);
      p.uv.push(u / tile, q[va] / tile);
      p.col.push(cc.r, cc.g, cc.b);
    }
  }
  // gộp thêm một BufferGeometry đã có (đã đặt vị trí) vào vật liệu
  geo(mat, g) {
    let p = this.parts.get(mat);
    if (!p) { p = { pos: [], nor: [], uv: [], col: [] }; this.parts.set(mat, p); }
    (p.geos ||= []).push(g.index ? g.toNonIndexed() : g);
    return this;
  }
  build({ cast = true, receive = true } = {}) {
    const out = [];
    for (const [mat, p] of this.parts) {
      const geos = (p.geos || []).map(stripTo3);
      if (p.pos.length) {
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.Float32BufferAttribute(p.pos, 3));
        g.setAttribute('normal', new THREE.Float32BufferAttribute(p.nor, 3));
        g.setAttribute('uv', new THREE.Float32BufferAttribute(p.uv, 2));
        if (mat.vertexColors) g.setAttribute('color', new THREE.Float32BufferAttribute(p.col, 3));
        geos.push(g);
      }
      const g = geos.length === 1 ? geos[0] : mergeGeometries(geos, false);
      g.computeBoundingSphere();
      const m = new THREE.Mesh(g, mat);
      m.castShadow = cast;
      m.receiveShadow = receive;
      out.push(m);
    }
    return out;
  }
}

// giữ position/normal/uv để gộp được
function stripTo3(g) {
  for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
  if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
  return g.index ? g.toNonIndexed() : g;
}

/**
 * Hộp bo góc mềm (đệm, nệm, gối) tâm ở gốc. r: bán kính bo; puff: độ phồng mặt trên/dưới (0..1).
 * UV chiếu theo trục chính của pháp tuyến, chia tile (mm).
 */
export function softBox(w, h, d, r, { seg = 6, puff = 0, tile = 20 } = {}) {
  r = Math.min(r, w / 2, h / 2, d / 2);
  const g = new THREE.BoxGeometry(w, h, d, seg, Math.max(2, seg >> 1), seg);
  const p = g.attributes.position, n = g.attributes.normal, uv = g.attributes.uv;
  const hw = w / 2 - r, hh = h / 2 - r, hd = d / 2 - r;
  const v = new THREE.Vector3(), c = new THREE.Vector3(), nn = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    c.set(THREE.MathUtils.clamp(v.x, -hw, hw), THREE.MathUtils.clamp(v.y, -hh, hh), THREE.MathUtils.clamp(v.z, -hd, hd));
    nn.subVectors(v, c);
    if (nn.lengthSq() < 1e-9) nn.fromBufferAttribute(n, i);
    nn.normalize();
    v.copy(c).addScaledVector(nn, r);
    if (puff) {
      // phồng giữa, mỏng dần ra mép (kiểu gối)
      const k = 1 - Math.pow(Math.abs(v.x) / (w / 2), 2) * 0.5 - Math.pow(Math.abs(v.z) / (d / 2), 2) * 0.5;
      v.y *= 1 - puff + puff * Math.max(0.2, k);
    }
    p.setXYZ(i, v.x, v.y, v.z);
    n.setXYZ(i, nn.x, nn.y, nn.z);
    const ax = Math.abs(nn.x), ay = Math.abs(nn.y), az = Math.abs(nn.z);
    if (ay >= ax && ay >= az) uv.setXY(i, v.x / tile, v.z / tile);
    else if (ax >= az) uv.setXY(i, v.z / tile, v.y / tile);
    else uv.setXY(i, v.x / tile, v.y / tile);
  }
  if (puff) g.computeVertexNormals();
  return g;
}

// Hộp thường có UV theo mm (dùng khi cần một BufferGeometry riêng, tâm ở gốc)
export function boxGeo(w, h, d, tile = 100) {
  const b = new Batch(), m = { userData: { tile } };
  b.add(m, [-w / 2, w / 2], [-h / 2, h / 2], [-d / 2, d / 2]);
  const p = b.parts.get(m);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p.pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(p.nor, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(p.uv, 2));
  return g;
}

// Đặt bóng đổ cho mọi mesh con
export function shadows(o, cast = true, receive = true) {
  o.traverse((m) => { if (m.isMesh) { m.castShadow = cast; m.receiveShadow = receive; } });
  return o;
}
