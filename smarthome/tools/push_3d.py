"""Đưa trang "Mô hình 3D" (path mo-hinh-3d) lên dashboard smarthome-doan và đăng ký resource thẻ 3D.
Không đụng các trang khác (không ghi đè cả dashboard). Chạy lại nhiều lần vẫn cho cùng kết quả.
Nguồn: /config/smarthome/dashboard_3d.yaml. Nhớ chạy build_dashboard.py trước (để model3d.json mới).

  python3 push_3d.py
"""
import glob
import hashlib
import os

import yaml

from push_dashboard import HA, URL_PATH

WWW = "/config/www/smarthome/"
SOURCE = "/config/smarthome/dashboard_3d.yaml"
BASE = "/local/smarthome/smarthome-3d-card.js"

# v = 8 ký tự md5 của thẻ + mọi module 3d/*.js + model + toàn bộ tài nguyên (kể cả manifest),
# vì các file này đều được nạp kèm ?v của thẻ → đổi bất kỳ file nào là trình duyệt tải lại
files = ["smarthome-3d-card.js", "3d/model3d.json"]
files += sorted(os.path.relpath(p, WWW) for p in glob.glob(WWW + "3d/*.js"))
files += sorted(os.path.relpath(p, WWW) for p in glob.glob(WWW + "3d/assets/**/*", recursive=True)
                if os.path.isfile(p))
md5 = hashlib.md5()
for f in files:
    md5.update(f.encode())
    md5.update(open(WWW + f, "rb").read())
v = md5.hexdigest()[:8]
url = f"{BASE}?v={v}"

ha = HA()

# Resource: khớp đúng đường dẫn (bỏ phần ?v=). Cập nhật cái đầu, xoá các bản trùng, nếu chưa có thì tạo mới
res = ha.call(type="lovelace/resources")
mine = [r for r in res if r["url"].split("?")[0] == BASE]
if mine:
    ha.call(type="lovelace/resources/update", resource_id=mine[0]["id"], res_type="module", url=url)
    for extra in mine[1:]:
        ha.call(type="lovelace/resources/delete", resource_id=extra["id"])
else:
    ha.call(type="lovelace/resources/create", res_type="module", url=url)

# Trang: thay tại chỗ nếu có, ngược lại chèn sau trang Điều khiển (index 2)
view = yaml.safe_load(open(SOURCE, encoding="utf-8"))
cur = ha.call(type="lovelace/config", url_path=URL_PATH)
views = cur.setdefault("views", [])
idx = next((i for i, x in enumerate(views) if x.get("path") == view["path"]), None)
if idx is None:
    views.insert(2, view)
else:
    views[idx] = view
ha.call(type="lovelace/config/save", url_path=URL_PATH, config=cur)
print(f"Resource v={v} · trang: {[x.get('path') for x in views]}")
