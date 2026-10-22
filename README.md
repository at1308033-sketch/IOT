# IOT — Smarthome

Đồ án nhà thông minh: ESP32 (ESPHome) ↔ MQTT ↔ Home Assistant + Node-RED + MariaDB, kèm dashboard điều khiển và thẻ mô hình 3D.

Mã nguồn nằm ở nhánh phụ; nhánh `main` chỉ giữ mô tả repo.

## Bảo mật
Repo **không** chứa `secrets.yaml`, cơ sở dữ liệu, log, chứng chỉ hay bản sao lưu.
Sao chép `secrets.example.yaml` và `esphome/secrets.example.yaml` thành `secrets.yaml` rồi điền giá trị thật trên máy của bạn.
