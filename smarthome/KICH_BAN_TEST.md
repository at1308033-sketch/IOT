# Kịch bản test sự kiện Smarthome

> Cập nhật 18/10/2026, đọc từ `esphome/smarthome.yaml`, `smarthome/ha_package.yaml`, Node-RED.
> Cột **Kích hoạt / Nhận / Đạt** để trống — ghi giờ (hh:mm:ss) lúc làm thao tác và lúc thấy kết quả.
> Xem giờ chính xác tới mili-giây: HA → entity → **Lịch sử** (hoặc Nhật ký).

## 0. Chuẩn bị trước khi test

| Hạng mục | Giá trị hiện tại | Chỉnh ở đâu |
|---|---|---|
| Chế độ tự động | Bật | `switch.smarthome_che_do_tu_dong` |
| Chế độ vắng nhà | Tắt | `switch.smarthome_che_do_vang_nha` |
| Thời gian mở cửa (tự đóng sau) | 10 s | `number.smarthome_thoi_gian_mo_cua` |
| Thời gian quay mở | 700 ms | `number.smarthome_thoi_gian_quay_mo` |
| Đèn hiên tắt sau | 2 phút | `number.smarthome_den_hien_tat_sau` |
| Ngưỡng trời tối | 30 % (sáng lại khi > 40 %) | `number.smarthome_nguong_troi_toi` |
| Ngưỡng báo gas | 1,5 V (hết khi < 1,3 V) | `number.smarthome_nguong_bao_gas` |
| Độ ẩm bật quạt | 58 % (tắt khi ≤ 53 %) | `number.smarthome_do_am_bat_quat` |
| Thẻ hợp lệ | 12-34-56-78 (+ thẻ trong trang Quản lý) | Trang **Quản lý** |
| Bảng mô phỏng Node-RED | **Tắt** | `switch.mo_phong_bat` |

## 1. Thông số thời gian (cố định trong firmware)

| Bộ phận | Thời gian |
|---|---|
| RFID quét thẻ | mỗi **1 s** |
| Bíp ngắn / dài / khóa | 120 ms / 1,5 s / 15 × 0,3 s ≈ 4,5 s |
| Đóng cửa | quay tới khi cảm biến báo đóng, tối đa **1,5 s**, quay thêm 100 ms |
| Cửa vướng | thử **3 lần**, mỗi lần ≈ 5,4 s (đóng 1,5 s → mở lại 0,8 s → chờ 3 s) |
| PIR | báo ON sau **200 ms**; hết cử động: module 3–5 s + firmware **10 s** |
| Cảm biến ánh sáng | đọc 2 s, trung bình 5 mẫu, "Trời tối" đổi sau 3 s ổn định |
| Lửa | báo sau **300 ms**, hết sau 3 s |
| Gas | đọc 1 s, trung bình 3 mẫu, báo sau **1 s**, hết sau 5 s; **bỏ qua 60 s đầu** sau khởi động |
| Báo động (còi + RGB) | kiểm tra mỗi **0,5 s** |
| Vắng nhà | **30 s** đầu để ra khỏi nhà (không báo đột nhập) |
| DHT11 | đọc mỗi **10 s** |
| HA: offline | báo sau **2 phút** mất kết nối |
| HA: lịch sử MariaDB | đọc lại **1 s** sau mỗi sự kiện |
| Node-RED: danh sách thẻ | gửi cho ESP32 khi khởi động + mỗi giờ + khi sửa thẻ |

---

## 2. Cửa & thẻ RFID

```
Quẹt thẻ ─≤1s─▶ bíp ─▶ quay mở 0,7s ─▶ chờ 10s ─▶ quay đóng ≤1,5s ─▶ dừng
          └────────────────── tổng ≈ 11–13 s ──────────────────┘
```

