import json
import pathlib

from conftest import HARNESS

A = pathlib.Path("/config/www/smarthome/3d/assets")
TEX = ["floor_wood", "floor_tile_kitchen", "wall_plaster", "wall_exterior",
       "paving", "grass", "countertop", "fabric_bed"]
MODELS = ["sofa", "coffee_table", "armchair", "nightstand", "shelf", "plant"]


def _manifest():
    return json.loads((A / "manifest.json").read_text())


def test_manifest_complete():
    m = _manifest()
    assert m["license"] == "CC0" and m["source"] == "Poly Haven"
    for k in TEX:
        t = m["textures"][k]
        assert t["repeat_mm"] > 0
        assert "diff" in t and "nor" in t and ("rough" in t or "arm" in t)
        for f in ("diff", "nor", "rough", "arm"):
            if f in t:
                assert (A / t[f]).is_file(), t[f]
    for k in MODELS:
        g = m["models"][k]
        assert (A / g["gltf"]).is_file()
        assert len(g["size_mm"]) == 3 and all(x > 0 for x in g["size_mm"])
    total = sum(p.stat().st_size for p in A.rglob("*") if p.is_file())
    assert total <= 15 * 1024 * 1024, total
    assert (A / "LICENSE.md").is_file()


def test_gltf_loads(page):
    m = _manifest()
    page.goto(HARNESS)
    res = page.evaluate("""async (models) => {
      const { GLTFLoader } = await import('/www/smarthome/3d/vendor/GLTFLoader.js');
      const out = {};
      for (const [k, v] of Object.entries(models)) {
        const g = await new GLTFLoader().loadAsync('/www/smarthome/3d/assets/' + v.gltf);
        let n = 0; g.scene.traverse(o => { if (o.isMesh) n++; });
        out[k] = n;
      }
      return out;
    }""", m["models"])
    assert set(res) == set(MODELS)
    assert all(n >= 1 for n in res.values()), res
    assert page.errors == []


# ---------------- assets.js: loadAssets ----------------
LOAD_JS = """async () => {
  const { loadAssets } = await import('/www/smarthome/3d/assets.js?v=t');
  const THREE = await import('/www/smarthome/3d/vendor/three.module.min.js');
  const prog = [];
  const r = await loadAssets((d, t) => prog.push([d, t]));
  const again = loadAssets(() => {}) === loadAssets(() => {});
  const models = {};
  for (const [k, g] of Object.entries(r.models)) {
    if (!g) { models[k] = null; continue; }
    let n = 0; g.traverse(o => { if (o.isMesh) n++; });
    const bb = new THREE.Box3().setFromObject(g);
    const s = bb.getSize(new THREE.Vector3());
    models[k] = { group: g.isGroup, name: g.name, meshes: n, size: [s.x, s.z, s.y], minY: bb.min.y,
                  cx: (bb.min.x + bb.max.x) / 2, cz: (bb.min.z + bb.max.z) / 2 };
  }
  const tex = {};
  for (const [k, t] of Object.entries(r.textures)) {
    tex[k] = { map: !!t.map, normalMap: !!t.normalMap, rough: !!t.roughnessMap, rep: t.repeat_mm,
               srgb: t.map && t.map.colorSpace === 'srgb', wrap: t.map && t.map.wrapS === 1000 };
  }
  return { failed: r.failed, prog, tex, models, cached: again };
}"""


def test_load_assets_all(page):
    m = _manifest()
    page.goto(HARNESS)
    r = page.evaluate(LOAD_JS)
    assert r["failed"] == []
    assert set(r["tex"]) == set(TEX) and set(r["models"]) == set(MODELS)
    for k, t in r["tex"].items():
        assert t["map"] and t["normalMap"] and t["rough"] and t["srgb"] and t["wrap"], k
        assert t["rep"] == m["textures"][k]["repeat_mm"]
    total = sum(len([f for f in ("diff", "nor", "rough", "arm") if f in t])
                               for t in m["textures"].values()) + len(MODELS)
    assert r["prog"][-1] == [total, total] and len(r["prog"]) == total
    assert r["cached"] is True
    for k, g in r["models"].items():
        assert g["group"] and g["name"] == k and g["meshes"] >= 1, k
        want = m["models"][k]["size_mm"]
        # trục khớp: kích thước lớn nhất theo size_mm phải sai lệch < 5 %
        i = max(range(3), key=lambda j: want[j])
        assert abs(g["size"][i] - want[i]) / want[i] < 0.05, (k, g["size"], want)
        assert abs(g["minY"]) < 1e-3 and abs(g["cx"]) < 1e-3 and abs(g["cz"]) < 1e-3, k
    assert page.errors == []


def test_asset_404_fallback(page):
    m = _manifest()
    bad_tex = m["textures"]["floor_wood"]["diff"]
    bad_model = m["models"]["plant"]["gltf"]
    for rel in (bad_tex, bad_model):
        page.route("**/3d/assets/" + rel + "*", lambda route: route.fulfill(status=404, body="no"))
    page.goto(HARNESS)
    r = page.evaluate(LOAD_JS)
    assert sorted(r["failed"]) == ["floor_wood", "plant"]
    assert r["models"]["plant"] is None and r["tex"]["floor_wood"]["map"] is False
    assert r["tex"]["floor_wood"]["normalMap"] is True
    assert r["models"]["sofa"]["meshes"] >= 1
    # 404 chỉ sinh lỗi console "Failed to load resource", không được có pageerror/lỗi khác
    assert [e for e in page.errors if "Failed to load resource" not in e] == []
