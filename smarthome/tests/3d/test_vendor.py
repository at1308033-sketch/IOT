from conftest import HARNESS

V = "/www/smarthome/3d/vendor"


def test_three_loads(page):
    page.goto(HARNESS)
    r = page.evaluate(f"""async () => {{
      const T = await import('{V}/three.module.min.js');
      const {{ OrbitControls }} = await import('{V}/OrbitControls.js');
      const {{ CSS2DRenderer }} = await import('{V}/CSS2DRenderer.js');
      const renderer = new T.WebGLRenderer();
      const ok = !!renderer.getContext();
      renderer.dispose();
      return {{ rev: T.REVISION, orbit: typeof OrbitControls, css2d: typeof CSS2DRenderer, gl: ok }};
    }}""")
    assert r == {"rev": "170", "orbit": "function", "css2d": "function", "gl": True}
    assert page.errors == []


def test_addons_load(page):
    # Các addon vendor nạp được trong trình duyệt
    page.goto(HARNESS)
    r = page.evaluate(f"""async () => {{
      const m = async (n) => await import('{V}/' + n + '.js');
      return {{
        gltf: typeof (await m('GLTFLoader')).GLTFLoader,
        env: typeof (await m('RoomEnvironment')).RoomEnvironment,
        comp: typeof (await m('EffectComposer')).EffectComposer,
        gtao: typeof (await m('GTAOPass')).GTAOPass,
        out: typeof (await m('OutputPass')).OutputPass,
      }};
    }}""")
    assert r == {k: "function" for k in ("gltf", "env", "comp", "gtao", "out")}
    assert page.errors == []


def test_vendor_imports_flat():
    # Không còn import trần 'three' hoặc đường dẫn ../
    import pathlib, re
    for f in pathlib.Path("/config/www/smarthome/3d/vendor").glob("*.js"):
        if f.name == "three.module.min.js":
            continue
        t = f.read_text()
        assert not re.search(r"from\s+['\"]three['\"]", t), f.name
        assert not re.search(r"from\s+['\"]\.\./", t), f.name
