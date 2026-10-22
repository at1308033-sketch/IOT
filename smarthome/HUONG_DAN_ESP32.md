# Smarthome đồ án — Hướng dẫn nạp, hiệu chỉnh và kiểm tra ESP32

File liên quan:
- Firmware: `/config/esphome/smarthome.yaml` (bản cũ: `smarthome.yaml.bak-20261016`)
- Automation HA: `/config/smarthome/ha_package.yaml` (bản cũ: `ha_package.yaml.bak-20261016`)
- Dashboard: trang **Điều khiển** trong dashboard `smarthome-doan`, nguồn `/config/smarthome/dashboard_dieu_khien.yaml`

## 1. Giả định đã dùng

| Mục | Giá trị | Nguồn |
|---|---|---|
| ACS712 | bản 20A, 100 mV/A | bạn xác nhận |
| DHT | DHT11 (module xanh, có sẵn trở kéo lên) | bạn xác nhận |
| Còi | kêu ở mức THẤP → `buzzer_inverted: "true"` | bạn xác nhận |
| Servo | loại QUAY LIÊN TỤC 360°: mở = quay ngược chiều kim đồng hồ trong "Thời gian quay mở" (mặc định 400 ms ≈ 80°, chỉnh trên HA); đóng = quay cùng chiều tới khi công tắc từ báo đóng (17/10) | quan sát thực tế |
| Tải | đèn, quạt chạy 5V chung bus, công suất = dòng × 5 V | bạn xác nhận |
| Kết nối HA | MQTT, tiền tố `smarthome-doan` (như bản cũ) | mặc định |
| Thẻ RFID | quản lý trên trang Quản lý (MariaDB → MQTT), 2 UID trong YAML chỉ là dự phòng | mặc định |
| Thông báo | `notify.mobile_app_izth` | mặc định |
| Đèn hiên | tắt sau 2 phút không chuyển động; trời tối khi ánh sáng < 30 % | mặc định, chỉnh trên HA |
| Quạt hút | bật khi độ ẩm ≥ 75 %, tắt khi ≤ 70 % | mặc định, chỉnh trên HA |
| Cửa | tự đóng sau 5 s | mặc định, chỉnh trên HA |
| Vắng nhà | còi + nháy đỏ + thông báo, có 30 s để ra khỏi nhà | mặc định |

## 2. Cái nào chạy ở đâu

| Chức năng | Chạy trên | Lý do |
|---|---|---|
| Cửa RFID, servo, tự đóng, phát hiện vướng | ESP32 | Phải mở cửa được cả khi mất mạng; cần phản hồi nhanh |
| Báo cháy/gas: còi, nháy đỏ, bật quạt hút | ESP32 | Yêu cầu an toàn: không phụ thuộc Wi-Fi/HA |
| Đèn hiên tự động | ESP32 | Logic đơn giản, cảm biến cùng mạch; ngưỡng vẫn chỉnh trên HA |
| Quạt theo độ ẩm | ESP32 | Như trên; chỉ tác động khi độ ẩm vượt ngưỡng nên vẫn bật/tắt tay được |
| Vắng nhà: phát hiện + còi | ESP32 | Kẻ gian cắt Wi-Fi vẫn bị báo |
| Thông báo điện thoại (cháy, gas, đột nhập, sai thẻ, cửa vướng, mất kết nối) | HA | Chỉ HA có app điện thoại |
| Lịch sử, biểu đồ, điện năng (kWh) | HA | Cần cơ sở dữ liệu |
| Quản lý thẻ | HA + Node-RED + MariaDB | Có giao diện thêm/khóa thẻ |

Quy tắc ưu tiên trên ESP32: **gas > tự động độ ẩm > bật tay**. Mở cửa hợp lệ (thẻ, nút HA, điện thoại) **tự tắt chế độ vắng nhà**. Bấm **Tắt báo động** thì còi im; đèn vẫn nháy đỏ tới khi hết lửa/gas. Riêng báo đột nhập thì bấm là xóa hẳn.

## 3. Nạp lần đầu qua USB

1. Tắt ESP32 ảo trước: trên trang **Mô phỏng**, tắt `switch.mo_phong_bat`. ESP32 ảo dùng chung entity với mạch thật.
2. Kiểm tra `/config/esphome/secrets.yaml` có đủ `wifi_ssid`, `wifi_password`, `mqtt_broker`, `mqtt_username`, `mqtt_password`, `smarthome_api_key`, `smarthome_ap_password`.
3. **Rút dây tín hiệu servo khỏi IO12** khi nạp lần đầu, vì IO12 là chân strapping.
4. HA → ESPHome Device Builder → thẻ **smarthome** → **Install** → **Manual download** → **Factory format**.
5. Trên máy tính, mở Chrome tại https://web.esphome.io. Cắm USB → **Connect** → chọn cổng COM → **Install** → chọn file vừa tải.
   - Báo "Failed to connect": giữ nút **BOOT** trên DevKit khi thanh tiến trình bắt đầu.
