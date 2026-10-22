-- =====================================================================
-- Smarthome đồ án — database "smarthome" (MariaDB add-on, host core-mariadb)
-- Thời gian lưu theo giờ Việt Nam (UTC+7), kiểu DATETIME.
--   ts_device : giờ ESP32 ghi nhận (SNTP) — NULL nếu ESP32 chưa đồng bộ giờ
--   ts_server : giờ Node-RED nhận được sự kiện
-- Tài khoản: smarthome_admin (tạo bảng) · nodered_rw (ghi/đọc) · ha_ro (chỉ đọc)
-- =====================================================================
SET NAMES utf8mb4;

-- Thẻ RFID được phép mở cửa (danh sách gốc, ESP32 nhận bản sao qua MQTT)
CREATE TABLE IF NOT EXISTS cards (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  uid         VARCHAR(32)  NOT NULL,
  holder_name VARCHAR(100) NOT NULL DEFAULT '',
  active      TINYINT(1)   NOT NULL DEFAULT 1,
  note        VARCHAR(255) NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cards_uid (uid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Lịch sử truy cập cửa chính
CREATE TABLE IF NOT EXISTS access_log (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ts_device   DATETIME NULL,
  ts_server   DATETIME NOT NULL,
  uid         VARCHAR(32)  NOT NULL DEFAULT '',
  card_id     INT UNSIGNED NULL,
  holder_name VARCHAR(100) NULL COMMENT 'Tên chủ thẻ tại thời điểm quẹt',
  result      ENUM('granted','denied','lockout') NOT NULL,
  method      ENUM('rfid','remote','phone') NOT NULL COMMENT 'phone: uid = tên điện thoại',
  KEY idx_access_ts (ts_server),
  KEY idx_access_uid (uid),
  CONSTRAINT fk_access_card FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sự kiện khác: cửa mở/đóng, báo cháy
CREATE TABLE IF NOT EXISTS events (
  id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ts_device DATETIME NULL,
  ts_server DATETIME NOT NULL,
  type      VARCHAR(20) NOT NULL COMMENT 'door | alarm',
  kind      VARCHAR(20) NOT NULL COMMENT 'main | fire',
  state     VARCHAR(20) NOT NULL COMMENT 'open/closed | on/off',
  KEY idx_events_type_ts (type, ts_server)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Lịch sử truy cập kèm nhãn tiếng Việt (dùng cho dashboard / báo cáo)
CREATE OR REPLACE VIEW v_access_log AS
SELECT a.id,
       COALESCE(a.ts_device, a.ts_server)                           AS ts,
       a.uid,
       CASE WHEN a.method = 'phone' THEN CONCAT('Điện thoại ', a.uid)
            ELSE COALESCE(NULLIF(a.holder_name, ''), IF(a.method = 'remote', 'Mở từ xa', 'Không rõ')) END AS who,
       a.result,
       CASE a.result WHEN 'granted' THEN 'Hợp lệ' WHEN 'denied' THEN 'Sai thẻ' ELSE 'Khóa tạm (sai 3 lần)' END AS result_vi,
       a.method
FROM access_log a;

-- Nâng cấp 05/10/2026: thêm cách mở 'phone' (chạm NFC / nút thông báo trên điện thoại)
-- ALTER TABLE access_log MODIFY method ENUM('rfid','remote','phone') NOT NULL COMMENT 'phone: uid = tên điện thoại';