| Mã | Điều kiện trước | Thao tác | Kết quả mong đợi | Thời gian kỳ vọng | Xem ở đâu | Kích hoạt | Nhận | Đạt |
|---|---|---|---|---|---|---|---|---|
| C1 | Cửa đóng | Quẹt **thẻ đúng** | Bíp ngắn, cửa mở; "Thẻ vừa quẹt" = UID; lịch sử ghi *granted / rfid* | Cửa mở ≤ 1,5 s; lịch sử ≤ 3 s | `binary_sensor.smarthome_cua_chinh`, trang Lịch sử truy cập | | | |
| C2 | Sau C1 | Không làm gì | Cửa **tự đóng** | ≈ 10–12 s sau khi cửa mở | `binary_sensor.smarthome_cua_chinh` → Đóng | | | |
| C3 | Cửa đóng | Quẹt **thẻ sai** 1 lần | Bíp dài 1,5 s; điện thoại báo "❌ Có người quẹt sai thẻ" (nút Mở cửa / Bỏ qua); lịch sử *denied* | Thông báo ≤ 3 s | Điện thoại, Lịch sử truy cập | | | |
| C4 | Cửa đóng | Quẹt thẻ sai **3 lần liên tiếp** | Lần 3: còi bíp liên tục ≈ 4,5 s; điện thoại "🚨 Sai thẻ 3 lần"; lịch sử *lockout* | Bíp ngay; thông báo ≤ 3 s | Điện thoại, Lịch sử truy cập | | | |
| C5 | Sau C3/C4 | Bấm **"Mở cửa"** trong thông báo | Cửa mở, tự đóng sau 10 s; lịch sử *granted / phone* | Cửa mở ≤ 2 s | `binary_sensor.smarthome_cua_chinh` | | | |
| C6 | Cửa đóng | Bấm nút **"Mở cửa"** trên dashboard | Cửa mở, tự đóng sau 10 s; lịch sử *granted / remote* | ≤ 1,5 s | Dashboard | | | |
| C7 | Cửa đang mở (trong 10 s) | Bấm nút **"Đóng cửa"** | Đóng ngay, không chờ hết 10 s | ≤ 2 s | Dashboard | | | |
| C8 | Cửa đóng | Điện thoại Izth **chạm thẻ NFC** cửa chính | Cửa mở; điện thoại "Đã mở cửa chính bằng NFC"; lịch sử *phone* | ≤ 3 s | Điện thoại | | | |
| C9 | Cửa đóng | Nói với Assist **"mở cửa"** | Cửa mở, tự đóng sau 10 s | ≤ 3 s | Assist | | | |
| C10 | Sau C1 | Lấy tay **chặn cửa** lúc nó tự đóng | Thử đóng 3 lần (mỗi lần mở lại + bíp dài) → để cửa mở; "Cửa bị vướng" ON; điện thoại "🚪 Cửa chính bị vướng" | ≈ 16 s từ lúc bắt đầu đóng | `binary_sensor.smarthome_cua_bi_vuong` | | | |
| C11 | Đang C10 (vướng) | Bỏ tay, quẹt thẻ đúng | "Cửa bị vướng" OFF, mở rồi tự đóng bình thường | như C1 + C2 | `binary_sensor.smarthome_cua_bi_vuong` | | | |
| C12 | Mở cửa bằng tay | Rút nguồn ESP32 rồi cắm lại | Khởi động xong tự quay đóng cửa | ≈ 10–20 s (khởi động + kết nối) | `binary_sensor.smarthome_cua_chinh` | | | |

## 3. PIR & đèn hiên

```
Vẫy tay ─0,2s─▶ PIR ON ─▶ (nếu Tự động + Trời tối) bật đèn hiên
Ngừng   ─3–5s (module) + 10s─▶ PIR OFF ─▶ đếm 2 phút ─▶ tắt đèn hiên
```