6. Xong thì cắm lại servo. Từ lần sau nạp qua mạng: **Install → Wirelessly** (máy HA phải cùng mạng với ESP32).

## 4. Thêm vào HA

Thiết bị gửi MQTT discovery nên **tự hiện** trong Cài đặt → Thiết bị → MQTT → **Smarthome**. Không cần thêm tích hợp ESPHome.
- Tên entity viết tiếng Việt có dấu, entity_id tự chuyển thành không dấu, ví dụ `switch.smarthome_den_hien`, `light.smarthome_den_rgb`.
- Một số entity cũ đổi tên sẽ thành "không khả dụng": LED dây phòng khách, Đèn bếp, Mức lửa bếp, Khí gas bếp, Chuyển động phòng khách, Đóng cửa ngay, và các bản `_2`. Bạn xóa chúng trong Cài đặt → Thực thể.

## 5. Lấy UID thẻ RFID

1. Quẹt thẻ lạ (còi bíp dài là bình thường).
2. Xem **Thẻ vừa quẹt** trên trang Điều khiển. UID có dạng `12-34-56-78`. Cũng có thể xem trong ESPHome → Logs.
3. Trang **Quản lý** → chạy "Lấy UID thẻ vừa quẹt" → đặt tên → "Thêm thẻ". Danh sách được gửi xuống ESP32 và lưu vào flash.
4. Quẹt lại: bíp ngắn, cửa mở.

## 6. Hiệu chỉnh

**Điểm 0 ACS712**
1. Tắt hết relay và đèn RGB, để cửa đứng yên. Lúc này chỉ còn ESP32 và các cảm biến tiêu thụ, khoảng 0,1–0,2 A.
2. Chờ 10 s, xem **Điện áp ACS712**. Giá trị phải ổn định quanh 2,4–2,6 V.
3. Bấm **Hiệu chuẩn ACS712 (0 A)**. Giá trị được lưu vào flash.
4. Bật một tải đã biết (ví dụ quạt), xem **Dòng tổng 5V** có hợp lý không.

Lưu ý: bản 20A chỉ có 100 mV/A, trong khi nhiễu ADC khoảng ±10–20 mV, tức sai số khoảng ±0,1–0,2 A. Firmware coi dòng dưới 0,1 A là 0. Vì đã hiệu chuẩn khi ESP32 đang chạy, số hiển thị là **dòng của tải**, không gồm ESP32.

**Ngưỡng ánh sáng**
1. Xem **Cảm biến ánh sáng** (%) lúc phòng sáng bình thường, rồi lấy tay che quang trở.
2. Đặt **Ngưỡng trời tối** ở khoảng giữa hai giá trị đó. "Trời tối" bật khi ánh sáng < ngưỡng và tắt khi > ngưỡng + 10 %.
3. Nếu che tay mà % lại *tăng*: module ra ngược chiều. Đổi lambda thành `return x / 3.3f * 100.0f;`.

**MQ-2**: chân **AO** nối thẳng **IO39** (ADC1; IO15 thuộc ADC2 nên không đọc analog được khi Wi-Fi chạy), DO để trống. Sấy 2–3 phút, xem "Mức khí gas" ở không khí sạch (thường 0,2–1 V), rồi đặt "Ngưỡng báo gas" cao hơn mức đó khoảng 0,5 V. Biến trở trên module không còn tác dụng. Firmware bỏ qua gas trong 60 s đầu.

**PIR HC-SR501**: vặn biến trở thời gian về mức nhỏ nhất. Jumper đặt ở **H** (lặp lại). Thời gian giữ đèn do HA chỉnh.

## 7. Checklist test sau khi nạp

