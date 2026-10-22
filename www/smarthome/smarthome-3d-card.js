// Thẻ Lovelace "smarthome-3d-card": mô hình 3D nhà thật (three.js r170, bản 2), chạm để điều khiển thiết bị.
// Nạp: HA tải /local/smarthome/smarthome-3d-card.js?v=<mã băm>; logic/scene/assets/model kèm cùng ?v,
// vendor thì KHÔNG kèm (để trùng đúng URL module mà scene.js import -> chỉ một bản three).
const V = new URL(import.meta.url).search;
const url = (p, keepV) => { const u = new URL(p, import.meta.url); u.search = keepV ? V : ''; return u.href; };

let LIBS = null;
const loadLibs = () => (LIBS ??= Promise.all([
  import(url('./3d/vendor/three.module.min.js')),
  import(url('./3d/vendor/OrbitControls.js')),
  import(url('./3d/vendor/CSS2DRenderer.js')),
  import(url('./3d/logic.js', true)),
  import(url('./3d/scene.js', true)),
  import(url('./3d/assets.js', true)),
  fetch(url('./3d/model3d.json', true)).then((r) => {
    if (!r.ok) throw new Error('model3d.json HTTP ' + r.status);
    return r.json();
  }),
]).then(([THREE, oc, c2d, L, S, A, model]) => (
  { THREE, OrbitControls: oc.OrbitControls, CSS2DRenderer: c2d.CSS2DRenderer, CSS2DObject: c2d.CSS2DObject, L, S, A, model }
)).catch((e) => { LIBS = null; throw e; }));

// Hậu kỳ cho máy tính (GTAO): chỉ nạp khi cần
let POST = null;
const loadPost = () => (POST ??= Promise.all(
  ['EffectComposer', 'RenderPass', 'GTAOPass', 'OutputPass'].map((n) => import(url(`./3d/vendor/${n}.js`))),
).then(([ec, rp, gp, op]) => (
  { EffectComposer: ec.EffectComposer, RenderPass: rp.RenderPass, GTAOPass: gp.GTAOPass, OutputPass: op.OutputPass }
)).catch((e) => { POST = null; throw e; }));

const TARGET = [250, 0, 178];
const MODES = [['day', '☀️', 'Ngày'], ['night', '🌙', 'Đêm'], ['auto', '🌓', 'Tự động', true]];
const VIEWS = [['overview', '🏠', 'Toàn cảnh'], ['living', '🛋️', 'Phòng khách'], ['kitchen', '🍳', 'Bếp'],
  ['bedroom', '🛏️', 'Phòng ngủ'], ['top', '🗺️', 'Từ trên']];
const ROOM_OF = { living: 'PHÒNG KHÁCH', kitchen: 'BẾP', bedroom: 'PHÒNG NGỦ' };
const BAR = [['temp', '🌡️', ''], ['hum', '💧', ''], ['gas', '💨', 'Gas'], ['power', '⚡', '']];
const HOLD_MS = 500, MOVE_PX = 6, TWEEN_MS = 800, NARROW = 600, MOBILE_W = 700;
// Camera mặc định cho tường cao (tường che camera tự hạ): Toàn cảnh và Từ trên
const OVERVIEW = [250, 700, -340], TOP = [250, 1000, 238];
// Huy hiệu chạm của mỗi thiết bị (trừ nhãn): luôn hiện, mũi chỉ vào thiết bị (kể cả khi thiết bị trượt theo tường hạ)
const CHIP_IC = { lamp: '💡', rfid: '💳', ldr: '🌗', buzzer: '🔔', pir: '👁️', gas: '💨', flame: '🔥', fan: '🌀', rgb: '🌈', door: '🚪' };

// localStorage có thể bị chặn (chế độ riêng tư, iframe) -> luôn bọc try/catch
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* bỏ qua */ } },
};
const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const shown = (o) => { for (; o; o = o.parent) if (!o.visible) return false; return true; };
// Màn hẹp (dọc) -> mở rộng góc nhìn để cả nhà lọt khung theo chiều ngang
const fovFor = (a) => (a >= 1.2 ? 38 : Math.min(60, (2 * Math.atan(Math.tan((19 * Math.PI) / 180) * 1.2 / a) * 180) / Math.PI));

