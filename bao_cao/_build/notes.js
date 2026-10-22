// Ghi chú thuyết trình (tiếng Việt) cho từng slide — nguồn duy nhất cho phần Notes trong .pptx
// và file SmartHome_Presentation_Notes.md. Mọi số liệu lấy từ SmartHome_Evidence_Map.md.
module.exports = [
  {
    title: 'Tiêu đề',
    time: '0:20',
    say: [
      'Kính chào thầy/cô. Nhóm em gồm 3 thành viên, xin trình bày đề tài: mô hình nhà thông minh dùng ESP32, MQTT và Home Assistant.',
      'Mô hình gồm phòng khách, bếp, phòng ngủ và cửa chính phía trước; hình bên phải là trang Mô hình 3D trên dashboard, chụp lúc mạch đang chạy.',
    ],
    detail: [],
    next: 'Trước hết, em xin nói về bài toán mà đề tài giải quyết.',
  },
  {
    title: 'Bài toán & mục tiêu',
    time: '0:50',
    say: [
      'Ba nhu cầu chính của một ngôi nhà: an toàn trước cháy và rò gas, kiểm soát người ra vào, và theo dõi, điều khiển từ xa.',
      'Điểm nhóm quan tâm nhất: nếu mọi xử lý đều nằm trên server thì khi mất Wi-Fi, chức năng báo cháy cũng mất theo. Vì vậy mục tiêu là các kịch bản an toàn phải chạy ngay trên mạch.',
      'Phạm vi đã làm: một ESP32 với 8 cảm biến, 4 relay, servo cửa, còi và LED RGB; phía server có dashboard, lịch sử ra vào, thông báo điện thoại và điều khiển bằng giọng nói.',
    ],
    detail: ['Đèn và quạt trong mô hình chạy bus 5 V; công suất được ước tính bằng dòng × 5 V (HUONG_DAN_ESP32.md, mục 1).'],
    next: 'Để đạt mục tiêu đó, nhóm chọn kiến trúc như sau.',
  },
  {
    title: 'Kiến trúc hệ thống',
    time: '1:20',
    say: [
      'Ở dưới là mạch ESP32: đọc cảm biến, điều khiển relay, servo, còi, và tự chạy các kịch bản an toàn.',
      'ESP32 nói chuyện với server duy nhất qua MQTT, broker là Mosquitto. Home Assistant nhận thiết bị tự động nhờ MQTT discovery, nên mỗi cảm biến và công tắc trên mạch thành một entity trong HA.',
      'Node-RED lắng nghe các sự kiện cửa, thẻ, báo động và ghi vào MariaDB. Home Assistant đọc lại MariaDB bằng tài khoản chỉ đọc để hiển thị lịch sử.',
      'Người dùng chỉ làm việc với Home Assistant: dashboard, thông báo trên điện thoại và trợ lý giọng nói.',
    ],
    detail: [
      'Server là Home Assistant OS 18.3 chạy trên máy ảo x86-64; Mosquitto 7.1.1, MariaDB và Node-RED 22.1.0 là add-on.',
      'ESP32 còn có trang web riêng (cổng 80, đăng nhập digest) để điều khiển dự phòng khi HA hỏng.',
    ],
    next: 'Tiếp theo là phần cứng cụ thể trên mạch.',
  },
  {
    title: 'Phần cứng',
    time: '1:00',
    say: [
      'Bộ điều khiển là ESP32 DevKit V1 loại 30 chân.',
      'Bên trái là 8 cảm biến: đầu đọc thẻ RC522 qua SPI, công tắc từ ở cửa, PIR, quang trở, DHT11, cảm biến lửa, MQ-2 và ACS712 đo dòng tổng.',
      'Bên phải là ngõ ra: relay 4 kênh cho đèn hiên, đèn khách, đèn ngủ và quạt hút; servo quay cửa; còi; hai đèn LED RGB dùng chung ba chân PWM.',
    ],
    detail: [
      'Relay và còi kích mức thấp nên firmware khai báo inverted.',
      'ACS712 nuôi 5 V nên ngõ ra đi qua cầu chia 1k/2k; firmware nhân lại 1,5 để ra điện áp thật.',
      'MQ-2 nối vào IO39 (ADC1) vì ADC2 không đọc được khi Wi-Fi đang chạy.',
    ],
    next: 'Phần mềm trên mạch và trên server được phân vai như sau.',
  },
  {
    title: 'Phần mềm & phân vai',
    time: '0:50',
    say: [
      'Firmware viết bằng ESPHome: cấu hình YAML, phần logic phức tạp viết bằng lambda C++.',
      'Nguyên tắc phân vai: cái gì cần chạy khi mất mạng thì đặt trên ESP32 — cửa, báo cháy, gas, đèn hiên, quạt. Cái gì cần điện thoại hay cơ sở dữ liệu thì đặt trên server — thông báo, lịch sử, quản lý thẻ.',
    ],
    detail: ['Bảng phân vai lấy từ HUONG_DAN_ESP32.md, mục 2 "Cái nào chạy ở đâu".'],
    next: 'Các thành phần này giao tiếp với nhau qua MQTT.',
  },
  {
    title: 'Giao tiếp MQTT & luồng dữ liệu',
    time: '1:30',
    say: [
      'Bảng bên trái là các topic chính. Trạng thái và lệnh của entity đi qua tiền tố smarthome-doan do ESPHome tự sinh. Ngoài ra nhóm tự định nghĩa topic sự kiện, topic lệnh mở cửa và topic danh sách thẻ.',
      'Ví dụ một lần quẹt thẻ: ESP32 so UID với danh sách lưu trong flash; nếu đúng thì bíp, mở cửa và gửi sự kiện JSON với QoS 1. Node-RED nhận sự kiện và INSERT vào MariaDB; cùng lúc Home Assistant nhận sự kiện đó và một giây sau đọc lại MariaDB để trang Lịch sử cập nhật.',
      'Việc kiểm tra thẻ diễn ra hoàn toàn trên ESP32, nên không cần server vẫn mở được cửa.',
    ],
    detail: [
      'Sự kiện mang giờ SNTP của ESP32 (ts_device); Node-RED ghi thêm giờ nhận (ts_server). Trên 183 sự kiện có đủ hai mốc, chênh lệch ≤ 1 s — độ phân giải của DB là 1 giây nên chỉ kết luận được "dưới 1 giây".',
      '45/228 sự kiện không có giờ ESP32 vì mạch chưa kịp đồng bộ SNTP sau khi khởi động; khi đó dùng giờ server.',
      'Danh sách thẻ gửi dạng retained: ESP32 khởi động lại là nhận ngay bản mới nhất, và còn lưu vào flash.',
    ],
    next: 'Bây giờ em đi vào hai nhóm tính năng chính, bắt đầu với cửa chính.',
  },
  {
    title: 'Kiểm soát ra vào',
    time: '1:20',
    say: [
      'Có năm cách yêu cầu mở cửa: thẻ RFID, nút trên dashboard, nút trong thông báo điện thoại, script trên điện thoại và giọng nói.',
      'Servo của nhóm là loại quay liên tục 360 độ, không giữ được góc. Vì vậy cửa mở bằng cách quay trong một khoảng thời gian (700 ms, đo trên cửa thật), và đóng bằng cách quay ngược tới khi công tắc từ báo đã đóng.',
      'Nếu sau 1,5 giây cửa vẫn chưa đóng — ví dụ có vật cản — mạch mở lại, bíp dài rồi thử lại; sau 3 lần thì để cửa mở và báo "Cửa bị vướng".',
      'Quẹt sai thẻ thì bíp dài và báo lên điện thoại kèm nút Mở cửa; sai 3 lần liên tiếp thì còi kêu khoảng 4,5 giây.',
    ],
    detail: [
      'Cảm biến cửa báo đóng khi cửa còn hở khoảng 15–25° nên firmware quay thêm 100 ms cho khít.',
      'Mở cửa hợp lệ tự tắt chế độ vắng nhà.',
      'UID được kiểm tra định dạng ở cả HA và Node-RED; câu SQL dùng tham số nên tránh được SQL injection.',
    ],
    next: 'Nhóm tính năng thứ hai là báo động và tự động hóa.',
  },
  {
    title: 'An toàn & tự động hóa',
    time: '1:20',
    say: [
      'Bộ não báo động là một vòng lặp chạy mỗi 0,5 giây trên ESP32: có lửa, có gas hoặc có đột nhập thì còi kêu liên tục và đèn RGB nháy đỏ; riêng gas thì bật thêm quạt hút.',
      'Sự kiện đồng thời gửi lên HA để gửi thông báo điện thoại; thông báo dùng kênh báo động nên kêu cả khi máy để im lặng, và có nút Tắt báo động.',
      'Các tự động hóa khác: đèn hiên theo chuyển động khi trời tối, quạt hút theo độ ẩm. Mọi ngưỡng đều có vùng trễ để không bật tắt liên tục, và chỉnh được trên HA.',
      'Chế độ vắng nhà bật/tắt được khi test, nhưng phần báo đột nhập chưa kích được vì PIR giữ trạng thái có chuyển động suốt lúc test; em ghi rõ trên slide.',
    ],
    detail: [
      'Thứ tự ưu tiên của quạt: gas > tự động theo độ ẩm > bật tay.',
      'Tắt báo động: còi im ngay nhưng đèn vẫn nháy tới khi hết lửa hoặc gas; riêng đột nhập thì xóa hẳn.',
      'MQ-2 cần làm nóng: trong 60 giây đầu sau khi cấp điện, vòng báo động không bật còi/quạt vì gas; riêng entity “Báo khí gas bếp” vẫn có thể lên ON và HA vẫn gửi thông báo.',
    ],
    next: 'Người dùng tương tác với tất cả những chức năng này qua giao diện sau.',
  },
  {
    title: 'Giao diện',
    time: '1:15',
    say: [
      'Dashboard "Smarthome đồ án" có 5 trang: Tổng quan là mặt bằng 2D chạm để điều khiển; Điều khiển chia theo phòng kèm biểu đồ 24 giờ; Mô hình 3D; Lịch sử truy cập đọc từ MariaDB; và Quản lý thẻ.',
      'Trang Mô hình 3D là thẻ Lovelace nhóm tự viết bằng three.js: chạm vào thiết bị để bật tắt, giữ để xem chi tiết, trạng thái cập nhật theo entity thật.',
      '[Nếu có demo trực tiếp: bật đèn trên trang Điều khiển → quẹt thẻ → trang Lịch sử truy cập cập nhật.]',
    ],
    detail: [
      'Bốn ảnh là ảnh chụp thật dashboard đêm 21/10 khi mạch đang chạy; trang 3D tự chuyển sang chế độ đêm vì cảm biến ánh sáng báo trời tối. Số công suất khoảng 80 W trên ảnh là giá trị sai của ACS712, em nói ở phần hạn chế.',
      'Assist dùng pipeline "Google Assistant": nhận giọng nói bằng Gemini, ưu tiên câu lệnh cục bộ của HA.',
    ],
    next: 'Phần tiếp theo là kết quả kiểm thử.',
  },
  {
    title: 'Kết quả vận hành',
    time: '1:00',
    say: [
      'Các con số ở trên đều truy vấn trực tiếp từ MariaDB, giai đoạn 17 đến 20/10, sau khi nạp firmware mới và tắt mạch mô phỏng.',
      '37 lượt quẹt thẻ: 23 hợp lệ và 14 lần sai, trong đó 3 lần sai liên tiếp làm còi cảnh báo; 101 lần cửa mở; 4 lần báo cháy và 6 lần báo gas đều được ghi lại.',
      'Nhóm chia kết quả thành ba mức: đã đo đạt trên mạch, đã có ghi nhận hoạt động, và chưa kiểm thử. Những mục chưa kiểm thử em ghi rõ, không tính vào kết quả.',
    ],
    detail: [
      '“133 lệnh mở từ xa” (method = remote) gồm mọi lệnh mở không qua thẻ hay điện thoại: nút dashboard, thẻ 2D/3D, Assist, trang web ESP32.',
      '“Lockout” không khóa đầu đọc: firmware chỉ hú còi ≈ 4,5 s và ghi một dòng vào DB.',
      'Test phần cứng ghi trong chú thích firmware: RC522 chip clone 0x82, SPI ổn định tới 8 MHz nên chạy 4 MHz; cảm biến cửa 142 mV khi đóng và 3139 mV khi mở; servo đóng tới cảm biến mất 149–388 ms.',
      'KICH_BAN_TEST.md có 48 ca đơn và 5 kịch bản kết hợp; 13 ca điều khiển từ xa đã chạy lại ngày 21/10 (slide sau), các ca cần thao tác tay (lửa, gas, PIR, mất mạng) chưa ghi kết quả.',
      'Thẻ 3D có bộ test tự động; 14/14 unit test logic đạt khi chạy lại ngày 20/10.',
    ],
    next: 'Ngoài số liệu vận hành, nhóm chạy lại các ca test điều khiển từ xa trên mạch thật.',
  },
  {
    title: 'Kiểm thử trên mạch thật',
    time: '1:00',
    say: [
      'Đêm 21/10 nhóm chạy lại 13 ca test có thể điều khiển từ xa, bằng một script gọi dịch vụ Home Assistant rồi theo dõi trạng thái ESP32 báo về.',
      'Cả 13 ca đều đạt: relay và đèn RGB phản hồi trong khoảng 14–102 ms; cửa mở sau 0,29 s và tự đóng, cả chu trình 11 giây; lệnh giọng nói “mở cửa” và “tắt còi” chạy đúng; thêm thẻ trên trang Quản lý thì sau 1,6 s ESP32 đã nhận danh sách mới.',
      'Ca báo đột nhập chưa kích được vì PIR giữ trạng thái có chuyển động liên tục trong lúc test, nên em để ở mức chưa kiểm thử.',
    ],
    detail: [
      'Thời gian phản hồi = last_updated của trạng thái mới trong HA − thời điểm gửi lệnh, đo trên cùng đồng hồ máy chủ. “Đạt” nghĩa là ESP32 báo đúng trạng thái; đèn sáng hay quạt quay không đo được từ xa.',
      'Chu trình cửa 11,1 s = 10 s “Thời gian mở cửa” + thời gian quay đóng.',
      'Ca thêm thẻ đi qua cả chuỗi HA → MQTT → Node-RED → MariaDB → MQTT retained → ESP32; thẻ thử FE-ED-00-01 đã được xóa sau test.',
      'Ghi nhận thêm (thao tác tay của nhóm lúc 00:31): mở cửa khi đang vắng nhà thì chế độ vắng nhà tự tắt, đúng thiết kế (A12).',
      'Lần chạy đầu, R3 (đèn hiên) không đo được vì PIR vừa tự bật đèn hiên trước lệnh — đúng kịch bản đèn hiên tự động; chạy lại thì đạt.',
    ],
    next: 'Trong quá trình làm, nhóm gặp một số khó khăn và vẫn còn hạn chế.',
  },
  {
    title: 'Khó khăn & hạn chế',
    time: '1:10',
    say: [
      'Ví dụ khó khăn: servo ban đầu không quay. Nguyên nhân là ESP32 cấp kênh PWM theo cặp dùng chung timer, servo 50 Hz bị kênh của đèn RGB 1000 Hz ép tần số. Nhóm tách servo sang kênh 4 thì chạy.',
      'Một ví dụ khác: PIR luôn báo có người, do dùng chung dây 5 V với relay và servo; đi dây nguồn riêng thì hết.',
      'Hạn chế lớn nhất em muốn nói thẳng: thông báo "ESP32 mất kết nối" chưa từng gửi được, vì automation chờ trạng thái off trong khi thực tế entity chuyển sang unavailable. Ngoài ra MQTT chưa mã hóa và thẻ RFID chỉ so UID.',
    ],
    detail: [
      'Lịch sử HA: binary_sensor.smarthome_ket_noi có 33 lần unavailable, 0 lần off; automation "ESP32 mất kết nối" chưa chạy lần nào.',
      'ACS712-20A chỉ có 100 mV/A, nhiễu ADC ±10–20 mV nên sai số ±0,1–0,2 A; lịch sử từng ghi giá trị vô lý (24,5 A) khi mất nguồn 5 V, nên nhóm không dùng số điện năng làm kết quả.',
    ],
    next: 'Cuối cùng là kết luận.',
  },
  {
    title: 'Kết luận & hỏi đáp',
    time: '0:30',
    say: [
      'Tóm lại, nhóm đã có một hệ thống chạy trên mạch thật, kịch bản an toàn chạy cục bộ, và phần server lưu lịch sử, hiển thị, thông báo.',
      'Hướng phát triển là các đề xuất, chưa thực hiện: bật TLS cho MQTT, sửa cảnh báo offline, xác thực thẻ mạnh hơn, và chạy đủ bộ kịch bản test.',
      'Em xin cảm ơn thầy/cô đã lắng nghe, nhóm sẵn sàng trả lời câu hỏi.',
    ],
    detail: [],
    next: '',
  },
];