| Mã | Điều kiện trước | Thao tác | Kết quả mong đợi | Thời gian kỳ vọng | Xem ở đâu | Kích hoạt | Nhận | Đạt |
|---|---|---|---|---|---|---|---|---|
| P1 | PIR OFF | **Vẫy tay** trước PIR | "Chuyển động trước nhà" ON (biểu tượng vàng) | ≤ 1 s | `binary_sensor.smarthome_chuyen_dong_truoc_nha` | | | |
| P2 | Sau P1 | **Ngừng cử động** / tránh khỏi tầm nhìn | PIR OFF (biểu tượng xám) | ≈ 13–15 s | như trên | | | |
| P3 | Tự động **bật**, đèn hiên tắt | **Che quang trở** | "Trời tối" ON khi ánh sáng < 30 % | ≈ 5–13 s | `binary_sensor.smarthome_troi_toi`, `sensor.smarthome_cam_bien_anh_sang` | | | |
| P4 | Sau P3 (trời tối) | Vẫy tay trước PIR | **Đèn hiên bật** | ≤ 1 s | `switch.smarthome_den_hien` | | | |
| P5 | Sau P4 | Ngừng cử động | PIR OFF → **đèn hiên tự tắt** | ≈ 2 phút 15 s sau khi ngừng | `switch.smarthome_den_hien` | | | |
| P6 | Đèn hiên đang chờ tắt (P5) | Vẫy tay lại | Hủy đếm, đèn vẫn sáng; đếm lại 2 phút khi PIR OFF | — | `switch.smarthome_den_hien` | | | |
| P7 | Đang vẫy tay (PIR ON), trời sáng | **Che quang trở** | Đèn hiên bật khi "Trời tối" lên ON | ≈ 5–13 s | `switch.smarthome_den_hien` | | | |
| P8 | Trời tối | **Bật đèn hiên bằng tay**, rồi vẫy tay và ngừng | Đèn **không** tự tắt (bật tay thì giữ) | — | `switch.smarthome_den_hien` | | | |
| P9 | **Tắt** Chế độ tự động, trời tối | Vẫy tay | Đèn hiên **không** bật | — | `switch.smarthome_den_hien` | | | |
| P10 | Trời sáng (không che LDR) | Vẫy tay | PIR ON nhưng đèn hiên **không** bật | — | `switch.smarthome_den_hien` | | | |

## 4. Báo động (cháy, gas, đột nhập)

Khi báo động: **còi kêu liên tục + RGB nháy đỏ**, điện thoại nhận thông báo (kêu cả khi để im lặng) có nút **"Tắt báo động"**.

| Mã | Điều kiện trước | Thao tác | Kết quả mong đợi | Thời gian kỳ vọng | Xem ở đâu | Kích hoạt | Nhận | Đạt |
|---|---|---|---|---|---|---|---|---|
| A1 | Không báo động | Đưa **lửa** (bật lửa) gần cảm biến lửa | "Báo cháy bếp" ON, còi + RGB nháy đỏ; điện thoại "🔥 Phát hiện LỬA ở bếp"; DB ghi *alarm/fire/on* | Còi ≤ 1 s; thông báo ≤ 3 s | `binary_sensor.smarthome_bao_chay_bep` | | | |
| A2 | Sau A1 | **Tắt lửa** | "Báo cháy bếp" OFF, còi tắt, RGB tắt | ≈ 3–4 s | như trên | | | |
| A3 | ESP32 đã chạy > 60 s | Xịt **gas** (bật lửa không đánh lửa) vào MQ-2 | "Mức khí gas" > 1,5 V → "Báo khí gas bếp" ON, còi + RGB, **quạt hút bật**; điện thoại "💨 Rò KHÍ GAS" | ≈ 2–4 s | `sensor.smarthome_muc_khi_gas`, `binary_sensor.smarthome_bao_khi_gas_bep`, `switch.smarthome_quat_hut_phong_ngu` | | | |
| A4 | Sau A3 | Chờ gas tan | Mức < 1,3 V → gas OFF, còi + RGB tắt, quạt trở lại theo độ ẩm | ≈ 5–8 s sau khi < 1,3 V | như trên | | | |
| A5 | ESP32 **vừa khởi động** (< 60 s) | Xịt gas | **Không** báo (MQ-2 đang làm nóng) | — | `binary_sensor.smarthome_bao_khi_gas_bep` | | | |
| A6 | Đang báo động (A1 hoặc A3) | Bấm **"Tắt báo động"** (dashboard / nút trong thông báo / nói "tắt còi") | Còi im ngay; RGB **vẫn nháy** tới khi hết lửa/gas | ≤ 1 s | `switch.smarthome_coi` | | | |
| A7 | Tắt vắng nhà | Bật **Chế độ vắng nhà** | Bíp ngắn | ngay | `switch.smarthome_che_do_vang_nha` | | | |
| A8 | Vắng nhà bật **< 30 s** | Vẫy tay PIR / mở cửa bằng tay | **Không** báo đột nhập | — | `binary_sensor.smarthome_bao_dong_dot_nhap` | | | |
| A9 | Vắng nhà bật **> 30 s** | **Vẫy tay** trước PIR | "Báo động đột nhập" ON, còi + RGB; điện thoại "🚨 Đột nhập khi vắng nhà — Có chuyển động trước nhà" | Còi ≤ 1 s; thông báo ≤ 3 s | `binary_sensor.smarthome_bao_dong_dot_nhap` | | | |
| A10 | Vắng nhà bật **> 30 s** | **Mở cửa bằng tay** | Như A9, thông báo "Cửa chính vừa mở" | như A9 | như trên | | | |
| A11 | Đang đột nhập | Bấm "Tắt báo động" **hoặc** tắt vắng nhà | Đột nhập **xóa hẳn**, còi + RGB tắt | ≤ 1 s | như trên | | | |
| A12 | Vắng nhà bật > 30 s | **Quẹt thẻ đúng** | Vắng nhà tự **tắt**, cửa mở, **không** báo đột nhập | ≤ 1,5 s | `switch.smarthome_che_do_vang_nha` | | | |
| A13 | Đang báo động | Quẹt thẻ (đúng/sai) | Bíp thẻ **không** chen vào; còi vẫn kêu liên tục | — | Nghe còi | | | |