const CSS = `
:host{display:block;height:var(--sh3d-h,calc(100vh - 120px));min-height:360px}
.wrap{position:relative;width:100%;height:100%;overflow:hidden;box-sizing:border-box;
  border-radius:var(--ha-card-border-radius,12px);background:var(--card-background-color,#fff);
  color:var(--primary-text-color,#1f2a37);font-family:var(--ha-font-family-body,Roboto,system-ui,sans-serif);
  user-select:none;-webkit-user-select:none;-webkit-tap-highlight-color:transparent;
  --ov-bg:rgba(255,255,255,.86);--ov-fg:#1f2a37;--ov-bd:rgba(20,30,50,.12);--ov-act:#1e6fd9;--ov-act-fg:#fff;--ov-mut:#5b6675}
.wrap[data-theme=night]{--ov-bg:rgba(8,16,36,.8);--ov-fg:#d8f6ff;--ov-bd:rgba(56,225,255,.38);
  --ov-act:#38e1ff;--ov-act-fg:#04121e;--ov-mut:#8fb4c8}
.stage{position:absolute;inset:0}
.stage canvas{display:block;outline:none}
.top,.bottom{position:absolute;left:8px;right:8px;display:flex;justify-content:space-between;gap:6px;
  flex-wrap:wrap;pointer-events:none}
.top{top:8px;align-items:flex-start}
.bottom{bottom:8px;align-items:flex-end}
.grp,.bar{display:flex;flex-wrap:wrap;gap:2px;padding:3px;border-radius:18px;background:var(--ov-bg);
  border:1px solid var(--ov-bd);box-shadow:0 2px 10px rgba(0,0,0,.14);pointer-events:auto;
  backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
button{font:inherit;color:inherit;background:none;border:0;margin:0;cursor:pointer}
.grp button,.bar button{padding:5px 10px;border-radius:15px;font-size:13px;line-height:18px;color:var(--ov-fg);
  white-space:nowrap;display:flex;align-items:center;gap:4px}
.grp button:hover,.bar button:hover{background:rgba(127,127,127,.16)}
.grp button.active{background:var(--ov-act);color:var(--ov-act-fg);font-weight:600}
button:focus-visible{outline:2px solid var(--ov-act);outline-offset:1px}
.bar button{font-size:12.5px;padding:4px 8px}
.bar .tx{color:var(--ov-mut)}
.bar b{font-weight:600;font-variant-numeric:tabular-nums}
.dot{width:9px;height:9px;border-radius:50%;background:#9aa0a6;flex:none}
.dot.ok{background:#22c55e;box-shadow:0 0 6px #22c55e}
.dot.bad{background:#ef4444;box-shadow:0 0 6px #ef4444}
.alarm{pointer-events:auto;background:#e53935;color:#fff;font-weight:700;font-size:14px;padding:8px 16px;
  border-radius:20px;box-shadow:0 2px 10px rgba(0,0,0,.25);animation:pulse 1.2s infinite}
.alarm[hidden],.tip[hidden],.msg[hidden],.loading[hidden],.note[hidden]{display:none}
.loading{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);display:flex;flex-direction:column;
  align-items:center;gap:9px;min-width:210px;padding:14px 20px;border-radius:14px;pointer-events:none;
  background:var(--ov-bg);color:var(--ov-fg);border:1px solid var(--ov-bd);box-shadow:0 4px 18px rgba(0,0,0,.16);
  font-size:14px;font-weight:600;font-variant-numeric:tabular-nums}
.pbar{width:100%;height:4px;border-radius:2px;background:var(--ov-bd);overflow:hidden}
.pbar i{display:block;height:100%;width:0;background:var(--ov-act);transition:width .2s}
.note{position:absolute;left:50%;bottom:50px;transform:translateX(-50%);max-width:calc(100% - 24px);
  padding:3px 10px;border-radius:10px;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  background:var(--ov-bg);color:var(--ov-mut);border:1px solid var(--ov-bd);pointer-events:none}
.chip{pointer-events:none;display:flex;flex-direction:column;align-items:center}
.chip button{pointer-events:auto;touch-action:none;position:relative;width:32px;height:32px;padding:0;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:16px;line-height:1;background:var(--ov-bg);color:var(--ov-fg);
  border:2px solid var(--ov-bd);box-shadow:0 2px 8px rgba(0,0,0,.28);transition:transform .12s,background .2s}
.chip button::before{content:'';position:absolute;inset:-5px;border-radius:50%}
.css2d>*{position:absolute!important;left:0;top:0}
.chip s{width:2px;height:var(--lift,0px);background:var(--ov-fg);opacity:.55;flex:none;transition:height .18s ease-out}
.chip i{width:0;height:0;border:6px solid transparent;border-top-color:var(--ov-bg);border-bottom:0;margin-top:-1px;
  filter:drop-shadow(0 1px 1px rgba(0,0,0,.25))}
.chip:hover button{transform:scale(1.12)}
.chip.on button{background:#fff;border:3px solid var(--c);box-shadow:0 0 0 2px rgba(255,255,255,.85),0 0 14px var(--c)}
.chip.on i{border-top-color:var(--c)}
.chip.na button{filter:grayscale(1);opacity:.6;border-style:dashed}
.chip.na::after{content:'⚠';position:absolute;right:-5px;top:-6px;font:bold 13px sans-serif;color:#f5a524;
  text-shadow:0 0 2px #000,0 0 4px #000}
.narrow .chip button{width:28px;height:28px;font-size:14px}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(229,57,53,.75)}70%{box-shadow:0 0 0 12px rgba(229,57,53,0)}
  100%{box-shadow:0 0 0 0 rgba(229,57,53,0)}}
@media (prefers-reduced-motion:reduce){.alarm{animation:none}.chip s{transition:none}}
.tip{position:absolute;left:0;top:0;pointer-events:none;transform:translate(-50%,calc(-100% - 16px));
  background:var(--ov-bg);color:var(--ov-fg);border:1px solid var(--ov-bd);padding:4px 10px;border-radius:8px;
  font-size:13px;font-weight:600;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;
  padding:24px;font-size:15px;color:var(--primary-text-color,#333)}
.failed .top,.failed .bottom,.failed .loading{display:none}
.ic.nar{display:none}
.narrow .tx{display:none}
.narrow .ic.nar{display:inline}
.narrow .grp button{padding:5px 8px}
.narrow .bar button{padding:4px 6px}
.narrow .alarm{font-size:13px;padding:7px 12px}
`;

const btn = ([key, ic, tx, nar], attr) =>
  `<button data-${attr}="${key}" title="${tx}" aria-label="${tx}"><span class="ic${nar ? ' nar' : ''}">${ic}</span>` +
  `<span class="tx">${tx}</span></button>`;