| # | Thiết bị | Cách test | Kết quả đúng |
|---|---|---|---|
| 1 | Kết nối | Mở trang Điều khiển | "Kết nối" = Đã kết nối, có Wi-Fi dBm |
| 2 | Relay ×4 | Bật/tắt từng cái trên HA | Đúng relay kêu tách, đúng đèn/quạt. Lúc khởi động tất cả TẮT |
| 3 | Đèn RGB | Chọn đỏ, lục, lam | Cả 2 đèn cùng màu đúng |
| 4 | Còi | Bật/tắt "Còi" | Kêu khi bật, im khi tắt |
| 5 | Cửa (công tắc từ) | Tách nam châm | "Cửa chính" = Mở; áp lại = Đóng |
| 6 | Servo | Bấm "Mở cửa" | Bíp ngắn, quay ngược chiều kim đồng hồ 80°, sau 5 s quay cùng chiều 80° đóng lại |
| 7 | Cửa vướng | Bấm Mở cửa, lấy tay giữ cửa khi đóng | Mở lại + bíp dài, sau 3 lần: "Cửa bị vướng" + thông báo |
| 8 | RFID | Quẹt thẻ hợp lệ / thẻ lạ / thẻ lạ 3 lần | Mở cửa / bíp dài + thông báo / còi 5 s |
| 9 | PIR + đèn hiên | Che quang trở, vẫy tay | Đèn hiên bật, tắt sau X phút không chuyển động |
| 10 | Ánh sáng | Che / chiếu đèn | % giảm / tăng |
| 11 | DHT11 | Hà hơi vào cảm biến | Độ ẩm tăng ≥ 75 % → quạt hút bật |
| 12 | Lửa | Bật lửa cách 20–30 cm | Còi + nháy đỏ + thông báo; bấm "Tắt báo động" thì im còi |
| 13 | Gas | Xịt gas bật lửa (không đánh lửa) gần MQ-2 | Còi + nháy đỏ + **quạt hút bật** + thông báo |
| 14 | Vắng nhà | Bật, chờ 30 s, mở cửa hoặc vẫy tay trước PIR | Còi + nháy đỏ + thông báo "Đột nhập" |
| 15 | Báo động offline | Tắt Wi-Fi router, thử lửa | Còi + nháy đỏ vẫn chạy |
| 16 | Dòng điện | Bật lần lượt các tải | Dòng/công suất tăng theo, biểu đồ có dữ liệu |

## 8. Lỗi thường gặp

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Không boot / không nạp được, log lặp `flash read err` | IO12 bị kéo lên khi khởi động | Rút servo khi nạp. Không thêm trở kéo lên vào IO12. Kiểm tra servo không cấp ngược điện áp vào chân tín hiệu |
| Relay chạy ngược (bật HA thì relay tắt) | Module relay kích mức cao | Bỏ `inverted: true` ở relay đó |
| Relay nháy lúc cấp điện | IO5 xuất PWM khi boot | Bình thường với IO5. Đèn hiên chớp chưa tới 1 s |
| Còi kêu liên tục / kêu ngược | Sai mức kích | Đổi `buzzer_inverted` thành `"false"` |
| Còi kêu "tạch" lúc khởi động | IO13 thả nổi trước khi firmware chạy | Bình thường; muốn hết thì thêm trở 10k từ IO13 lên 3V3 |
| RC522 không đọc, log `Communication with RC522 failed` | Sai dây SPI, cấp 5V, RST không lên 3V3 | Kiểm tra SCK 25, MOSI 26, MISO 33, SDA 27, VCC **3V3**, RST nối 3V3 |
| RC522 đọc chập chờn | Dây SPI dài, nguồn 3V3 yếu | Rút ngắn dây, thêm tụ 10 µF tại VCC module |
| Servo rung, ESP32 khởi động lại khi cửa quay | Sụt áp 5V | Cấp servo từ bus 5V, thêm tụ 470 µF tại servo |
| Cửa bị báo vướng dù đã đóng | Công tắc từ lệch hoặc mất trở kéo lên | Kiểm tra trở 1k IO34 → 3V3, chỉnh vị trí nam châm |
| DHT11 báo `nan` | Sai chân, cảm biến chưa ổn định | Đợi 20 s; kiểm tra DATA → IO19 |
| Dòng nhảy lung tung / âm | Chưa hiệu chuẩn, nhiễu ADC | Hiệu chuẩn lại; bản 20A có sai số khoảng ±0,1 A |
| "Trời tối" ngược | Module ra ngược chiều | Đổi công thức (mục 6) |
| Báo gas ngay khi cắm điện | MQ-2 chưa sấy, ngưỡng quá thấp | Chờ 2–3 phút, tăng "Ngưỡng báo gas" trên HA |
| Không thấy thiết bị trong HA | MQTT sai, ESP32 ảo đang chạy | Xem log ESPHome, kiểm tra secrets, tắt mô phỏng |
| Cảnh báo điện áp | Module cấp 5V nhưng chân ra nối thẳng ESP32 | Lửa (IO18), quang trở (IO32), DHT (IO19), RC522 phải cấp **3V3**. ACS712 có cầu chia áp; MQ-2 AO nối thẳng IO39 (ít khi vượt 3,3 V, chỉ khi gas rất đậm) |
