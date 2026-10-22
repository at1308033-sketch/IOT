// Nạp texture + model CC0 (Poly Haven) theo assets/manifest.json. Không bao giờ reject.
import * as THREE from './vendor/three.module.min.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

// Chuỗi ?v=... của chính module này, gắn vào manifest và file tài nguyên để phá cache sau khi deploy.
const V = new URL(import.meta.url).search;
const url = (rel) => new URL('./assets/' + rel + V, import.meta.url).href;

let cached = null;

/**
 * loadAssets(onProgress) -> Promise<{textures, models, failed}>
 * - textures[key] = {map, normalMap, roughnessMap, metalnessMap, aoMap, repeat_mm}; map thiếu = null.
 *   Texture dùng chung: nơi dùng muốn repeat khác phải .clone() (clone vẫn chia sẻ ảnh) rồi tự đặt .repeat.
 * - models[key] = THREE.Group tên key, đã scale đồng đều về size_mm, đáy y=0, tâm x/z=0 (dùng .clone()).
 * - failed = key lỗi (mỗi key một lần) hoặc ['manifest'].
 * onProgress(done, total) gọi sau mỗi file (thành công hay lỗi); total = số file texture + số model.
 * Kết quả được cache ở mức module: lần gọi thứ hai trả cùng Promise, onProgress mới bị bỏ qua.
 */
export function loadAssets(onProgress) {
  if (!cached) cached = run(onProgress || (() => {}));
  return cached;
}

const FILE_KEYS = ['diff', 'nor', 'arm', 'rough'];

async function run(onProgress) {
  const out = { textures: {}, models: {}, failed: [] };
  let man;
  try {
    const r = await fetch(url('manifest.json'));
    if (!r.ok) throw new Error(String(r.status));
    man = await r.json();
  } catch (e) {
    return { textures: {}, models: {}, failed: ['manifest'] };
  }
  const texDefs = man.textures || {}, modelDefs = man.models || {};
  const total = Object.values(texDefs).reduce((n, t) => n + FILE_KEYS.filter(f => t[f]).length, 0)
    + Object.keys(modelDefs).length;
  let done = 0;
  const tick = () => { try { onProgress(++done, total); } catch (e) { /* bỏ qua lỗi của callback */ } };
  const fail = (k) => { if (!out.failed.includes(k)) out.failed.push(k); };

  const texLoader = new THREE.TextureLoader();
  const loadTex = (key, rel, srgb) => texLoader.loadAsync(url(rel)).then(t => {
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 4;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }).catch(() => { fail(key); return null; }).finally(tick);

  const jobs = [];
  for (const [key, def] of Object.entries(texDefs)) {
    const e = { map: null, normalMap: null, roughnessMap: null, metalnessMap: null, aoMap: null, repeat_mm: def.repeat_mm };
    out.textures[key] = e;
    if (def.diff) jobs.push(loadTex(key, def.diff, true).then(t => { e.map = t; }));
    if (def.nor) jobs.push(loadTex(key, def.nor, false).then(t => { e.normalMap = t; }));
    if (def.arm) jobs.push(loadTex(key, def.arm, false).then(t => { e.aoMap = t; e.roughnessMap = t; e.metalnessMap = t; }));
    if (def.rough) jobs.push(loadTex(key, def.rough, false).then(t => { if (t) e.roughnessMap = t; }));
  }

  // Lưu ý: .bin/texture tham chiếu tương đối trong glTF được GLTFLoader phân giải theo thư mục của URL glTF, nên mất ?v (chấp nhận).
  const gl = new GLTFLoader();
  for (const [key, def] of Object.entries(modelDefs)) {
    jobs.push(gl.loadAsync(url(def.gltf)).then(g => fitModel(key, g.scene, def.size_mm))
      .catch(() => { fail(key); return null; }).finally(tick).then(m => { out.models[key] = m; }));
  }
  await Promise.all(jobs);
  return out;
}

// Scale đồng đều: kích thước lớn nhất của size_mm khớp trục tương ứng (x=w, z=d, y=h); đáy y=0, tâm x/z=0.
function fitModel(key, scene, size) {
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(scene);
  const s = box.getSize(new THREE.Vector3());
  const have = [s.x, s.z, s.y];
  const i = [0, 1, 2].reduce((a, j) => (size[j] > size[a] ? j : a), 0);
  const k = have[i] > 0 ? size[i] / have[i] : 1;
  const inner = new THREE.Group();
  inner.add(scene);
  inner.scale.setScalar(k);
  inner.position.set(-(box.min.x + box.max.x) / 2 * k, -box.min.y * k, -(box.min.z + box.max.z) / 2 * k);
  const g = new THREE.Group();
  g.name = key;
  g.add(inner);
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}