class Smarthome3DCard extends HTMLElement {
  constructor() {
    super();
    this._cfg = { demo: false };
    this._devs = {};
    this._objs = [];
    this._over = {};        // ghi đè trạng thái của chế độ demo
    this._raf = 0;
    this._extra = 0;
    this._mode = ['day', 'night', 'auto'].includes(store.get('smarthome3d.mode')) ? store.get('smarthome3d.mode') : 'auto';
    const v = store.get('smarthome3d.view');
    this._view = VIEWS.some((x) => x[0] === v) ? v : 'overview';
    this._atView = this._view;
    this.ready = new Promise((r) => { this._resolveReady = r; });
    const root = this.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>${CSS}</style><style class="hcss"></style>
<div class="wrap" data-theme="day">
  <div class="stage"></div>
  <div class="top">
    <div class="grp modes" role="group" aria-label="Chế độ hiển thị">${MODES.map((m) => btn(m, 'mode')).join('')}</div>
    <div class="grp views" role="group" aria-label="Góc nhìn">${VIEWS.map((m) => btn(m, 'view')).join('')}</div>
  </div>
  <div class="bottom">
    <div class="bar">
      <button data-k="link" title="Kết nối ESP32"><i class="dot"></i><span class="tx">ESP32</span></button>
      ${BAR.map(([k, ic, tx]) => `<button data-k="${k}"><span class="ic">${ic}</span>${tx ? `<span class="tx">${tx}</span>` : ''}<b>—</b></button>`).join('')}
    </div>
    <button class="alarm" hidden>🔕 Tắt báo động</button>
  </div>
  <div class="loading" role="status"><span class="lt">Đang tải mô hình…</span><div class="pbar"><i></i></div></div>
  <div class="note" hidden></div>
  <div class="tip" hidden></div>
  <div class="msg" hidden></div>
</div>`;
    const $ = (s) => root.querySelector(s);
    this._wrap = $('.wrap');
    this._stage = $('.stage');
    this._tip = $('.tip');
    this._msg = $('.msg');
    this._alarmBtn = $('.alarm');
    this._hcss = $('.hcss');
    this._loading = $('.loading');
    this._note = $('.note');
    this._ptrs = new Set();  // pointerId đang chạm trên sân khấu (chặn đa điểm)
    this._chips = {};        // slug -> CSS2DObject chip
    root.querySelectorAll('[data-mode]').forEach((b) => b.addEventListener('click', () => this._setMode(b.dataset.mode)));
    root.querySelectorAll('[data-view]').forEach((b) => b.addEventListener('click', () => this._setView(b.dataset.view)));
    root.querySelectorAll('.bar [data-k]').forEach((b) => b.addEventListener('click', () => {
      if (this._lib) this._fireMoreInfo(this._lib.L.STATUS[b.dataset.k]);
    }));
    this._alarmBtn.addEventListener('click', () => this._silence());
    this._marks();
  }

  // ---------- API Lovelace ----------
  setConfig(config) {
    const c = config || {};
    const demo = !!c.demo, flip = demo !== this._cfg.demo;
    this._cfg = { demo, height: c.height ? String(c.height) : null };
    const h = this._cfg.height && this._cfg.height.replace(/[;{}<>]/g, '');
    this._hcss.textContent = h ? `:host{--sh3d-h:${h}}` : '';
    // bật/tắt demo -> bỏ mọi ghi đè demo, áp lại trạng thái thật
    if (flip) {
      this._over = {};
      if (this._built) this._apply();
    }
  }

  set hass(h) {
    this._hass = h;
    if (this._built) this._apply();
  }

  get hass() { return this._hass; }

  getCardSize() { return 8; }

  // ---------- thuộc tính cho test ----------
  get loopRunning() { return this._raf !== 0; }

  get renderer() { return this._renderer; }

  get mode() { return this._mode; }

  get theme() { return this._theme; }

  get mobile() { return this._mobile; }

  // Điểm chạm của thiết bị (px tính từ góc trên-trái của thẻ): huy hiệu nếu đang hiện, nhãn DOM nếu có,
  // không thì tâm khung bao (world) chiếu lên màn hình. hit = slug thật sự nhận chạm tại điểm đó;
  // down = thiết bị (gắn tường) đang trượt xuống theo tường hạ.
  debug(slug) {
    const d = this._devs[slug];
    if (!d) return null;
    const hr = this.getBoundingClientRect();
    const chip = !!(this._chips[slug] && this._chips[slug].visible);
    const el = chip ? this._chips[slug].element.firstChild : this._stage.querySelector(`[data-slug="${slug}"]:not(.chip)`);
    const er = el && el.getBoundingClientRect();
    let x, y;
    if (er && er.width && er.height) {
      x = er.left + er.width / 2 - hr.left;
      y = er.top + er.height / 2 - hr.top;
    } else {
      const { THREE } = this._lib;
      this._scene.updateMatrixWorld();
      const box = new THREE.Box3(), b = new THREE.Box3();
      d.api.object.traverse((o) => {
        if (!o.isMesh || o.userData.fx || !shown(o)) return;
        if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
        box.union(b.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld));
      });
      const c = box.getCenter(new THREE.Vector3()).project(this._camera);
      const r = this._renderer.domElement.getBoundingClientRect();
      // lệch 0,5 px: tia đi đúng đỉnh tâm của đĩa chạm (quạt tam giác) có thể trượt mọi tam giác
      x = ((c.x + 1) / 2) * r.width + r.left - hr.left + 0.5;
      y = ((1 - c.y) / 2) * r.height + r.top - hr.top + 0.5;
    }
    return { screen: [x, y], vis: d.vis, chip, down: chip && this._chips[slug].userData.down,
      hit: this._hitAt(hr.left + x, hr.top + y) };
  }

  // ---------- vòng đời ----------
  connectedCallback() {
    this._connected = true;
    if (!this._started) {
      this._started = true;
      this._build();
    } else if (this._built) {
      this._ro.observe(this._wrap);
      this._kick();
    }
  }

  disconnectedCallback() {
    this._connected = false;
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
    this._last = 0;
    if (this._ro) this._ro.disconnect();
    this._cancelPress();
    this._ptrs.clear();
  }

  _fail(text) {
    this._loading.hidden = true;
    this._msg.textContent = text;
    this._msg.hidden = false;
    this._wrap.classList.add('failed');
    this._resolveReady();
  }

  // Dựng cảnh MỘT lần cho mỗi phần tử (texture canvas không giải phóng được) và dùng lại khi gắn lại
  async _build() {
    let lib;
    try {
      lib = await loadLibs();
    } catch (e) {
      console.warn('smarthome-3d-card:', e);
      this._fail('Không tải được mô hình 3D');
      return;
    }
    const { THREE, OrbitControls, CSS2DRenderer, L, S, A, model } = lib;
    const canvas = document.createElement('canvas');
    let gl = null;
    try { gl = canvas.getContext('webgl2', { antialias: true }); } catch { gl = null; }
    if (!gl) { this._fail('Trình duyệt không hỗ trợ WebGL'); return; }
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, context: gl, antialias: true });
    } catch (e) {
      console.warn('smarthome-3d-card:', e);
      this._fail('Trình duyệt không hỗ trợ WebGL');
      return;
    }
    // Điện thoại: màn chạm hoặc thẻ hẹp < 700 px -> vẽ thẳng, pixel ratio <= 1,5, đèn điểm không đổ bóng.
    // Quyết định MỘT lần lúc dựng (đổi cỡ qua ngưỡng sau đó vẫn giữ nguyên).
    const coarse = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
    const mobile = coarse || (this._wrap.clientWidth || window.innerWidth) < MOBILE_W;
    this._mobile = mobile;
    // texture + model: thanh tải "N/M" (loadAssets không bao giờ reject)
    const assets = await A.loadAssets((n, m) => this._progress(n, m));
    this._lib = lib;
    S.setupRenderer(renderer, { mobile });   // trước applyTheme (PMREM + cờ điện thoại)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile ? 1.5 : 2));
    renderer.info.autoReset = false;          // đếm draw call cả khung (reset ở _draw)
    const css = new CSS2DRenderer();
    css.domElement.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none';
    css.domElement.className = 'css2d';
    this._stage.append(canvas, css.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1.5, 10, 6000);
    scene.add(S.buildHouse(model, assets));
    for (const [slug, dev] of Object.entries(model.devices)) {
      const info = L.KINDS[slug];
      if (!info) continue;
      const api = S.createDevice(slug, info, dev, model, assets);
      scene.add(api.object);
      this._objs.push(api.object);
      this._devs[slug] = { api, dev, kind: info.kind, ids: info.entities || [dev.entity], vis: null, key: null };
    }
    this._makeChips(lib, scene);
    // Máy tính: EffectComposer (RenderPass -> GTAO -> OutputPass); lỗi (thiếu WebGL2...) -> vẽ thẳng, im lặng
    if (!mobile) {
      try {
        const P = await loadPost();
        const rt = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
        const comp = new P.EffectComposer(renderer, rt);
        comp.addPass(new P.RenderPass(scene, camera));
        const ao = new P.GTAOPass(scene, camera, 1, 1);
        ao.updateGtaoMaterial({ radius: 12, distanceExponent: 1.5, thickness: 6, scale: 1.2, samples: 8 });
        ao.blendIntensity = 1;
        comp.addPass(ao);
        comp.addPass(new P.OutputPass());
        comp.setPixelRatio(renderer.getPixelRatio());
        this._comp = comp;
      } catch (e) {
        console.warn('smarthome-3d-card: tắt GTAO', e);
        this._comp = null;
      }
    }
    const controls = new OrbitControls(camera, canvas);
    Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, maxPolarAngle: 0.47 * Math.PI,
      minDistance: 250, maxDistance: 1400 });
    controls.target.set(...TARGET);
    controls.addEventListener('change', () => this._kick());
    controls.addEventListener('start', () => { this._tween = null; this._p0 = camera.position.clone(); });
    controls.addEventListener('end', () => {
      if (this._p0 && this._p0.distanceTo(camera.position) > 0.5) { this._atView = null; this._marks(); }
    });
    Object.assign(this, { _renderer: renderer, _css: css, _scene: scene, _camera: camera, _controls: controls,
      _ray: new THREE.Raycaster(), _ndc: new THREE.Vector2(), _rooms: model.rooms });

    const st = this._stage;
    // huy hiệu/nhãn là phần tử DOM nằm trên canvas: chuyển tiếp nhấn (xoay/chụm) và lăn chuột (phóng to) xuống
    // canvas cho OrbitControls (chỉ sự kiện thật; bản sao không nổi bọt -> không chạy _down hai lần)
    const fwd = (e) => e.isTrusted && e.target !== canvas && this._stage.contains(e.target) && e.target.closest('[data-slug]');
    st.addEventListener('pointerdown', (e) => {
      if (fwd(e)) {
        const init = { bubbles: false, cancelable: true, composed: false };
        for (const k of ['pointerId', 'pointerType', 'isPrimary', 'clientX', 'clientY', 'screenX', 'screenY', 'button',
          'buttons', 'ctrlKey', 'shiftKey', 'altKey', 'metaKey', 'width', 'height', 'pressure']) init[k] = e[k];
        canvas.dispatchEvent(new PointerEvent('pointerdown', init));
      }
      this._down(e);
    });
    st.addEventListener('wheel', (e) => {
      if (!fwd(e)) return;
      e.preventDefault();
      canvas.dispatchEvent(new WheelEvent('wheel', { bubbles: false, cancelable: true, deltaX: e.deltaX, deltaY: e.deltaY,
        deltaZ: e.deltaZ, deltaMode: e.deltaMode, clientX: e.clientX, clientY: e.clientY, ctrlKey: e.ctrlKey,
        shiftKey: e.shiftKey, metaKey: e.metaKey }));
    }, { passive: false });
    st.addEventListener('pointermove', (e) => this._move(e));
    st.addEventListener('pointerup', (e) => { this._ptrs.delete(e.pointerId); this._up(e); });
    st.addEventListener('pointercancel', (e) => { this._ptrs.delete(e.pointerId); this._cancelPress(); });
    st.addEventListener('pointerleave', () => { if (!this._tipTimer) this._tip.hidden = true; });
    this._ro = new ResizeObserver((es) => {
      const r = es[es.length - 1].contentRect;
      this._resize(r.width, r.height);
    });
    this._built = true;
    this._resize(this._wrap.clientWidth, this._wrap.clientHeight);
    this._snapView(this._view);
    this._apply();
    // biên dịch shader trước, rồi vẽ hẳn một khung (môi trường + bóng: khung đầu rất chậm) rồi mới báo sẵn sàng
    // (máy tính: biên dịch đúng biến thể vẽ vào render target của composer — tuyến tính, không tone map —
    // nếu không, vật đang ẩn như kính cửa sổ tường trước sẽ biên dịch giữa chừng, khựng vài giây)
    try {
      if (this._comp) renderer.setRenderTarget(this._comp.renderTarget1);
      const job = renderer.compileAsync(scene, camera);
      renderer.setRenderTarget(null);
      await job;
    } catch { renderer.setRenderTarget(null); }
    S.updateCutaway(scene, camera, 0);
    this._syncChips();
    this._draw();
    try { gl.finish(); } catch { /* bỏ qua */ }
    this._loading.hidden = true;
    if (assets.failed.length) {
      this._note.textContent = `Thiếu ${assets.failed.length} tài nguyên, dùng hình đơn giản`;
      this._note.hidden = false;
      setTimeout(() => { this._note.hidden = true; }, 6000);
    }
    if (this._connected) this._ro.observe(this._wrap);
    this._live = true;   // từ đây vòng lặp mới được chạy (trước đó một khung có thể chặn luồng chính vài giây)
    this._kick();
    this._resolveReady();
  }

  _progress(n, m) {
    this._loading.querySelector('.lt').textContent = `Đang tải mô hình… ${n}/${m}`;
    this._loading.querySelector('.pbar i').style.width = (m ? (100 * n) / m : 0) + '%';
  }

  // Huy hiệu cho mỗi thiết bị có điểm neo (api.pin): mũi chỉ đúng vào thiết bị, bám theo khi thân thiết bị gắn
  // tường trượt xuống theo tường hạ
  _makeChips({ THREE, CSS2DObject }, scene) {
    const g = new THREE.Group();
    g.name = 'chips';
    scene.updateMatrixWorld(true);
    for (const [slug, d] of Object.entries(this._devs)) {
      if (!d.api.pin) continue;
      const el = document.createElement('div');
      el.className = 'chip';
      el.dataset.slug = slug;
      const b = document.createElement('button');
      b.textContent = CHIP_IC[d.kind] || '•';
      b.setAttribute('aria-label', d.dev.title || slug);
      el.append(b, document.createElement('s'), document.createElement('i'));
      const o = new CSS2DObject(el);
      o.center.set(0.5, 1);   // mũi nhọn chạm đúng điểm neo
      o.userData.pin = d.api.pin;
      o.userData.mounts = (d.api.object.userData.mounts || []).map((m) => m.o);
      o.userData.down = false;
      // huy hiệu xám có ⚠ riêng: ẩn ⚠ rời của thiết bị (lớp camera không thấy)
      d.api.object.traverse((q) => { if (q.isCSS2DObject && q.element.textContent === '⚠') q.layers.set(31); });
      o.userData.lift = 0;
      d.api.pin.getWorldPosition(o.position);
      g.add(o);
      this._chips[slug] = o;
    }
    scene.add(g);
    // nhãn DOM (mức gas, nhiệt ẩm): vật cản cố định khi gỡ chồng huy hiệu
    this._labels = [];
    for (const d of Object.values(this._devs)) {
      if (d.api.pin) continue;
      d.api.object.traverse((o) => { if (o.isCSS2DObject && o.element.dataset.slug) this._labels.push(o); });
    }
    this._v = new THREE.Vector3();
  }

  // Gỡ chồng huy hiệu trên màn hình: xét từ dưới lên (thường là gần camera hơn), huy hiệu chạm vào huy hiệu/nhãn
  // đã đặt thì nâng lên trên cuống mảnh (mũi vẫn ở đúng thiết bị)
  _declutter() {
    const w = this._w, h = this._h, v = this._v, cam = this._camera, G = 10;   // khe ≥ 2 × vùng chạm nới (5 px)
    const B = w < NARROW ? 28 : 32, C = 6;   // cỡ nút, mũi
    const scr = (p) => { v.copy(p).project(cam); return v.z >= -1 && v.z <= 1 ? [((v.x + 1) / 2) * w, ((1 - v.y) / 2) * h] : null; };
    const placed = [];
    for (const o of this._labels) {
      const q = o.visible && scr(o.position.clone().applyMatrix4(o.parent.matrixWorld));
      const el = o.element;
      if (q) placed.push([q[0] - el.offsetWidth / 2, q[1] - el.offsetHeight, q[0] + el.offsetWidth / 2, q[1]]);
    }
    const items = [];
    for (const o of Object.values(this._chips)) {
      const q = scr(o.position);
      if (q) items.push([o, q]); else o.userData.lift = -1;
    }
    items.sort((a, b) => b[1][1] - a[1][1]);
    for (const [o, [x, y]] of items) {
      let lift = 0, box;
      const at = (l) => [x - B / 2, y - C - l - B, x + B / 2, y - C - l];
      for (let k = 0; k < 8; k++) {
        box = at(lift);
        const hit = placed.find((p) => box[0] < p[2] + G && box[2] > p[0] - G && box[1] < p[3] + G && box[3] > p[1] - G);
        if (!hit || lift >= 90) break;
        lift = Math.min(90, lift + box[3] - hit[1] + G);
      }
      placed.push(at(lift));   // hộp đúng độ nâng cuối (vòng lặp có thể dừng ngay sau khi nâng)
      lift = Math.round(lift);
      if (lift !== o.userData.lift) {
        o.userData.lift = lift;
        o.element.style.setProperty('--lift', lift + 'px');
      }
    }
  }

  // huy hiệu bám điểm neo (thân thiết bị gắn tường trượt theo tường hạ / nâng); down = thân đang trượt xuống
  _syncChips() {
    for (const o of Object.values(this._chips)) {
      const u = o.userData;
      if (!u.mounts.length) continue;
      u.pin.getWorldPosition(o.position);
      u.down = u.mounts.some((m) => m.position.y < -0.5);
    }
  }

  // màu huy hiệu theo trạng thái thiết bị
  _paintChip(slug, d) {
    const o = this._chips[slug];
    if (!o) return;
    const v = d.vis, el = o.element;
    const on = !v.unavailable && (d.kind === 'door' ? v.door > 0 : v.on);
    // màu khi bật dùng chung với viền thiết bị (cảm biến/còi: đang báo -> đỏ); rgb lấy đúng màu đèn
    let c = this._lib.S.ON_COLOR[d.kind] || 'var(--ov-act)';
    if (d.kind === 'rgb' && v.color) c = `rgb(${v.color.map((k) => Math.round(k)).join(',')})`;
    el.classList.toggle('on', on);
    el.classList.toggle('na', !!v.unavailable);
    el.style.setProperty('--c', c);
  }

  // Vẽ một khung (composer GTAO nếu có; lỗi -> vẽ thẳng từ đó về sau) + lớp nhãn CSS2D
  _draw() {
    const r = this._renderer;
    r.info.reset();
    if (this._comp) {
      try { this._comp.render(); } catch (e) {
        console.warn('smarthome-3d-card: tắt GTAO', e);
        this._comp = null;
        r.setRenderTarget(null);
      }
    }
    if (!this._comp) r.render(this._scene, this._camera);
    this._declutter();
    this._css.render(this._scene, this._camera);
  }

  _resize(w, h) {
    if (!this._built || !w || !h || (w === this._w && h === this._h)) return;   // RO gọi lần đầu cùng cỡ -> bỏ
    this._w = w;
    this._h = h;
    this._renderer.setSize(w, h);
    if (this._comp) this._comp.setSize(w, h);
    this._css.setSize(w, h);
    const cam = this._camera;
    cam.aspect = w / h;
    cam.fov = fovFor(cam.aspect);
    cam.updateProjectionMatrix();
    this._wrap.classList.toggle('narrow', w < NARROW);
    if (this._atView && !this._tween) this._snapView(this._atView);
    this._kick();
  }

  // ---------- trạng thái ----------
  _states() { return { ...(this._hass ? this._hass.states : {}), ...this._over }; }

  // Áp state -> vật thể (chỉ thiết bị đổi), giao diện, thanh trạng thái; khởi động vòng lặp nếu có đổi
  _apply() {
    const { L, S } = this._lib;
    const states = this._states();
    let changed = false;
    if (this._hass || this._cfg.demo) {
      for (const [slug, d] of Object.entries(this._devs)) {
        const vis = L.visualState(d.kind, d.ids.map((id) => states[id]));
        const key = JSON.stringify(vis);
        if (key === d.key) continue;
        d.key = key;
        d.vis = vis;
        d.api.update(vis);
        this._paintChip(slug, d);
        changed = true;
      }
    }
    const theme = L.resolveTheme(this._mode, states);
    if (theme !== this._theme) {
      this._theme = theme;
      S.applyTheme(this._scene, theme);   // sau khi đã thêm thiết bị; bóng đổ chỉ ở chế độ Ngày
      this._wrap.dataset.theme = theme;
      changed = true;
    }
    const on = (id) => !!states[id] && states[id].state === 'on';
    const house = on(L.STATUS.intrusion);
    const kitchen = L.STATUS.alarms.some((id) => id !== L.STATUS.intrusion && on(id));
    if (house !== this._alarmH || kitchen !== this._alarmK) changed = true;
    this._alarmH = house;
    this._alarmK = kitchen;
    this._bar(states);
    if (changed) this._kick();
    return changed;
  }

  _bar(states) {
    const { L } = this._lib, S = L.STATUS, root = this.shadowRoot;
    const link = states[S.link];
    const dot = root.querySelector('.dot');
    dot.className = 'dot ' + (!link || L.isUnavailable(link) || link.state === 'unknown' ? '' : link.state === 'on' ? 'ok' : 'bad');
    root.querySelector('[data-k=link]').title = 'ESP32: ' +
      (dot.classList.contains('ok') ? 'đã kết nối' : dot.classList.contains('bad') ? 'mất kết nối' : 'không rõ');
    for (const [k] of BAR) {
      const b = root.querySelector(`[data-k=${k}] b`), t = L.fmtState(states[S[k]]);
      if (b.textContent !== t) b.textContent = t;
    }
    this._alarmBtn.hidden = !L.alarmActive(states);
  }

  _setMode(m) {
    this._mode = m;
    store.set('smarthome3d.mode', m);
    this._marks();
    if (this._built) this._apply();
  }

  _marks() {
    const root = this.shadowRoot;
    root.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('active', b.dataset.mode === this._mode));
    root.querySelectorAll('[data-view]').forEach((b) => b.classList.toggle('active', b.dataset.view === this._atView));
  }

  // ---------- camera ----------
  _preset(name) {
    const { THREE } = this._lib;
    let pos, tgt = new THREE.Vector3(...TARGET), need = 300;
    if (name === 'top') { pos = new THREE.Vector3(...TOP); need = 290; }
    const r = ROOM_OF[name] && this._rooms.find((q) => q.name === ROOM_OF[name]);
    if (r) {
      // nhìn chếch từ phía trước nhà, nhắm hơi sâu vào phòng (ngang nửa tường) cho phòng nằm giữa khung
      tgt = new THREE.Vector3(r.x + r.w / 2, 20, r.y + r.d * 0.58);
      const dist = 360 + 0.8 * Math.max(r.w, r.d);   // gần hơn Toàn cảnh, đủ thấy cả phòng
      pos = tgt.clone().add(new THREE.Vector3(0, 0.87 * dist, -0.5 * dist));
      need = r.w / 2 + 50;
    }
    if (!pos) pos = new THREE.Vector3(...OVERVIEW);
    // màn hẹp: lùi camera để phòng/nhà vừa khung theo chiều ngang
    const cam = this._camera, off = pos.clone().sub(tgt), D = off.length();
    const half = D * Math.tan((cam.fov * Math.PI) / 360) * cam.aspect;
    if (half < need) off.multiplyScalar(Math.min(need / half, 1400 / D));
    return { pos: tgt.clone().add(off), tgt };
  }

  _snapView(name) {
    const p = this._preset(name);
    this._camera.position.copy(p.pos);
    this._controls.target.copy(p.tgt);
    this._controls.update();
  }

  _setView(name) {
    this._view = this._atView = name;
    store.set('smarthome3d.view', name);
    this._marks();
    if (!this._built) return;
    const p = this._preset(name);
    this._tween = { p0: this._camera.position.clone(), q0: this._controls.target.clone(), p1: p.pos, q1: p.tgt, t0: null };
    this._kick();
  }

  _stepTween(now) {
    const tw = this._tween;
    tw.t0 ??= now;
    const k = Math.min(1, (now - tw.t0) / TWEEN_MS), e = ease(k);
    this._camera.position.lerpVectors(tw.p0, tw.p1, e);
    this._controls.target.lerpVectors(tw.q0, tw.q1, e);
    if (k >= 1) this._tween = null;
    return true;
  }

  // ---------- vòng lặp: chỉ chạy khi có hoạt ảnh/thao tác; đúng một chuỗi rAF ----------
  _kick() {
    this._extra = 1;
    if (this._inFrame || this._raf || !this._connected || !this._live) return;
    this._raf = requestAnimationFrame(this._frame);
  }

  _frame = (now) => {
    this._raf = 0;
    this._inFrame = true;
    let busy = false;
    try {
      const dt = this._last ? Math.min((now - this._last) / 1000, 0.1) : 0;
      this._last = now;
      for (const d of Object.values(this._devs)) if (d.api.tick(dt)) busy = true;
      if (this._tween && this._stepTween(now)) busy = true;
      if (this._controls.update()) busy = true;
      const { S } = this._lib, t = now / 1000;
      // tường che camera tự hạ / nâng (thiết bị gắn tường trượt theo) -> huy hiệu bám theo
      if (S.updateCutaway(this._scene, this._camera, dt)) busy = true;
      this._syncChips();
      if (S.alarmGlow(this._scene, this._rooms, this._alarmH, t, 'house')) busy = true;
      if (S.alarmGlow(this._scene, this._rooms, this._alarmK, t, 'kitchen')) busy = true;
      this._draw();
    } finally {
      this._inFrame = false;
    }
    if (busy) this._extra = 1;
    else if (this._extra > 0) this._extra--;   // vẽ thêm một khung sau khung đứng yên cuối cùng
    else { this._last = 0; return; }
    if (this._connected) this._raf = requestAnimationFrame(this._frame);
    else this._last = 0;
  };

  // ---------- chạm / giữ / rê ----------
  _pick(cx, cy) {
    if (!this._built) return null;
    const r = this._renderer.domElement.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    this._ndc.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
    this._ray.setFromCamera(this._ndc, this._camera);
    // chỉ raycast vật thể thiết bị: tường/nội thất không bao giờ chặn
    for (const h of this._ray.intersectObjects(this._objs, true)) {
      if (h.object.userData.slug && shown(h.object)) return h.object.userData.slug;
    }
    return null;
  }

  // slug nhận chạm tại điểm màn hình như một cú chạm thật: phần tử DOM trên cùng (chip/nhãn) rồi raycast;
  // điểm bị nút/thanh phủ lên -> null
  _hitAt(cx, cy) {
    const el = this.shadowRoot.elementFromPoint(cx, cy);
    if (!el || !this._stage.contains(el)) return null;
    const s = el.closest('[data-slug]');
    return s ? s.dataset.slug : this._pick(cx, cy);
  }

  _slugAt(e) {
    const el = e.target && e.target.closest && e.target.closest('[data-slug]');
    return el ? el.dataset.slug : this._pick(e.clientX, e.clientY);
  }

  _down(e) {
    // theo dõi mọi ngón ngay từ đầu (trước khi xét thiết bị): >= 2 ngón (phóng to/xoay) -> không bao giờ là chạm
    if (e.isPrimary) this._ptrs.clear();   // ngón chính = không còn ngón nào khác (bỏ id cũ bị lỡ pointerup)
    this._ptrs.add(e.pointerId);
    if (this._ptrs.size >= 2) { this._cancelPress(); return; }
    if (this._press) { this._cancelPress(); return; }
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    const slug = this._slugAt(e);
    if (!slug) return;
    // phần tử DOM: giữ con trỏ (sự kiện thật đã chuyển cho OrbitControls, nó tự giữ trên canvas)
    if (e.target !== this._renderer.domElement && !e.isTrusted) {
      try { e.target.setPointerCapture(e.pointerId); } catch { /* bỏ qua */ }
    }
    const p = { id: e.pointerId, x: e.clientX, y: e.clientY, t: e.timeStamp, slug };
    p.timer = setTimeout(() => { if (this._press === p) { this._press = null; this._hold(slug); } }, HOLD_MS);
    this._press = p;
  }

  // Giữ đủ 500 ms -> more-info
  _hold(slug) {
    this._showTip(slug);
    this._fireMoreInfo(this._devs[slug].ids[0]);
  }

  _move(e) {
    const p = this._press;
    if (p && e.pointerId === p.id && Math.hypot(e.clientX - p.x, e.clientY - p.y) >= MOVE_PX) this._cancelPress();
    if (!p && e.pointerType === 'mouse' && e.buttons === 0 && !this._tipTimer) {
      const slug = this._slugAt(e);
      this._renderer.domElement.style.cursor = slug ? 'pointer' : '';
      if (slug) {
        const hr = this.getBoundingClientRect();
        this._showTip(slug, [e.clientX - hr.left, e.clientY - hr.top], 0);
      } else this._tip.hidden = true;
    }
  }

  _up(e) {
    const p = this._press;
    if (!p || e.pointerId !== p.id) return;
    this._cancelPress();
    // pointermove có thể bị gộp/mất: xét lại quãng rê từ điểm nhấn
    if (Math.hypot(e.clientX - p.x, e.clientY - p.y) >= MOVE_PX) return;
    // luồng chính bận (vd biên dịch shader) có thể xử lý pointerup trước hẹn giờ: xét theo mốc thời gian sự kiện
    if (e.timeStamp - p.t >= HOLD_MS) this._hold(p.slug);
    else this._tap(p.slug);
  }

  _cancelPress() {
    if (this._press) clearTimeout(this._press.timer);
    this._press = null;
  }

  _tap(slug) {
    const d = this._devs[slug], { L } = this._lib;
    const entity = d.ids[0], states = this._states();
    this._showTip(slug);
    if (this._cfg.demo && d.kind !== 'label') return this._demo(slug, entity, states);
    const r = L.tapCall({ entity, tap: d.dev.tap }, states[entity]);
    if (r.moreInfo) this._fireMoreInfo(r.moreInfo);
    else this._call(r.domain, r.service, r.data);
  }

  // Demo: đổi trạng thái cục bộ, không gọi HA. Còi kéo theo báo động đột nhập (để thử cảnh ửng đỏ cả nhà).
  _demo(slug, entity, states) {
    const { L } = this._lib;
    const next = L.demoNext(entity, states[entity]);
    this._over[entity] = next;
    if (slug === 'buzzer') this._over[L.STATUS.intrusion] = { state: next.state, attributes: {} };
    this._apply();
  }

  _silence() {
    const { L } = this._lib;
    if (this._cfg.demo) {
      for (const id of [...L.STATUS.alarms, this._devs.buzzer && this._devs.buzzer.ids[0]]) delete this._over[id];
      this._apply();
    } else this._call('button', 'press', { entity_id: L.STATUS.alarmButton });
  }

  // Lỗi dịch vụ: HA tự hiện thông báo -> nuốt promise reject (không thành lỗi trang)
  _call(domain, service, data) {
    if (!this._hass) return;
    try {
      const p = this._hass.callService(domain, service, data);
      if (p && typeof p.catch === 'function') p.catch(() => {});
    } catch (e) {
      console.warn('smarthome-3d-card:', e);
    }
  }

  _fireMoreInfo(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId }, bubbles: true, composed: true }));
  }

  // Tên thiết bị: theo chuột (ms = 0) hoặc tại thiết bị trong 2 s sau khi chạm
  _showTip(slug, at, ms = 2000) {
    const d = this._devs[slug];
    if (!d) return;
    const [x, y] = at || this.debug(slug).screen;
    this._tip.textContent = (d.dev.title || slug) + (d.vis && d.vis.unavailable ? ' ⚠ không khả dụng' : '');
    this._tip.style.left = x + 'px';
    this._tip.style.top = y + 'px';
    this._tip.hidden = false;
    clearTimeout(this._tipTimer);
    this._tipTimer = 0;
    if (ms) this._tipTimer = setTimeout(() => { this._tip.hidden = true; this._tipTimer = 0; }, ms);
  }
}

if (!customElements.get('smarthome-3d-card')) customElements.define('smarthome-3d-card', Smarthome3DCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === 'smarthome-3d-card')) {
  window.customCards.push({ type: 'smarthome-3d-card', name: 'Smarthome 3D', description: 'Mô hình 3D nhà thông minh' });
}
