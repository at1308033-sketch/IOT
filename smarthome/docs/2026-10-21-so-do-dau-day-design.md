# Sơ đồ đấu dây mạch Smarthome — thiết kế (21/10/2026)

## Mục tiêu
Sơ đồ đi dây/lắp đặt khớp đúng mạch thật để chèn báo cáo và mở trên Wokwi. Không cần chạy code.

## Sản phẩm (`SmartHome_BaoCao/so_do_day/`)
| File | Nội dung |
|---|---|
| `so_do_dau_day.svg/.png` | Hình chính: ESP32 DevKit V1 30 chân trên board mở rộng ở giữa; cảm biến + RC522 bên trái, RGB/DHT11/lửa/relay 4 kênh bên phải; khối nguồn adapter 5 V → ACS712 (IP+ → IP−) → jack board; cầu chia 1k/2k vào IO36; trở kéo lên 1k IO34 → 3V3; tải qua COM/NO relay; PIR dây 5 V riêng |
| `vi_tri_lap_dat.png` | Mặt bằng 4 phòng, đánh dấu chỗ đặt linh kiện (không vẽ dây) |
| `bang_dau_day.md` | Bảng từng sợi dây: từ chân → tới chân, màu, ghi chú |
| `wokwi/` | `diagram.json` + 6 custom chip (adapter, ACS712, MC-38, module còi, cảm biến lửa — `wokwi-flame-sensor` có hình nhưng editor/lint không nhận —, quạt) + README + `xem_truoc.png`; DHT11 → DHT22, relay 4 kênh → 4 relay đơn `transistor: pnp`; VIN của ESP32 đóng vai jack board. `wokwi-cli lint` 0 lỗi |

Đã làm 21/10: `day_noi.py` (bảng dây + kiểm tra firmware), `ve_so_do_day.py` (hình chính, tự kiểm tra không có 2 dây khác mạng chồng nhau), `ve_bang_dau_day.py`, `ve_vi_tri.py` (cần matplotlib), `ve_wokwi.py`, `xem_truoc_wokwi.py` (cần Playwright) — tất cả trong `bao_cao/_build/`.

Quy ước màu: đỏ 5 V, cam 3V3, đen GND, tím đường dòng tải qua ACS712, mỗi nhóm tín hiệu một màu.

## Cách làm
- Dữ liệu duy nhất: `bao_cao/_build/day_noi.py` (linh kiện, chân, dây). Mọi hình và `diagram.json` sinh từ đây.
- Kiểm tra tự động: đọc `esphome/smarthome.yaml`, báo lỗi nếu GPIO nào trong sơ đồ khác firmware.
- SVG → PNG bằng `rsvg-convert`; hình linh kiện lấy từ `@wokwi/elements` 1.9.2 và `wokwi-boards` (MIT) khi có, còn lại tự vẽ.

## Giả định (người dùng đồng ý 21/10)
1. Relay IN1 = IO5 đèn hiên, IN2 = IO17 đèn khách, IN3 = IO16 đèn ngủ, IN4 = IO4 quạt hút; bus 5 V → COM, NO → tải (+), tải (−) → GND.
2. Adapter 5 V cắm jack DC board mở rộng; module 5 V (relay, servo, còi, MQ-2, ACS712, PIR) lấy hàng chân 5V của board, module 3V3 (RC522, DHT11, lửa, quang trở) lấy hàng chân 3V3.
3. Thứ tự chân module theo loại phổ biến; trên hình luôn ghi tên chân.
4. Không vẽ các tụ 470 µF / 10 µF (chỉ là khuyến nghị).
