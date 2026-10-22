"""Kiểm tra model3d.json do tools/build_dashboard.py xuất ra (không cần trình duyệt)."""
import json
import subprocess

import pytest

MODEL = "/config/www/smarthome/3d/model3d.json"
DASH = "/config/smarthome/dashboard.yaml"


@pytest.fixture(scope="module")
def model():
    subprocess.run(["python3", "/config/smarthome/tools/build_dashboard.py"], check=True, capture_output=True)
    return json.load(open(MODEL, encoding="utf-8"))


def test_house_dims(model):
    assert model["house"] == {"w": 500, "d": 355, "wall_h": 135, "door_h": 105, "wall_t": 6}
    assert len(model["rooms"]) == 3
    assert len(model["doors"]) == 3
    assert [d.get("main") for d in model["doors"]] == [True, None, None]
    assert model["doors"][0]["y"] == 0
    assert model["window"] == {"x1": 201, "x2": 321, "y": 0, "sill": 45, "top": 105}
    assert sorted(f["kind"] for f in model["furniture"]) == ["bed", "sofa", "stove", "tv"]


def test_devices_complete(model):
    dev = model["devices"]
    assert set(dev) == {"door", "buzzer", "pir", "living", "rgb", "porch", "rfid", "ldr", "gas", "gaslvl",
                        "flame", "fan", "dht", "bedroom"}
    assert dev["door"]["entity"] == "cover.smarthome_cua"
    assert dev["buzzer"]["tap"] == "more-info"
    assert dev["living"]["tap"] == "toggle"


def test_positions_applied(model):
    rgb = model["devices"]["rgb"]
    assert rgb["x"] == pytest.approx(-20 + 55.6 / 100 * 540, abs=0.2)
    assert rgb["y"] == pytest.approx(-55 + 47.7 / 100 * 430, abs=0.2)


def test_titles_no_pins(model):
    for d in model["devices"].values():
        assert "IO" not in d["title"] and "relay" not in d["title"]
    assert model["devices"]["door"]["title"] == "Cửa"
    assert model["devices"]["gaslvl"]["title"] == "Mức khí gas (AO)"


def test_view_inserted(model):
    # venv của pytest không có PyYAML → nạp bằng python3 hệ thống rồi đổi sang JSON
    out = subprocess.run(["python3", "-c", "import sys,json,yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))", DASH],
                         check=True, capture_output=True, text=True).stdout
    views = json.loads(out)["views"]
    assert views[2]["path"] == "mo-hinh-3d"
    assert {v["path"] for v in views} >= {"tong-quan", "dieu-khien", "truy-cap", "quan-ly"}