## 5. Môi trường

| Mã | Điều kiện trước | Thao tác | Kết quả mong đợi | Thời gian kỳ vọng | Xem ở đâu | Kích hoạt | Nhận | Đạt |
|---|---|---|---|---|---|---|---|---|
| E1 | Tự động bật, quạt tắt | **Thở / hà hơi** vào DHT11 cho độ ẩm ≥ 58 % | **Quạt hút** bật | ≤ 10 s (chu kỳ đọc) | `sensor.smarthome_do_am_phong_ngu`, `switch.smarthome_quat_hut_phong_ngu` | | | |
| E2 | Sau E1 | Để độ ẩm giảm | Quạt tắt khi ≤ 53 % | ≤ 10 s sau khi ≤ 53 % | như trên | | | |
| E3 | Quạt đang bật do độ ẩm | **Tắt quạt bằng tay** | Quạt giữ tắt (chỉ tự bật lại khi độ ẩm vượt ngưỡng lần nữa) | — | như trên | | | |
| E4 | **Tắt** Chế độ tự động | Xịt gas (như A3) | Quạt **vẫn bật** (gas luôn ưu tiên) | ≈ 2–4 s | `switch.smarthome_quat_hut_phong_ngu` | | | |
| E5 | Đang tắt tự động, độ ẩm cao | **Bật lại** Chế độ tự động | Quạt bật ngay theo độ ẩm | ≤ 1 s | như trên | | | |

## 6. Thông báo & hệ thống

| Mã | Điều kiện trước | Thao tác | Kết quả mong đợi | Thời gian kỳ vọng | Xem ở đâu | Kích hoạt | Nhận | Đạt |
|---|---|---|---|---|---|---|---|---|
| S1 | ESP32 online | **Rút nguồn** ESP32 | "Kết nối" OFF, mọi entity unavailable | ≈ 15–25 s | `binary_sensor.smarthome_ket_noi` | | | |
| S2 | Sau S1 | Tiếp tục để mất nguồn | Điện thoại "⚠️ Smarthome offline" | ≈ 2 phút sau khi "Kết nối" OFF | Điện thoại | | | |
| S3 | ESP32 offline | Điện thoại chạm thẻ NFC | Điện thoại "Không mở được cửa — ESP32 đang offline" | ≤ 3 s | Điện thoại | | | |
| S4 | — | Trang Quản lý: **thêm thẻ** mới | "Số thẻ hợp lệ" tăng; quẹt thẻ đó mở được cửa | ≤ 3 s | `sensor.smarthome_so_the_hop_le` | | | |
| S5 | Sau S4 | **Khóa / xóa** thẻ đó | "Số thẻ hợp lệ" giảm; quẹt thẻ đó bị *denied* | ≤ 3 s | như trên | | | |
| S6 | — | Trang Quản lý: **Lấy UID thẻ vừa quẹt** | Ô UID điền sẵn mã thẻ vừa quẹt | ngay | Trang Quản lý | | | |
| S7 | Sau mỗi sự kiện cửa/thẻ/báo động | — | Trang Lịch sử truy cập + bảng sự kiện cập nhật | ≈ 1–3 s | Trang Lịch sử truy cập | | | |
| S8 | Tắt WiFi / broker MQTT | Đưa lửa gần cảm biến | Còi + RGB **vẫn chạy** trên mạch (không có thông báo điện thoại) | ≤ 1 s | Nghe còi | | | |

---

## 7. Kịch bản kết hợp

Làm theo thứ tự từng bước, mỗi bước ghi giờ.

