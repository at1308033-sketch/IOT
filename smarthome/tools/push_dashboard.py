"""Đẩy dashboard "Smarthome đồ án" (chế độ storage) vào Home Assistant qua websocket.

  python3 push_dashboard.py           # chỉ cập nhật thẻ mặt bằng (giữ nguyên bố cục bạn đã kéo thả)
  python3 push_dashboard.py --pull    # đọc vị trí biểu tượng bạn tự đặt trong HA → positions.json
  python3 push_dashboard.py --add-views  # thêm các trang mới (theo path) chưa có, không đụng trang cũ
  python3 push_dashboard.py --replace-view <path>  # thay đúng một trang (vd mo-phong) bằng bản sinh mới
  python3 push_dashboard.py --insert  # thẻ mặt bằng đã bị xóa → chèn lại dưới tiêu đề "Mô hình nhà thông minh"
  python3 push_dashboard.py --full    # tạo dashboard nếu chưa có + ghi đè TOÀN BỘ bằng dashboard.yaml

Chạy build_dashboard.py trước để sinh lại dashboard.yaml / floorplan.svg / wires/*.svg.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".pylib"))
import websocket  # noqa: E402
import yaml  # noqa: E402

URL_PATH = "smarthome-doan"
SOURCE = "/config/smarthome/dashboard.yaml"
FLOORPLAN = "/local/smarthome/floorplan.svg"


class HA:
    def __init__(self):
        self.ws = websocket.create_connection("ws://supervisor/core/websocket", timeout=30)
        assert json.loads(self.ws.recv())["type"] == "auth_required"
        self.ws.send(json.dumps({"type": "auth", "access_token": os.environ["SUPERVISOR_TOKEN"]}))
        msg = json.loads(self.ws.recv())
        if msg["type"] != "auth_ok":
            sys.exit(f"Đăng nhập websocket thất bại: {msg}")
        self.n = 0

    def call(self, **payload):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, **payload}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if not msg.get("success"):
                    raise RuntimeError(f"{payload['type']}: {msg.get('error')}")
                return msg.get("result")


def floorplan_cards(node):
    """Mọi thẻ picture-elements dùng ảnh mặt bằng, ở bất kỳ độ sâu nào."""
    if isinstance(node, dict):
        if node.get("type") == "picture-elements" and FLOORPLAN in str(node.get("image", "")):
            yield node
        for v in node.values():
            yield from floorplan_cards(v)
    elif isinstance(node, list):
        for v in node:
            yield from floorplan_cards(v)


def main():
    new = yaml.safe_load(open(SOURCE, encoding="utf-8"))
    ha = HA()
    if "--full" in sys.argv:
        boards = ha.call(type="lovelace/dashboards/list")
        if not any(b["url_path"] == URL_PATH for b in boards):
            ha.call(type="lovelace/dashboards/create", url_path=URL_PATH, title=new.get("title", "Smarthome"),
                    icon="mdi:home-automation", show_in_sidebar=True, require_admin=False, mode="storage")
            print("Đã tạo dashboard", URL_PATH)
        ha.call(type="lovelace/config/save", url_path=URL_PATH, config=new)
        print("Đã ghi toàn bộ dashboard từ", SOURCE)
        return

    cur = ha.call(type="lovelace/config", url_path=URL_PATH)
    if "--pull" in sys.argv:
        pos = {}
        # % trên dashboard tính theo khung ảnh đang dùng → lưu kèm viewBox để đổi khung vẫn quy đúng ra mm
        svg_head = open("/config/www/smarthome/floorplan.svg", encoding="utf-8").read(400)
        vb = svg_head.split('viewBox="', 1)[1].split('"', 1)[0]
        pos["_viewbox"] = [float(v) for v in vb.split()]
        for card in floorplan_cards(cur):
            for el in card.get("elements", []):
                st = el.get("style", {})
                if el.get("entity") and "left" in st and "top" in st:
                    pos[el["entity"]] = [float(str(st["left"]).rstrip("%")), float(str(st["top"]).rstrip("%"))]
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")
        json.dump(pos, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"Đã lưu vị trí {len(pos)} phần tử vào {out}")
        return
    if "--add-views" in sys.argv:
        have = {v.get("path") for v in cur.get("views", [])}
        added = [v for v in new.get("views", []) if v.get("path") not in have]
        cur.setdefault("views", []).extend(added)
        if added:
            ha.call(type="lovelace/config/save", url_path=URL_PATH, config=cur)
        print("Đã thêm trang:", [v.get("title") for v in added] or "không có trang mới")
        return
    if "--replace-view" in sys.argv:
        path = sys.argv[sys.argv.index("--replace-view") + 1]
        src_v = next((v for v in new.get("views", []) if v.get("path") == path), None)
        idx = next((i for i, v in enumerate(cur.get("views", [])) if v.get("path") == path), None)
        if src_v is None or idx is None:
            sys.exit(f"Không tìm thấy trang '{path}'")
        cur["views"][idx] = src_v
        ha.call(type="lovelace/config/save", url_path=URL_PATH, config=cur)
        print(f"Đã thay trang \"{src_v.get('title')}\".")
        return
    src = next(floorplan_cards(new))
    targets = list(floorplan_cards(cur))
    if not targets and "--insert" in sys.argv:
        for view in cur.get("views", []):
            for section in view.get("sections", []):
                cards = section.get("cards", [])
                for i, card in enumerate(cards):
                    if card.get("type") == "heading" and card.get("heading") == "Mô hình nhà thông minh":
                        cards.insert(i + 1, src)
                        ha.call(type="lovelace/config/save", url_path=URL_PATH, config=cur)
                        print(f"Đã chèn lại thẻ mặt bằng vào trang \"{view.get('title')}\".")
                        return
        sys.exit("Không tìm thấy tiêu đề \"Mô hình nhà thông minh\" để chèn thẻ mặt bằng.")
    if not targets:
        sys.exit("Không tìm thấy thẻ mặt bằng trong dashboard hiện tại — dùng --insert để chèn lại "
                 "hoặc --full để ghi đè toàn bộ.")
    for card in targets:
        for key in ("image", "elements", "card_mod"):
            card[key] = src[key]
    ha.call(type="lovelace/config/save", url_path=URL_PATH, config=cur)
    print(f"Đã cập nhật {len(targets)} thẻ mặt bằng, giữ nguyên phần còn lại.")


if __name__ == "__main__":
    main()
