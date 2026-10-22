# Trang "Mô hình 3D" cho dashboard smarthome-doan — đặc tả

Ngày: 19/10/2026 · Trạng thái: chờ duyệt

## Mục tiêu
Thêm một trang mới vào dashboard `smarthome-doan`: mô hình 3D sống động của ngôi nhà, thao tác được
giống mặt bằng 2D (trang Tổng quan). Mọi thiết bị có trên mặt bằng 2D đều có trên 3D, chạm được và
cập nhật theo thời gian thực.

**Không làm:** ESP32, relay, dây, mạch điện hay linh kiện ẩn khác. Chỉ vẽ ngôi nhà và các thiết bị
nhìn thấy được (đèn, quạt, cửa, còi, cảm biến, đầu đọc thẻ).

## Kiến trúc
- `/config/www/smarthome/smarthome-3d-card.js`: thẻ Lovelace tự viết (custom element
  `smarthome-3d-card`). Thẻ nhận `hass`, dựng cảnh three.js, ánh xạ entity sang vật thể 3D, gọi
  service và mở bảng more-info chuẩn của HA (sự kiện `hass-more-info`).
- `/config/www/smarthome/vendor/three.module.min.js` và `OrbitControls.js`: three.js r170, chép về
  máy để chạy không cần internet.
- Đăng ký resource qua websocket `lovelace/resources/create|update` (dạng module), kèm `?v=<mã băm>`
  để trình duyệt không giữ bản cũ. Không sửa `configuration.yaml`, không khởi động lại HA. Một lệnh
  `tools/push_3d.py` cập nhật resource và thêm/thay trang `mo-hinh-3d`.
- Tọa độ: `build_dashboard.py` ghi thêm `/config/www/smarthome/model3d.json` (kích thước nhà, vách,
  cửa, nội thất, vị trí thiết bị tính bằng mm, đã áp `positions.json`). Thẻ 3D đọc file này, nên kéo
  lại icon ở mặt bằng 2D thì 3D cũng đổi theo.
- Trang mới: `smarthome/dashboard_3d.yaml` (`title: Mô hình 3D`, `path: mo-hinh-3d`, kiểu panel
  hoặc sections), được `build_dashboard.py` chèn vào `dashboard.yaml`. Đẩy lên HA bằng
  `push_dashboard.py --add-views`. Không dùng `--full`; 4 trang cũ giữ nguyên.
- Cấu hình thẻ: tùy chọn `demo: true` cho phép chạm để đổi trạng thái ngay trong trình duyệt, không
  gọi HA. Dùng để kiểm tra hình và hoạt ảnh khi ESP32 offline; ESP32 ảo (`_mo_phong`) không dùng được
  vì nó vẫn theo tên entity đời cũ, không có cửa, đèn RGB hay đèn phòng khách.

## Mô hình
- Tỉ lệ 1 đơn vị = 1 mm như mặt bằng. Nhà 500 × 355; vách giữa y = 188; vách bếp | ngủ x = 220.
- Tường cao khoảng 90 mm, không mái (nhà búp bê cắt nóc). Có ô cửa chính 45–105, cửa sổ 201–321,
  cửa bếp và cửa phòng ngủ. Nội thất khối đơn giản: TV, sofa, giường đôi, bếp nấu.
- Hai chế độ hiển thị, nút chọn **Ngày / Đêm / Tự động**:
  - Ngày: sàn gỗ, tường kem, nắng có bóng đổ.
  - Đêm (digital twin): nền tối, tường bán trong suốt viền neon, thiết bị phát sáng.
  - Tự động: theo `binary_sensor.smarthome_troi_toi`.
- Lựa chọn chế độ và góc nhìn lưu trong `localStorage` (chỉ để tiện cho từng máy).

## Thiết bị

| Entity | Hiển thị | Chạm | Giữ |
|---|---|---|---|
| `cover.smarthome_cua` | cánh cửa xoay mượt; khi `opening`/`closing` thì xoay dần | mở/đóng (toggle) | more-info |
| `switch.smarthome_den_phong_khach`, `_den_phong_ngu`, `_den_hien` | bóng đèn sáng + PointLight chiếu lên phòng | bật/tắt | more-info |
| `light.smarthome_den_rgb` | dải đèn đúng màu `rgb_color` và độ sáng `brightness` | bật/tắt | more-info (chọn màu) |
| `switch.smarthome_quat_hut_phong_ngu` | cánh quạt quay | bật/tắt | more-info |
| `switch.smarthome_coi` | còi rung + vòng sóng âm khi on | more-info | more-info |
| `binary_sensor.smarthome_bao_khi_gas_bep` | đèn hiệu đỏ nhấp nháy, bếp ửng đỏ | more-info | more-info |
| `binary_sensor.smarthome_bao_chay_bep` | ngọn lửa động trên bếp + bếp ửng đỏ | more-info | more-info |
| `binary_sensor.smarthome_bao_dong_dot_nhap` | cả nhà ửng đỏ nhấp nháy | — | — |
| `binary_sensor.smarthome_chuyen_dong_truoc_nha` | nón vùng quét, sáng lên khi on | more-info | more-info |
| `sensor.smarthome_the_vua_quet` | đầu đọc ngoài tường trước chớp xanh khi giá trị đổi | more-info | more-info |
| `binary_sensor.smarthome_troi_toi` | biểu tượng mặt trăng/mặt trời ngoài nhà | more-info | more-info |
| `sensor.smarthome_nhiet_do_phong_ngu`, `_do_am_phong_ngu`, `_muc_khi_gas` | nhãn chữ nổi trong phòng | more-info | more-info |

