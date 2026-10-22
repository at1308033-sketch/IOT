"""Thêm (hoặc thay) đúng trang "Điều khiển" (path dieu-khien) vào dashboard smarthome-doan.
Không đụng các trang khác. Nguồn: /config/smarthome/dashboard_dieu_khien.yaml

  python3 add_view_dieu_khien.py
"""
import yaml

from push_dashboard import HA, URL_PATH

SOURCE = "/config/smarthome/dashboard_dieu_khien.yaml"

view = yaml.safe_load(open(SOURCE, encoding="utf-8"))
ha = HA()
cur = ha.call(type="lovelace/config", url_path=URL_PATH)
views = cur.setdefault("views", [])
idx = next((i for i, v in enumerate(views) if v.get("path") == view["path"]), None)
if idx is None:
    views.insert(1, view)  # ngay sau trang Tổng quan
else:
    views[idx] = view
ha.call(type="lovelace/config/save", url_path=URL_PATH, config=cur)
print("Đã", "thêm" if idx is None else "thay", "trang", view["title"], "→", [v.get("title") for v in views])