### K1 · Về nhà buổi tối
| Bước | Thao tác | Kết quả mong đợi | Giờ | Đạt |
|---|---|---|---|---|
| 1 | Bật Chế độ vắng nhà, chờ > 30 s | Bíp ngắn | | |
| 2 | Che quang trở | "Trời tối" ON | | |
| 3 | Quẹt **thẻ đúng** | Vắng nhà tự tắt, cửa mở, **không** còi | | |
| 4 | Đi ngang PIR (vẫy tay) | Đèn hiên bật | | |
| 5 | Chờ | Cửa tự đóng sau 10 s | | |
| 6 | Ngừng cử động | Đèn hiên tắt sau ≈ 2 phút 15 s | | |

### K2 · Người lạ khi vắng nhà
| Bước | Thao tác | Kết quả mong đợi | Giờ | Đạt |
|---|---|---|---|---|
| 1 | Bật Chế độ vắng nhà, chờ > 30 s | Bíp ngắn | | |
| 2 | Quẹt **thẻ sai 3 lần** | Bíp khóa ≈ 4,5 s; điện thoại "Sai thẻ 3 lần" | | |
| 3 | Vẫy tay trước PIR | Đột nhập: còi + RGB, điện thoại "Đột nhập khi vắng nhà" | | |
| 4 | Bấm "Tắt báo động" **trong thông báo điện thoại** | Còi + RGB tắt, đột nhập OFF | | |
| 5 | Vẫy tay lại (vắng nhà vẫn bật) | Báo đột nhập **lần nữa** | | |
| 6 | Tắt Chế độ vắng nhà | Hết báo động | | |

### K3 · Cháy + gas cùng lúc
| Bước | Thao tác | Kết quả mong đợi | Giờ | Đạt |
|---|---|---|---|---|
| 1 | Đưa lửa gần cảm biến lửa | Còi + RGB; thông báo 🔥 | | |
| 2 | Xịt gas vào MQ-2 | Quạt hút bật; thông báo 💨 (2 thông báo riêng) | | |
| 3 | Nói "tắt còi" với Assist | Còi im; Assist trả lời "Đèn vẫn nháy đỏ tới khi hết lửa hoặc gas" | | |
| 4 | Tắt lửa | RGB vẫn nháy (còn gas) | | |
| 5 | Chờ gas tan | RGB tắt; quạt trở lại theo độ ẩm | | |

### K4 · Cửa vướng rồi tự xử lý
| Bước | Thao tác | Kết quả mong đợi | Giờ | Đạt |
|---|---|---|---|---|
| 1 | Quẹt thẻ đúng | Cửa mở | | |
| 2 | Sau 10 s, lấy tay chặn cửa | 3 lần thử, mỗi lần mở lại + bíp dài | | |
| 3 | Giữ chặn tới hết | "Cửa bị vướng" ON; điện thoại báo | | |
| 4 | Bỏ tay, bấm "Đóng cửa" | Cửa đóng, "Cửa bị vướng" OFF | | |

### K5 · Mất mạng vẫn an toàn
| Bước | Thao tác | Kết quả mong đợi | Giờ | Đạt |
|---|---|---|---|---|
| 1 | Tắt WiFi "<SSID>" (hoặc rút mạng broker) | "Kết nối" OFF sau ≈ 20 s | | |
| 2 | Quẹt thẻ đúng | Cửa **vẫn mở** (danh sách thẻ lưu trong ESP32) | | |
| 3 | Đưa lửa gần cảm biến | Còi + RGB **vẫn chạy** | | |
| 4 | Chờ > 2 phút | Điện thoại "Smarthome offline" | | |
| 5 | Bật lại WiFi | "Kết nối" ON; HA nhận lại trạng thái | | |

---

## Ghi chú khi test
- **Không ghi vào MariaDB:** chuyển động PIR bình thường, độ ẩm, quạt — chỉ có trong lịch sử HA. Cửa, thẻ, báo động thì có.
- **PIR luôn ON khi bạn ngồi trong tầm nhìn** (~3 m, góc 110°) — jumper H giữ ON suốt khi còn cử động.
- **Đèn hiên** chỉ do firmware điều khiển (automation "Đèn hiên theo trời tối/sáng" trong HA đang tắt).
- Thời gian "Nhận" ở điện thoại phụ thuộc mạng — chậm hơn 1–3 s so với HA là bình thường.