- Còi chỉ mở more-info khi chạm (giữ đúng quy ước bản 2D để tránh bấm nhầm).
- Entity `unavailable` hoặc chưa có: vật thể màu xám kèm dấu ⚠.
- Có tên thiết bị khi rê chuột (máy tính) hoặc ngay sau khi chạm (điện thoại).
- Thanh trạng thái gọn trên thẻ: kết nối ESP32 (`binary_sensor.smarthome_ket_noi`), nhiệt độ, độ ẩm,
  gas, công suất. Có nút "Tắt báo động" (`button.smarthome_tat_bao_dong`), chỉ hiện khi đang báo động.

## Camera
OrbitControls: kéo để xoay, cuộn hoặc hai ngón để phóng to, giới hạn không nhìn xuống dưới sàn. Có các
nút góc nhìn nhanh (Toàn cảnh, Phòng khách, Bếp, Phòng ngủ, Từ trên), camera chuyển mượt giữa các góc.

## Hiệu năng
- Chỉ dựng cảnh lại khi có hoạt ảnh (quạt, cửa đang chạy, báo động) hoặc khi người dùng thao tác.
  Khi đứng yên thì không chạy vòng lặp.
- Dừng hẳn khi thẻ bị ẩn (IntersectionObserver hoặc `disconnectedCallback`).
- Bóng đổ chỉ bật ở chế độ Ngày; pixel ratio tối đa 2.

## Kiểm tra
1. Mở trang khi ESP32 offline: cảnh tải xong, console không lỗi, mọi thiết bị xám kèm ⚠.
2. Thẻ tạm với `demo: true`: chạm từng thiết bị → hình và hoạt ảnh đổi đúng (đèn, màu RGB, quạt,
   cửa, gas, lửa, đột nhập, PIR, quẹt thẻ).
3. Kiểm tra giao diện điện thoại (app HA) và máy tính; thử cả ba chế độ hiển thị.
4. Khi cắm ESP32 thật: chạm từng thiết bị → trạng thái trong HA đổi → mô hình đổi theo. Đổi trạng
   thái từ trang Điều khiển → 3D cập nhật. Nút "Tắt báo động" chạy.

---

## Bản 2 — "Nhà thật" (20/10/2026, thay phần Mô hình và hai chế độ hiển thị ở trên)

Người dùng xem bản 1 thấy "xấu, không chân thật, chế độ đêm rất khó nhìn" và chọn: **như nhà thật / ảnh thực** + **đêm thật, tường đặc**.

### Thay đổi
- **Tỉ lệ thật 1:20.** Mặt bằng giữ nguyên số đo (mm mô hình). Tường cao 135 (2,7 m thật), cửa đi cao 105 (2,1 m), cửa sổ bậu 45 / đỉnh 105.
- **Tường tự hạ (cutaway kiểu The Sims):** tường nằm giữa camera và tâm nhà hạ xuống 25 mm; các tường khác cao đủ. Cập nhật mỗi khi camera đổi, chuyển mượt.
- **Vật liệu PBR thật** (vân Poly Haven CC0, 1k): sàn gỗ (khách, ngủ), gạch bếp, tường sơn trong nhà, tường vữa ngoài, lối đi lát đá, cỏ. Ánh sáng môi trường `RoomEnvironment` (PMREM), tone mapping ACES/AgX, bóng mềm. Máy tính: thêm ambient occlusion (GTAO); điện thoại: tắt GTAO, bóng 1024, pixel ratio ≤ 1,5.
- **Nội thất:** model glTF thật từ Poly Haven (CC0) cho sofa, bàn trà, ghế bành, kệ/tủ, tủ đầu giường, cây cảnh. Tự dựng bằng vật liệu PBR: giường đôi (chăn, gối), tủ bếp mặt đá + bếp nấu, TV màn phẳng. Tài nguyên chép về `www/smarthome/3d/assets/` (≈ 10 MB, kèm `manifest.json` + ghi chú giấy phép CC0), có thanh tải lần đầu.
- **Thiết bị như đồ thật:** đèn ốp trần (bật → phòng sáng ấm, có bóng), đèn hắt RGB đổi màu, quạt hút có lưới + cánh quay, cửa gỗ có tay nắm, cảm biến là khối trắng nhỏ đúng cỡ, còi/báo động có đèn xoay đỏ.
- **Đêm thật:** tường đặc; trời xanh thẫm + ánh trăng nhẹ đủ nhìn rõ nhà; đèn bật → phòng sáng ấm, cửa sổ hắt sáng, đèn hiên rọi lối đi. **Bỏ** kiểu tường trong suốt viền neon.
- **Giữ nguyên:** thao tác chạm/giữ, góc nhìn nhanh, thanh trạng thái, nút tắt báo động, demo, `push_3d.py`; API thẻ ↔ scene giữ tên cũ, chỉ thêm `loadAssets`, `updateCutaway`.

### Kiểm tra bản 2
1. Toàn bộ test cũ vẫn đạt (sửa test nào phụ thuộc hình học cũ).
2. Ảnh chụp Ngày / Đêm / điện thoại so với bản 1; đêm phải đọc rõ phòng, đồ vật.
3. Số draw call ở chế độ điện thoại trong ngân sách; không lỗi console khi nạp tài nguyên.
4. Thử lại với ESP32 thật (dữ liệu thật + bật/tắt đèn).
