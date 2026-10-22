// Tạo SmartHome_Project_Report.pptx (BẢN NHÁP) và SmartHome_Presentation_Notes.md vào /config/SmartHome_BaoCao.
// Chạy:  cd /config/bao_cao/_build && NODE_PATH=./node_modules node build.js
// Cần:   pptxgenjs + @mdi/js (node_modules ở đây), rsvg-convert (vẽ icon MDI ra PNG).
// Nội dung lấy từ SmartHome_Evidence_Map.md; ghi chú thuyết trình ở notes.js.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const pptxgen = require('pptxgenjs');
const mdi = require('@mdi/js');
const { applyTheme } = require('./apply_theme.js');
const NOTES = require('./notes.js');

const OUT = path.resolve(__dirname, '..', '..', 'SmartHome_BaoCao'); // /config/SmartHome_BaoCao
const ASSET = (f) => path.join(__dirname, 'assets', f);
const DECK = path.join(OUT, 'SmartHome_Project_Report.pptx');
const FOOTER = 'Đồ án Smarthome · ESP32 + MQTT + Home Assistant';
const DRAFT = false; // bản cuối: đặt false để bỏ nhãn "BẢN NHÁP"

const THEME = {
  name: 'Smarthome Navy Teal',
  headFontFace: 'Calibri',
  bodyFontFace: 'Calibri',
  colors: {
    dk1: '0F1B2D', lt1: 'FFFFFF', dk2: '0B2545', lt2: 'EEF3F8',
    accent1: '0D9488', accent2: '22D3EE', accent3: 'B45309', accent4: 'DC2626',
    accent5: '5B6B80', accent6: '15803D', hlink: '0D9488', folHlink: '5B6B80',
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13,333 × 7,5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'Mô hình nhà thông minh với ESP32, MQTT và Home Assistant';
pres.subject = 'Báo cáo đồ án Smarthome (bản nháp)';
const C = pres.SchemeColor;
const S = pres.shapes;

// ---------- Icon MDI (cùng bộ icon với dashboard HA) → PNG ----------
const iconCache = {};
function icon(name, hex) {
  if (!mdi[name]) throw new Error('Không có icon ' + name);
  const k = name + hex;
  if (!iconCache[k]) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256"><path fill="#${hex}" d="${mdi[name]}"/></svg>`;
    iconCache[k] = 'image/png;base64,' + execFileSync('rsvg-convert', ['-w', '256', '-h', '256'], { input: svg }).toString('base64');
  }
  return iconCache[k];
}

// ---------- Tiện ích vẽ ----------
const T = (slide, text, o) => slide.addText(text, { isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: 'top', ...o });
const shadow = () => ({ type: 'outer', blur: 8, offset: 2, angle: 90, color: '0F1B2D', opacity: 0.12 });

function kicker(slide, text, dark) {
  T(slide, text, { x: 0.6, y: 0.3, w: 10.5, h: 0.3, fontSize: 13, bold: true, charSpacing: 1.5, color: dark ? C.accent2 : C.accent1, objectName: 'Nhãn mục' });
}
function box(slide, o) {
  slide.addShape(S.ROUNDED_RECTANGLE, {
    x: o.x, y: o.y, w: o.w, h: o.h, rectRadius: o.r ?? 0.08,
    fill: o.fill ?? { color: C.background1 },
    line: o.line ?? { type: 'none' },
    shadow: o.shadow ? shadow() : undefined,
    objectName: o.name,
  });
}
function iconDot(slide, name, x, y, d, bg, fgHex, o = {}) {
  slide.addShape(S.OVAL, { x, y, w: d, h: d, fill: { color: bg, transparency: o.tint ?? 0 }, line: { type: 'none' }, objectName: o.name });
  const p = d * (o.pad ?? 0.22);
  slide.addImage({ data: icon(name, fgHex), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, altText: o.alt ?? name });
}
// Mũi tên thẳng (x1,y1) → (x2,y2); both = hai đầu
function arrow(slide, x1, y1, x2, y2, o = {}) {
  slide.addShape(S.LINE, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1,
    line: {
      color: o.color ?? C.accent5, width: o.width ?? 1.5, dashType: o.dash,
      endArrowType: o.end === false ? undefined : 'triangle', beginArrowType: o.both ? 'triangle' : undefined,
    },
  });
}
function label(slide, text, x, y, w, o = {}) {
  T(slide, text, { x, y, w, h: o.h ?? 0.28, fontSize: o.size ?? 11, color: o.color ?? C.accent5, align: o.align ?? 'center', italic: o.italic, bold: o.bold, valign: o.valign ?? 'bottom', fontFace: o.font });
}
function bullets(items, o = {}) {
  return items.map((t, i) => ({
    text: t,
    options: { bullet: { indent: 16 }, breakLine: i < items.length - 1, paraSpaceAfter: o.space ?? 6 },
  }));
}

// ---------- Bố cục (slide layout) ----------
const draftPill = (dark) => ({
  text: {
    text: 'BẢN NHÁP',
    options: {
      x: 11.48, y: 0.28, w: 1.25, h: 0.32, fontSize: 11, bold: true, align: 'center', valign: 'middle', margin: 0,
      color: dark ? 'FCD34D' : C.accent3, fill: { color: dark ? C.text2 : 'FFFBEB' },
      line: { color: dark ? 'FCD34D' : C.accent3, width: 1 }, shape: S.ROUNDED_RECTANGLE, rectRadius: 0.08,
    },
  },
});
const footer = (dark) => ({ text: { text: FOOTER, options: { x: 0.6, y: 7.02, w: 7, h: 0.28, fontSize: 11, margin: 0, color: dark ? C.background2 : C.accent5 } } });
const slideNum = (dark) => ({ x: 12.13, y: 7.02, w: 0.6, h: 0.28, fontSize: 11, align: 'right', margin: 0, color: dark ? 'CBD5E1' : '5B6B80' });

pres.defineSlideMaster({
  title: 'TIEU_DE',
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', align: 'left', x: 0.7, y: 1.7, w: 6.75, h: 2.1, fontSize: 38, bold: true, color: C.background1, valign: 'top', margin: 0 }, text: '' } },
    ...(DRAFT ? [draftPill(true)] : []),
  ],
});
pres.defineSlideMaster({
  title: 'NOI_DUNG',
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', align: 'left', x: 0.6, y: 0.6, w: 12.13, h: 0.7, fontSize: 30, bold: true, color: C.text2, valign: 'top', margin: 0 }, text: '' } },
    footer(false),
    ...(DRAFT ? [draftPill(false)] : []),
  ],
  slideNumber: slideNum(false),
});
pres.defineSlideMaster({
  title: 'KET_LUAN',
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', align: 'left', x: 0.6, y: 0.6, w: 12.13, h: 0.7, fontSize: 30, bold: true, color: C.background1, valign: 'top', margin: 0 }, text: '' } },
    footer(true),
    ...(DRAFT ? [draftPill(true)] : []),
  ],
  slideNumber: slideNum(true),
});

let slideNo = 0;
function newSlide(master, section) {
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  const n = NOTES[slideNo++];
  const parts = [`[${n.title} · khoảng ${n.time}]`, '', ...n.say];
  if (n.detail.length) parts.push('', 'Chi tiết (không có trên slide):', ...n.detail.map((d) => '• ' + d));
  if (n.next) parts.push('', 'Chuyển ý: ' + n.next);
  s.addNotes(parts.join('\n'));
  return s;
}

// =====================================================================
// S1 · Tiêu đề
// =====================================================================
pres.addSection({ title: 'Mở đầu' });
{
  const s = newSlide('TIEU_DE', 'Mở đầu');
  T(s, 'ĐỒ ÁN MÔN HỌC · ……………………………………', { x: 0.7, y: 1.2, w: 6.75, h: 0.35, fontSize: 14, bold: true, charSpacing: 1.5, color: C.accent2 });
  s.addText('Mô hình nhà thông minh với ESP32, MQTT và Home Assistant', { placeholder: 'title' });
  T(s, 'Kịch bản an toàn chạy ngay trên mạch ESP32 · giám sát, lưu trữ và thông báo trên Home Assistant', { x: 0.7, y: 3.9, w: 6.6, h: 0.8, fontSize: 17, color: C.background2 });
  // Chỗ trống để nhóm tự điền (3 thành viên)
  const dots = '……………………………………………';
  T(s, [
    { text: 'Nhóm thực hiện', options: { bold: true, color: C.accent2, breakLine: true } },
    ...[1, 2, 3].map((i) => ({ text: `${i}. Họ tên: ${dots}   MSSV: ………………………`, options: { breakLine: true } })),
    { text: 'GVHD: ', options: { bold: true } }, { text: dots + '……………', options: { breakLine: true } },
    { text: 'Khoa – Trường: ', options: { bold: true } }, { text: '…………………………………   Ngày: ……/……/2026' },
  ], { x: 0.7, y: 4.8, w: 6.75, h: 2.25, fontSize: 14, color: C.background2, paraSpaceAfter: 3 });
  box(s, { x: 7.85, y: 1.3, w: 4.95, h: 3.81, r: 0.1, fill: { color: C.text1 }, line: { color: '3B5578', width: 1 }, name: 'Khung ảnh 3D' });
  s.addImage({ path: ASSET('live_3d_title.png'), x: 8.0, y: 1.45, w: 4.65, h: 3.508, altText: 'Ảnh chụp thật trang Mô hình 3D trên dashboard, 21/10/2026' });
  T(s, 'Trang “Mô hình 3D” trên dashboard — ảnh chụp thật 21/10/2026', { x: 7.85, y: 5.25, w: 4.95, h: 0.3, fontSize: 11, color: C.background2, align: 'center' });
}

// =====================================================================
// S2 · Bài toán & mục tiêu
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Mở đầu');
  kicker(s, '01 · BÀI TOÁN & MỤC TIÊU');
  s.addText('Nhà thông minh phải giữ an toàn kể cả khi mất mạng', { placeholder: 'title' });
  T(s, 'Vấn đề cần giải quyết', { x: 0.6, y: 1.6, w: 6, h: 0.4, fontSize: 18, bold: true, color: C.text2 });
  const probs = [
    ['mdiFire', 'Cháy và rò khí gas', 'Phải báo động tại chỗ ngay, không phụ thuộc Wi-Fi hay server'],
    ['mdiDoorClosedLock', 'Kiểm soát ra vào', 'Biết ai mở cửa, lúc nào; phản ứng khi có người quẹt sai thẻ'],
    ['mdiCellphoneLink', 'Giám sát và điều khiển từ xa', 'Xem trạng thái, nhận cảnh báo, mở cửa qua điện thoại'],
  ];
  probs.forEach(([ic, t, d], i) => {
    const y = 2.2 + i * 1.45;
    iconDot(s, ic, 0.6, y, 0.8, C.accent1, 'FFFFFF');
    T(s, t, { x: 1.65, y: y + 0.02, w: 4.9, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
    T(s, d, { x: 1.65, y: y + 0.45, w: 4.9, h: 0.75, fontSize: 15, color: C.accent5 });
  });
  box(s, { x: 7.0, y: 1.6, w: 5.73, h: 5.05, fill: { color: C.background2 }, name: 'Thẻ mục tiêu' });
  T(s, 'Mục tiêu & phạm vi đã làm', { x: 7.35, y: 1.85, w: 5.1, h: 0.4, fontSize: 18, bold: true, color: C.text2 });
  T(s, bullets([
    'Mô hình 3 phòng (khách, bếp, ngủ) và cửa chính, hiên trước nhà',
    '1 ESP32 · 8 cảm biến · 4 relay, servo cửa, còi, LED RGB',
    'Kịch bản an toàn chạy cục bộ trên ESP32',
    'Home Assistant: dashboard, thông báo điện thoại, giọng nói',
    'Node-RED + MariaDB: lịch sử ra vào, quản lý thẻ RFID',
  ], { space: 14 }), { x: 7.35, y: 2.45, w: 5.1, h: 3.5, fontSize: 16, color: C.text1 });
  T(s, 'Đèn và quạt trong mô hình chạy bus 5 V', { x: 7.35, y: 6.1, w: 5.1, h: 0.3, fontSize: 12, italic: true, color: C.accent5 });
}

// =====================================================================
// S3 · Kiến trúc hệ thống
// =====================================================================
pres.addSection({ title: 'Thiết kế hệ thống' });
{
  const s = newSlide('NOI_DUNG', 'Thiết kế hệ thống');
  kicker(s, '02 · KIẾN TRÚC');
  s.addText('Logic an toàn trên ESP32, server lo giao diện và lưu trữ', { placeholder: 'title' });

  // Khung máy chủ
  box(s, { x: 2.85, y: 1.5, w: 9.88, h: 3.4, fill: { color: C.background2 }, name: 'Khung máy chủ' });
  label(s, 'Máy chủ: Home Assistant OS 18.3 · máy ảo x86-64', 8.4, 4.55, 4.15, { align: 'right', size: 12, bold: true });

  // Người dùng
  label(s, 'NGƯỜI DÙNG', 0.6, 1.5, 1.95, { align: 'left', size: 11, bold: true, color: C.accent1 });
  const users = [['mdiMonitorDashboard', 'Dashboard', 'web · app'], ['mdiCellphoneMessage', 'Thông báo', 'điện thoại'], ['mdiMicrophone', 'Giọng nói', 'Assist']];
  users.forEach(([ic, t, d], i) => {
    const y = 1.85 + i * 0.95;
    box(s, { x: 0.6, y, w: 1.95, h: 0.75, line: { color: 'CBD5E1', width: 1 } });
    s.addImage({ data: icon(ic, HEX.accent1), x: 0.72, y: y + 0.17, w: 0.4, h: 0.4 });
    T(s, [{ text: t, options: { bold: true, breakLine: true } }, { text: d }], { x: 1.22, y: y + 0.1, w: 1.3, h: 0.6, fontSize: 13, color: C.text2 });
    arrow(s, 2.55, y + 0.375, 3.1, y + 0.375, { both: true });
  });

  // Các thành phần máy chủ
  const comp = (x, y, w, h, ic, t, d) => {
    box(s, { x, y, w, h, line: { color: C.accent1, width: 1.25 }, shadow: true });
    s.addImage({ data: icon(ic, HEX.accent1), x: x + (w - 0.5) / 2, y: y + 0.15, w: 0.5, h: 0.5 });
    T(s, t, { x: x + 0.08, y: y + 0.7, w: w - 0.16, h: 0.35, fontSize: 15, bold: true, align: 'center', color: C.text2 });
    T(s, d, { x: x + 0.1, y: y + 1.05, w: w - 0.2, h: h - 1.1, fontSize: 12, align: 'center', color: C.accent5 });
  };
  comp(3.1, 1.85, 2.0, 2.6, 'mdiHomeAssistant', 'Home Assistant', 'Dashboard 5 trang\n10 automation\n6 cảm biến SQL');
  comp(5.75, 2.65, 1.95, 1.45, 'mdiTransitConnectionVariant', 'Mosquitto', 'MQTT broker');
  comp(8.3, 2.65, 1.95, 1.45, 'mdiSitemap', 'Node-RED', 'ghi sự kiện, gửi thẻ');
  comp(10.75, 2.65, 1.85, 1.45, 'mdiDatabase', 'MariaDB', 'thẻ, lịch sử, sự kiện');
  arrow(s, 5.1, 3.375, 5.75, 3.375, { both: true }); label(s, 'MQTT', 5.1, 3.05, 0.65);
  arrow(s, 7.7, 3.375, 8.3, 3.375, { both: true }); label(s, 'MQTT', 7.7, 3.05, 0.6);
  arrow(s, 10.25, 3.375, 10.75, 3.375); label(s, 'ghi', 10.25, 3.05, 0.5);
  // MariaDB → HA (đọc SQL)
  arrow(s, 11.675, 2.65, 11.675, 2.1, { end: false });
  arrow(s, 11.675, 2.1, 5.1, 2.1);
  label(s, 'đọc SQL (tài khoản chỉ đọc ha_ro): lịch sử, danh sách thẻ, thống kê', 5.3, 1.78, 6.2);

  // ESP32 và ngoại vi
  arrow(s, 6.725, 4.1, 6.725, 5.3, { both: true });
  label(s, 'MQTT qua Wi-Fi\n(user/password)', 6.85, 4.95, 1.9, { align: 'left', valign: 'top', h: 0.45 });
  box(s, { x: 4.9, y: 5.3, w: 3.65, h: 1.35, fill: { color: C.text2 }, shadow: true, name: 'ESP32' });
  s.addImage({ data: icon('mdiChip', HEX.accent2), x: 5.05, y: 5.6, w: 0.7, h: 0.7 });
  T(s, [{ text: 'ESP32 DevKit V1', options: { bold: true, breakLine: true } }, { text: 'firmware ESPHome', options: { fontSize: 13, breakLine: true } }, { text: 'kịch bản an toàn chạy tại chỗ', options: { fontSize: 13, color: C.accent2 } }],
    { x: 5.9, y: 5.45, w: 2.6, h: 1.1, fontSize: 16, color: C.background1 });
  box(s, { x: 1.35, y: 5.55, w: 3.0, h: 0.85, line: { color: 'CBD5E1', width: 1 } });
  T(s, [{ text: '8 cảm biến', options: { bold: true, breakLine: true } }, { text: 'RFID · cửa · PIR · ánh sáng · DHT11 · lửa · gas · dòng', options: { fontSize: 11, color: C.accent5 } }], { x: 1.5, y: 5.62, w: 2.75, h: 0.75, fontSize: 14, color: C.text2 });
  arrow(s, 4.35, 5.975, 4.9, 5.975);
  box(s, { x: 9.1, y: 5.55, w: 3.0, h: 0.85, line: { color: 'CBD5E1', width: 1 } });
  T(s, [{ text: 'Cơ cấu chấp hành', options: { bold: true, breakLine: true } }, { text: '4 relay · servo cửa · còi · LED RGB', options: { fontSize: 11, color: C.accent5 } }], { x: 9.25, y: 5.62, w: 2.75, h: 0.75, fontSize: 14, color: C.text2 });
  arrow(s, 8.55, 5.975, 9.1, 5.975);
}

// =====================================================================
// S4 · Phần cứng
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Thiết kế hệ thống');
  kicker(s, '03 · PHẦN CỨNG');
  s.addText('Một ESP32 đọc 8 cảm biến và điều khiển toàn bộ mô hình', { placeholder: 'title' });
  const row = (x, y, w, ic, name, detail, pin) => {
    box(s, { x, y, w, h: 0.5, fill: { color: C.background2 } });
    iconDot(s, ic, x + 0.08, y + 0.06, 0.38, C.accent1, 'FFFFFF', { pad: 0.2 });
    T(s, [{ text: name, options: { bold: true } }, { text: '  ' + detail, options: { color: C.accent5, fontSize: 12 } }], { x: x + 0.58, y: y + 0.1, w: w - 1.75, h: 0.32, fontSize: 14, color: C.text2, valign: 'middle' });
    T(s, pin, { x: x + w - 1.15, y: y + 0.1, w: 1.05, h: 0.32, fontSize: 12, bold: true, align: 'right', color: C.accent1, valign: 'middle' });
  };
  T(s, 'NGÕ VÀO · 8 CẢM BIẾN', { x: 0.6, y: 1.55, w: 4.9, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const ins = [
    ['mdiCardAccountDetails', 'RFID RC522', 'SPI 4 MHz', '25·26·33·27'],
    ['mdiDoorOpen', 'Công tắc từ cửa', 'đóng/mở', 'IO34'],
    ['mdiMotionSensor', 'PIR HC-SR501', 'chuyển động', 'IO35'],
    ['mdiBrightness6', 'Quang trở', 'ánh sáng, ADC', 'IO32'],
    ['mdiThermometerWater', 'DHT11', 'nhiệt độ, độ ẩm', 'IO19'],
    ['mdiFire', 'Cảm biến lửa', 'ngõ số', 'IO18'],
    ['mdiMolecule', 'MQ-2', 'khí gas, ADC1', 'IO39'],
    ['mdiCurrentDc', 'ACS712-20A', 'dòng tổng 5 V', 'IO36'],
  ];
  ins.forEach((r, i) => row(0.6, 1.95 + i * 0.56, 4.95, ...r));

  // ESP32 ở giữa
  box(s, { x: 5.95, y: 2.35, w: 1.85, h: 3.5, fill: { color: C.text2 }, shadow: true, name: 'ESP32' });
  s.addImage({ data: icon('mdiChip', HEX.accent2), x: 6.425, y: 2.65, w: 0.9, h: 0.9 });
  T(s, 'ESP32\nDevKit V1', { x: 6.0, y: 3.65, w: 1.75, h: 0.8, fontSize: 18, bold: true, align: 'center', color: C.background1 });
  T(s, '30 chân · Wi-Fi\nESPHome', { x: 6.0, y: 4.55, w: 1.75, h: 0.7, fontSize: 12, align: 'center', color: C.accent2 });
  arrow(s, 5.6, 4.1, 5.95, 4.1, { width: 2 });
  arrow(s, 7.8, 4.1, 8.15, 4.1, { width: 2 });

  T(s, 'NGÕ RA · CƠ CẤU CHẤP HÀNH', { x: 8.2, y: 1.55, w: 4.53, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  box(s, { x: 8.2, y: 1.95, w: 4.53, h: 2.15, fill: { color: C.background2 }, name: 'Relay' });
  iconDot(s, 'mdiElectricSwitch', 8.28, 2.01, 0.38, C.accent1, 'FFFFFF', { pad: 0.2 });
  T(s, [{ text: 'Relay 4 kênh', options: { bold: true } }, { text: '  kích mức thấp', options: { color: C.accent5, fontSize: 12 } }], { x: 8.78, y: 2.05, w: 3.8, h: 0.32, fontSize: 14, color: C.text2, valign: 'middle' });
  const relays = [['IO5', 'Đèn hiên'], ['IO17', 'Đèn phòng khách'], ['IO16', 'Đèn phòng ngủ'], ['IO4', 'Quạt hút phòng ngủ']];
  relays.forEach(([p, n], i) => {
    T(s, p, { x: 8.78, y: 2.5 + i * 0.38, w: 0.65, h: 0.32, fontSize: 12, bold: true, color: C.accent1, valign: 'middle' });
    T(s, n, { x: 9.45, y: 2.5 + i * 0.38, w: 3.1, h: 0.32, fontSize: 14, color: C.text2, valign: 'middle' });
  });
  const outs = [
    ['mdiRotateLeft', 'Servo 360° cửa', 'PWM 50 Hz', 'IO12'],
    ['mdiBullhorn', 'Còi', 'kích mức thấp', 'IO13'],
    ['mdiLedStripVariant', 'LED RGB ×2', 'PWM', '23·22·21'],
  ];
  outs.forEach((r, i) => row(8.2, 4.23 + i * 0.56, 4.53, ...r));
  T(s, 'ACS712 nối qua cầu chia áp 1k/2k · tải đèn, quạt chạy bus 5 V · nguồn cấp, loại module: [cần bổ sung]', { x: 0.6, y: 6.55, w: 12.13, h: 0.3, fontSize: 11, color: C.accent5 });
}

// =====================================================================
// S5 · Phần mềm & phân vai
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Thiết kế hệ thống');
  kicker(s, '04 · PHẦN MỀM');
  s.addText('Cần chạy khi mất mạng thì đặt trên ESP32, còn lại trên server', { placeholder: 'title' });
  T(s, 'CÔNG NGHỆ SỬ DỤNG', { x: 0.6, y: 1.55, w: 5.5, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const stack = [
    ['mdiChip', 'ESPHome', '2026.9', 'Firmware ESP32: YAML + lambda C++'],
    ['mdiTransitConnectionVariant', 'Mosquitto', '7.1.1', 'MQTT broker'],
    ['mdiHomeAssistant', 'Home Assistant', '2026.10.2', 'Dashboard, automation, thông báo, giọng nói'],
    ['mdiSitemap', 'Node-RED', '22.1.0', 'Ghi sự kiện vào DB, đồng bộ thẻ'],
    ['mdiDatabase', 'MariaDB', 'add-on 3.0.1', 'Bảng cards, access_log, events'],
    ['mdiCubeOutline', 'three.js', 'r170', 'Thẻ "Mô hình 3D" tự viết'],
  ];
  stack.forEach(([ic, n, v, d], i) => {
    const y = 1.95 + i * 0.77;
    iconDot(s, ic, 0.6, y + 0.06, 0.52, C.accent1, 'FFFFFF', { pad: 0.2 });
    T(s, [{ text: n, options: { bold: true } }, { text: '  ' + v, options: { color: C.accent1, fontSize: 12, bold: true } }], { x: 1.3, y: y + 0.02, w: 4.7, h: 0.32, fontSize: 15, color: C.text2 });
    T(s, d, { x: 1.3, y: y + 0.36, w: 4.7, h: 0.3, fontSize: 13, color: C.accent5 });
  });

  T(s, 'CHỨC NĂNG CHẠY Ở ĐÂU?', { x: 6.55, y: 1.55, w: 6.18, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const H = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });
  const where = (t, esp) => ({ text: t, options: { bold: true, color: esp ? C.accent1 : C.text2 } });
  const rows = [
    [H('Chức năng'), H('Chạy trên'), H('Lý do')],
    ['Cửa RFID, servo, chống kẹt', where('ESP32', 1), 'Mở được cả khi mất mạng'],
    ['Báo cháy/gas: còi, nháy đỏ, quạt hút', where('ESP32', 1), 'Không phụ thuộc Wi-Fi, HA'],
    ['Đèn hiên, quạt theo độ ẩm', where('ESP32', 1), 'Cảm biến cùng mạch, phản hồi nhanh'],
    ['Thông báo điện thoại', where('HA'), 'Chỉ HA có app điện thoại'],
    ['Lịch sử, biểu đồ', where('HA + MariaDB'), 'Cần cơ sở dữ liệu'],
    ['Quản lý thẻ RFID', where('HA + Node-RED'), 'Có giao diện thêm, khóa thẻ'],
  ];
  s.addTable(rows, {
    x: 6.55, y: 1.95, w: 6.18, colW: [2.55, 1.5, 2.13], fontSize: 13, color: C.text1, valign: 'middle',
    border: { type: 'solid', pt: 0.75, color: 'CBD5E1' }, rowH: 0.6, margin: [0.06, 0.1, 0.06, 0.1],
  });
}

// =====================================================================
// S6 · Giao tiếp MQTT & luồng dữ liệu
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Thiết kế hệ thống');
  kicker(s, '05 · GIAO TIẾP');
  s.addText('MQTT nối mọi thành phần — ví dụ một lần quẹt thẻ', { placeholder: 'title' });
  T(s, 'TOPIC MQTT CHÍNH', { x: 0.6, y: 1.55, w: 5.3, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const tp = (t) => ({ text: t, options: { fontFace: 'Courier New', fontSize: 12, bold: true, color: C.text2 } });
  const ds = (dir, t) => ({ text: [{ text: dir, options: { bold: true, color: C.accent1, breakLine: true } }, { text: t }] });
  s.addTable([
    [tp('smarthome-doan/…'), ds('ESP32 ↔ HA', 'trạng thái, lệnh (MQTT discovery)')],
    [tp('smarthome/event/access\nsmarthome/event/door\nsmarthome/event/alarm'), ds('ESP32 → Node-RED, HA', 'sự kiện JSON, QoS 1, kèm giờ SNTP')],
    [tp('smarthome/cmd/door'), ds('HA → ESP32', 'mở cửa từ điện thoại')],
    [tp('smarthome/cmd/cards'), ds('HA → Node-RED', 'thêm, khóa, xóa thẻ')],
    [tp('smarthome/config/cards'), ds('Node-RED → ESP32', 'danh sách UID, retained')],
  ], {
    x: 0.6, y: 1.95, w: 5.3, colW: [2.75, 2.55], fontSize: 13, color: C.text1, valign: 'middle',
    border: { type: 'solid', pt: 0.75, color: 'CBD5E1' }, margin: [0.06, 0.1, 0.06, 0.1],
  });

  // Sơ đồ tuần tự
  T(s, 'VÍ DỤ: QUẸT THẺ HỢP LỆ', { x: 6.3, y: 1.55, w: 6.43, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const L = [6.95, 8.65, 10.35, 12.0];
  const heads = ['Người dùng', 'ESP32', 'Node-RED\n+ MariaDB', 'Home Assistant'];
  heads.forEach((h, i) => {
    box(s, { x: L[i] - 0.7, y: 1.95, w: 1.4, h: 0.6, fill: { color: i === 1 ? C.text2 : C.background2 } });
    T(s, h, { x: L[i] - 0.7, y: 1.95, w: 1.4, h: 0.6, fontSize: 12, bold: true, align: 'center', valign: 'middle', color: i === 1 ? C.background1 : C.text2 });
    s.addShape(S.LINE, { x: L[i], y: 2.55, w: 0, h: 3.75, line: { color: 'A3B1C2', width: 1, dashType: 'dash' } });
  });
  const msg = (a, b, y, t, o = {}) => {
    arrow(s, L[a], y, L[b], y, { color: o.color ?? C.text2, width: 1.5 });
    const x0 = Math.min(L[a], L[b]), w = Math.abs(L[b] - L[a]);
    label(s, t, x0 + (o.dx ?? 0), y - 0.3, o.w ?? w, { color: C.text1, size: 12 });
  };
  const note = (i, y, t, w = 1.55) => {
    box(s, { x: L[i] - w / 2, y, w, h: 0.5, line: { color: C.accent1, width: 1 } });
    T(s, t, { x: L[i] - w / 2, y, w, h: 0.5, fontSize: 11, align: 'center', valign: 'middle', color: C.text2 });
  };
  msg(0, 1, 2.95, 'quẹt thẻ');
  note(1, 3.1, 'so UID trong flash\n→ bíp, servo mở');
  msg(1, 2, 3.95, 'event/access · QoS 1');
  note(2, 4.1, 'INSERT access_log');
  msg(1, 3, 4.95, 'cùng sự kiện', { dx: 1.7, w: 1.65 });
  note(3, 5.1, 'đọc lại SQL sau 1 s', 1.4);
  msg(3, 0, 5.95, 'trang Lịch sử truy cập cập nhật', { color: C.accent1 });
  T(s, 'Sai thẻ: HA gửi thông báo kèm nút “Mở cửa” → smarthome/cmd/door → ESP32 mở cửa', { x: 6.3, y: 6.4, w: 6.43, h: 0.3, fontSize: 12, color: C.accent5 });

  box(s, { x: 0.6, y: 5.75, w: 5.3, h: 0.95, fill: { color: C.accent1, transparency: 88 } });
  iconDot(s, 'mdiTimerSand', 0.75, 5.93, 0.6, C.accent1, 'FFFFFF', { pad: 0.2 });
  T(s, [{ text: 'Đo được: ', options: { bold: true } }, { text: 'giờ ESP32 và giờ ghi vào MariaDB lệch ≤ 1 s trên 183 sự kiện (DB lưu theo giây)' }], { x: 1.5, y: 5.85, w: 4.3, h: 0.78, fontSize: 13, color: C.text2, valign: 'middle' });
}

// =====================================================================
// S7 · Kiểm soát ra vào
// =====================================================================
pres.addSection({ title: 'Triển khai' });
{
  const s = newSlide('NOI_DUNG', 'Triển khai');
  kicker(s, '06 · TÍNH NĂNG 1 — CỬA CHÍNH');
  s.addText('Cửa chính: thẻ RFID, servo 360° và chống kẹt', { placeholder: 'title' });
  T(s, 'CHU TRÌNH MỞ – ĐÓNG CỬA', { x: 0.6, y: 1.55, w: 6.2, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const steps = [
    ['Yêu cầu mở', 'Thẻ RFID · nút dashboard · nút trong thông báo · script điện thoại · giọng nói'],
    ['Mở', 'Bíp ngắn, servo quay 700 ms (chỉ khi cửa đang đóng); tự tắt chế độ vắng nhà'],
    ['Giữ mở', 'Chờ “Thời gian mở cửa” (chỉnh trên HA); bấm Đóng cửa để đóng sớm'],
    ['Đóng', 'Quay ngược tới khi công tắc từ báo đóng (tối đa 1,5 s), quay thêm 100 ms cho khít'],
    ['Chống kẹt', 'Chưa đóng được: mở lại, bíp dài, thử lại; sau 3 lần báo “Cửa bị vướng”'],
  ];
  s.addShape(S.LINE, { x: 0.85, y: 2.2, w: 0, h: 3.6, line: { color: C.accent1, width: 2 } });
  steps.forEach(([t, d], i) => {
    const y = 1.98 + i * 0.9;
    s.addShape(S.OVAL, { x: 0.6, y, w: 0.5, h: 0.5, fill: { color: i === 4 ? C.accent3 : C.accent1 }, line: { color: C.background1, width: 2 } });
    T(s, String(i + 1), { x: 0.6, y, w: 0.5, h: 0.5, fontSize: 16, bold: true, align: 'center', valign: 'middle', color: C.background1 });
    T(s, t, { x: 1.3, y: y - 0.02, w: 5.75, h: 0.32, fontSize: 15, bold: true, color: C.text2 });
    T(s, d, { x: 1.3, y: y + 0.3, w: 5.75, h: 0.55, fontSize: 13, color: C.accent5 });
  });

  box(s, { x: 7.3, y: 1.55, w: 5.43, h: 1.95, fill: { color: C.background2 }, name: 'Sai thẻ' });
  iconDot(s, 'mdiCardRemove', 7.5, 1.75, 0.6, C.accent4, 'FFFFFF', { pad: 0.2 });
  T(s, 'Khi quẹt sai thẻ', { x: 8.25, y: 1.82, w: 4.3, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  T(s, bullets([
    'Bíp dài 1,5 s, điện thoại nhận thông báo có nút “Mở cửa”',
    'Sai 3 lần liên tiếp: còi kêu ≈ 4,5 s, ghi “lockout” vào DB',
  ]), { x: 7.55, y: 2.45, w: 5.0, h: 1.0, fontSize: 14, color: C.text1 });

  box(s, { x: 7.3, y: 3.7, w: 5.43, h: 2.95, fill: { color: C.background2 }, name: 'Quản lý thẻ' });
  iconDot(s, 'mdiCardAccountDetails', 7.5, 3.9, 0.6, C.accent1, 'FFFFFF', { pad: 0.2 });
  T(s, 'Quản lý thẻ', { x: 8.25, y: 3.97, w: 4.3, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  const chips = ['Trang\nQuản lý', 'Node-RED', 'MariaDB', 'Flash\nESP32'];
  chips.forEach((t, i) => {
    const x = 7.5 + i * 1.29;
    box(s, { x, y: 4.7, w: 1.0, h: 0.62, line: { color: C.accent1, width: 1 } });
    T(s, t, { x, y: 4.7, w: 1.0, h: 0.62, fontSize: 12, bold: true, align: 'center', valign: 'middle', color: C.text2 });
    if (i < 3) arrow(s, x + 1.0, 5.01, x + 1.29, 5.01, { color: C.accent1 });
  });
  T(s, 'Danh sách UID gửi xuống bằng MQTT retained (khi khởi động, mỗi giờ, mỗi lần sửa) và lưu vào flash → mất mạng vẫn mở được bằng thẻ đã lưu', { x: 7.55, y: 5.5, w: 5.0, h: 1.05, fontSize: 13, color: C.accent5 });
}

// =====================================================================
// S8 · An toàn & tự động hóa
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Triển khai');
  kicker(s, '07 · TÍNH NĂNG 2 — AN TOÀN');
  s.addText('Báo động và tự động hóa chạy ngay trên mạch', { placeholder: 'title' });
  T(s, 'BÁO ĐỘNG TRÊN ESP32', { x: 0.6, y: 1.55, w: 6.6, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const chip = (x, y, w, ic, t, d, red) => {
    box(s, { x, y, w, h: 0.75, line: { color: red ? C.accent4 : 'CBD5E1', width: 1 } });
    s.addImage({ data: icon(ic, red ? HEX.accent4 : HEX.accent1), x: x + 0.1, y: y + 0.17, w: 0.42, h: 0.42 });
    T(s, [{ text: t, options: { bold: true, breakLine: !!d } }, ...(d ? [{ text: d, options: { fontSize: 11, color: C.accent5 } }] : [])], { x: x + 0.6, y: y + 0.08, w: w - 0.65, h: 0.62, fontSize: 13, color: C.text2, valign: 'middle' });
  };
  const ins = [['mdiFire', 'Lửa', 'IO18, báo sau 0,3 s'], ['mdiMolecule', 'Khí gas', 'MQ-2 vượt ngưỡng'], ['mdiMotionSensor', 'Đột nhập', 'PIR/cửa khi vắng nhà']];
  const outs = [['mdiBullhorn', 'Còi kêu liên tục', ''], ['mdiLedStripVariant', 'LED RGB nháy đỏ', ''], ['mdiFan', 'Quạt hút bật', 'khi có gas']];
  ins.forEach((r, i) => { chip(0.6, 2.0 + i * 0.95, 2.15, ...r, true); arrow(s, 2.75, 2.375 + i * 0.95, 3.05, 2.375 + i * 0.95); });
  box(s, { x: 3.05, y: 2.0, w: 1.75, h: 2.65, fill: { color: C.text2 }, shadow: true, name: 'Vòng báo động' });
  s.addImage({ data: icon('mdiAlarmLight', HEX.accent2), x: 3.6, y: 2.2, w: 0.65, h: 0.65 });
  T(s, 'Vòng kiểm tra\n500 ms', { x: 3.1, y: 3.0, w: 1.65, h: 0.75, fontSize: 15, bold: true, align: 'center', color: C.background1 });
  T(s, 'chạy liên tục trên ESP32', { x: 3.1, y: 3.8, w: 1.65, h: 0.6, fontSize: 11, align: 'center', color: C.accent2 });
  outs.forEach((r, i) => { arrow(s, 4.8, 2.375 + i * 0.95, 5.1, 2.375 + i * 0.95); chip(5.1, 2.0 + i * 0.95, 2.1, ...r); });
  arrow(s, 3.925, 4.65, 3.925, 5.05);
  box(s, { x: 0.6, y: 5.05, w: 6.6, h: 0.8, fill: { color: C.accent1, transparency: 88 } });
  s.addImage({ data: icon('mdiCellphoneMessage', HEX.accent1), x: 0.75, y: 5.22, w: 0.45, h: 0.45 });
  T(s, 'Sự kiện MQTT → HA gửi thông báo điện thoại (kêu cả khi máy để im lặng), kèm nút “Tắt báo động”', { x: 1.35, y: 5.1, w: 5.75, h: 0.7, fontSize: 13, color: C.text2, valign: 'middle' });
  T(s, 'Tắt báo động: còi im ngay; đèn vẫn nháy đỏ tới khi hết lửa/gas', { x: 0.6, y: 6.05, w: 6.6, h: 0.3, fontSize: 13, italic: true, color: C.accent5 });

  box(s, { x: 7.6, y: 1.55, w: 5.13, h: 5.1, fill: { color: C.background2 }, name: 'Tự động hóa' });
  T(s, 'TỰ ĐỘNG HÓA & NGƯỠNG', { x: 7.85, y: 1.75, w: 4.7, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const rules = [
    ['Đèn hiên', 'chuyển động + trời tối → bật; hết chuyển động → tắt sau N phút'],
    ['Quạt hút', 'độ ẩm ≥ ngưỡng → bật; ≤ ngưỡng − 5 % → tắt'],
    ['Trời tối', 'ánh sáng < ngưỡng; sáng lại khi > ngưỡng + 10 %'],
    ['Gas', 'ngưỡng điện áp, trễ 0,2 V; 60 s đầu không bật còi/quạt (MQ-2 làm nóng)'],
    ['Ưu tiên', 'gas > tự động theo độ ẩm > bật tay'],
  ];
  rules.forEach(([k, v], i) => {
    T(s, [{ text: k + ': ', options: { bold: true, color: C.text2 } }, { text: v }], { x: 7.85, y: 2.2 + i * 0.66, w: 4.7, h: 0.6, fontSize: 14, color: C.text1 });
  });
  T(s, 'Mọi ngưỡng chỉnh trên HA, lưu vào flash ESP32', { x: 7.85, y: 5.5, w: 4.7, h: 0.3, fontSize: 13, italic: true, color: C.accent1 });
  box(s, { x: 7.85, y: 5.9, w: 4.65, h: 0.6, fill: { color: 'FFFBEB' }, line: { color: C.accent3, width: 1 } });
  T(s, [{ text: 'Vắng nhà: ', options: { bold: true, color: C.accent3 } }, { text: '30 s để ra khỏi nhà; sau đó PIR/cửa mở → đột nhập (bật/tắt đã test, báo đột nhập chưa kích được)' }], { x: 7.97, y: 5.93, w: 4.45, h: 0.55, fontSize: 12, color: C.text1, valign: 'middle' });
}

// =====================================================================
// S9 · Giao diện (ảnh chụp thật dashboard 21/10/2026)
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Triển khai');
  kicker(s, '08 · GIAO DIỆN');
  s.addText('Dashboard 5 trang, thông báo điện thoại và giọng nói', { placeholder: 'title' });
  const shots = [
    ['live_tongquan.png', 'Tổng quan — mặt bằng 2D, chạm để điều khiển'],
    ['live_3d.png', 'Mô hình 3D — tự chuyển chế độ đêm'],
    ['live_dieukhien.png', 'Điều khiển — theo phòng, biểu đồ 24 giờ'],
    ['live_truycap.png', 'Lịch sử truy cập — đọc từ MariaDB'],
  ];
  const W = 3.95, Hh = 2.135; // ảnh đã cắt cùng tỉ lệ 1,85
  shots.forEach(([f, cap], i) => {
    const x = 0.6 + (i % 2) * (W + 0.2), y = 1.5 + Math.floor(i / 2) * (Hh + 0.45);
    s.addImage({ path: ASSET(f), x, y, w: W, h: Hh, altText: 'Ảnh chụp thật: ' + cap });
    s.addShape(S.RECTANGLE, { x, y, w: W, h: Hh, fill: { type: 'none' }, line: { color: 'CBD5E1', width: 1 } });
    T(s, cap, { x, y: y + Hh + 0.07, w: W, h: 0.28, fontSize: 12, bold: true, color: C.text2 });
  });
  T(s, 'Ảnh chụp thật lúc mạch đang chạy, 21/10/2026 · số công suất ≈ 80 W trên ảnh là giá trị sai của ACS712 (xem slide 12)', { x: 0.6, y: 6.62, w: 8.1, h: 0.28, fontSize: 11, color: C.accent5 });

  T(s, 'DASHBOARD “SMARTHOME ĐỒ ÁN”', { x: 9.05, y: 1.5, w: 3.68, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  const pages = [
    ['mdiFloorPlan', 'Tổng quan', 'mặt bằng 2D, chạm để điều khiển'],
    ['mdiTuneVariant', 'Điều khiển', 'theo phòng, biểu đồ 24 giờ'],
    ['mdiCubeOutline', 'Mô hình 3D', 'three.js, theo trạng thái thật'],
    ['mdiHistory', 'Lịch sử truy cập', 'đọc từ MariaDB'],
    ['mdiCardAccountDetails', 'Quản lý', 'thêm, khóa, xóa thẻ RFID'],
  ];
  pages.forEach(([ic, n, d], i) => {
    const y = 1.93 + i * 0.68;
    iconDot(s, ic, 9.05, y, 0.46, C.accent1, 'FFFFFF', { pad: 0.2 });
    T(s, [{ text: n, options: { bold: true, breakLine: true } }, { text: d, options: { fontSize: 12, color: C.accent5 } }], { x: 9.65, y: y - 0.04, w: 3.08, h: 0.62, fontSize: 14, color: C.text2 });
  });
  T(s, 'KÊNH KHÁC', { x: 9.05, y: 5.45, w: 3.68, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent1 });
  T(s, 'Thông báo có nút hành động · Assist: “tắt còi”, “mở cửa” · Trang web dự phòng trên ESP32', { x: 9.05, y: 5.8, w: 3.68, h: 0.85, fontSize: 13, color: C.text1 });
}

// =====================================================================
// S10 · Kiểm thử & kết quả
// =====================================================================
pres.addSection({ title: 'Kết quả & đánh giá' });
{
  const s = newSlide('NOI_DUNG', 'Kết quả & đánh giá');
  kicker(s, '09 · KẾT QUẢ VẬN HÀNH');
  s.addText('Số liệu thật từ MariaDB, 17/10 – 20/10/2026', { placeholder: 'title' });
  const stats = [
    ['37', 'lượt quẹt thẻ', '23 hợp lệ · 14 sai thẻ'],
    ['101', 'lần cửa mở', '133 lệnh mở từ xa'],
    ['4 · 6', 'báo cháy · báo gas', 'đều ghi vào bảng events'],
    ['≤ 1 s', 'lệch giờ ESP32 ↔ DB', 'trên 183 sự kiện có giờ SNTP'],
  ];
  stats.forEach(([n, l, d], i) => {
    const x = 0.6 + i * 3.08;
    box(s, { x, y: 1.55, w: 2.9, h: 1.6, line: { color: 'CBD5E1', width: 1 }, shadow: true });
    T(s, n, { x: x + 0.2, y: 1.65, w: 2.5, h: 0.7, fontSize: 36, bold: true, color: C.accent1 });
    T(s, l, { x: x + 0.2, y: 2.35, w: 2.5, h: 0.32, fontSize: 14, bold: true, color: C.text2 });
    T(s, d, { x: x + 0.2, y: 2.68, w: 2.5, h: 0.32, fontSize: 12, color: C.accent5 });
  });
  const cols = [
    ['mdiCheckDecagram', C.accent6, 'Đạt — đo trên mạch', [
      'RC522: chip 0x82, SPI chạy 4 MHz',
      'Cửa: 142 mV đóng, 3139 mV mở',
      'Servo: đóng tới cảm biến 149–388 ms',
      'PIR: đạt sau khi đi dây 5 V riêng',
    ]],
    ['mdiFormatListChecks', C.accent1, 'Có ghi nhận hoạt động', [
      'Quẹt thẻ; còi cảnh báo khi sai 3 lần',
      'Báo cháy, báo gas, cửa vướng (1 lần)',
      'Thông báo sai thẻ và báo động',
      'Mở cửa bằng script điện thoại',
    ]],
    ['mdiProgressClock', C.accent3, 'Chưa kiểm thử', [
      'Báo đột nhập khi vắng nhà',
      'Chạy khi mất Wi-Fi / mất server',
      'Mở cửa bằng sticker NFC thật',
      'Ghi kết quả các ca cần thao tác tay',
    ]],
  ];
  cols.forEach(([ic, col, t, items], i) => {
    const x = 0.6 + i * 4.09;
    box(s, { x, y: 3.4, w: 3.95, h: 3.0, fill: { color: C.background2 } });
    iconDot(s, ic, x + 0.2, 3.58, 0.5, col, 'FFFFFF', { pad: 0.2 });
    T(s, t, { x: x + 0.8, y: 3.66, w: 3.05, h: 0.35, fontSize: 15, bold: true, color: C.text2 });
    T(s, bullets(items, { space: 10 }), { x: x + 0.2, y: 4.25, w: 3.6, h: 2.05, fontSize: 14, color: C.text1 });
  });
  T(s, 'Nguồn: bảng access_log, events (MariaDB); lịch sử HA; chú thích test trong esphome/smarthome.yaml · Test tự động thẻ 3D: 14/14 đạt · Kiểm thử từ xa 21/10: slide sau', { x: 0.6, y: 6.58, w: 12.13, h: 0.3, fontSize: 11, color: C.accent5 });
}

// =====================================================================
// S11 · Kiểm thử trên mạch thật (chạy lại 21/10/2026)
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Kết quả & đánh giá');
  kicker(s, '10 · KIỂM THỬ TRÊN MẠCH THẬT');
  s.addText('13/13 ca test điều khiển từ xa đều đạt trên mạch thật', { placeholder: 'title' });
  const H = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });
  const code = (t) => ({ text: t, options: { bold: true, color: C.accent1 } });
  const ok = (t = 'Đạt') => ({ text: t, options: { bold: true, color: C.accent6 } });
  const no = (t) => ({ text: t, options: { bold: true, color: C.accent3 } });
  const rows = [
    [H('Mã'), H('Kịch bản (theo KICH_BAN_TEST)'), H('Kết quả'), H('Thời gian phản hồi')],
    [code('R1–R4'), 'Bật/tắt 4 relay từ HA: đèn khách, đèn ngủ, đèn hiên, quạt hút', ok('Đạt 4/4'), '14–102 ms'],
    [code('R5'), 'Đổi màu đèn RGB sang xanh dương', ok(), '25 ms'],
    [code('C6 + C2'), 'Nút “Mở cửa” trên dashboard → cửa mở, tự đóng sau 10 s', ok(), 'mở sau 0,29 s · cả chu trình 11,1 s'],
    [code('C7'), 'Bấm “Đóng cửa” khi cửa đang mở → đóng ngay', ok(), '0,57 s'],
    [code('C9'), 'Assist “mở cửa” (gõ văn bản) → cửa mở', ok(), '0,38 s · trả lời “đã mở”'],
    [code('A6'), 'Assist “tắt còi” → bấm nút Tắt báo động', ok(), 'trả lời “Đã tắt còi báo động.”'],
    [code('E5 + E3'), 'Bật lại Chế độ tự động khi độ ẩm 70 % ≥ 58 % → quạt bật; tắt tay → giữ tắt', ok(), 'quạt bật sau 18 ms'],
    [code('S4 + S5'), 'Thêm thẻ trên trang Quản lý → ESP32 nhận (2 → 3 thẻ); xóa → còn 2', ok(), 'thêm 1,59 s · xóa 0,12 s'],
    [code('A7 + A11'), 'Bật / tắt Chế độ vắng nhà', ok(), '15–69 ms'],
    [code('A12*'), 'Mở cửa khi đang vắng nhà → tự tắt chế độ vắng nhà', ok('Đạt (quan sát)'), 'cùng thời điểm mở cửa'],
    [code('A9'), 'Chuyển động khi đang vắng nhà → báo đột nhập', no('Chưa kích được'), 'PIR giữ ON liên tục suốt lúc test'],
  ];
  s.addTable(rows, {
    x: 0.6, y: 1.5, w: 12.13, colW: [1.15, 6.18, 1.75, 3.05], fontSize: 13, color: C.text1, valign: 'middle',
    border: { type: 'solid', pt: 0.75, color: 'CBD5E1' }, rowH: 0.38, margin: [0.04, 0.1, 0.04, 0.1],
  });
  T(s, 'Chạy 21/10/2026 lúc 00:22–00:29 bằng script gọi dịch vụ HA và theo dõi trạng thái ESP32 báo về. Thời gian phản hồi = lúc HA nhận trạng thái mới − lúc gửi lệnh. “Đạt” = ESP32 báo đúng trạng thái; đèn sáng, quạt quay không đo được từ xa. Thẻ thử đã xóa sau test. * A12 ghi nhận từ thao tác tay của nhóm lúc 00:31, không tính vào 13 ca.',
    { x: 0.6, y: 6.28, w: 12.13, h: 0.62, fontSize: 11, color: C.accent5 });
}

// =====================================================================
// S12 · Khó khăn & hạn chế
// =====================================================================
{
  const s = newSlide('NOI_DUNG', 'Kết quả & đánh giá');
  kicker(s, '11 · KHÓ KHĂN & HẠN CHẾ');
  s.addText('Những gì đã gỡ được và những gì còn tồn tại', { placeholder: 'title' });
  const col = (x, ic, color, t, items) => {
    box(s, { x, y: 1.55, w: 5.95, h: 5.1, fill: { color: C.background2 } });
    iconDot(s, ic, x + 0.25, 1.75, 0.55, color, 'FFFFFF', { pad: 0.2 });
    T(s, t, { x: x + 0.95, y: 1.84, w: 4.8, h: 0.4, fontSize: 18, bold: true, color: C.text2 });
    items.forEach(([k, v], i) => {
      const y = 2.5 + i * 0.82;
      T(s, k, { x: x + 0.3, y, w: 5.4, h: 0.3, fontSize: 14, bold: true, color: C.text2 });
      T(s, v, { x: x + 0.3, y: y + 0.3, w: 5.4, h: 0.45, fontSize: 13, color: C.accent5 });
    });
  };
  col(0.6, 'mdiCheck', C.accent6, 'Khó khăn đã giải quyết', [
    ['Servo không quay', 'Kênh PWM chung timer với LED RGB 1 kHz → tách sang kênh 4'],
    ['MQ-2 luôn báo gas', 'AO cắm IO15 (ADC2, không đọc analog khi bật Wi-Fi) → chuyển sang IO39'],
    ['PIR luôn báo có người', 'Dùng chung dây 5 V với relay, servo → đi dây nguồn riêng'],
    ['Servo 360° không giữ góc', 'Mở theo thời gian quay, đóng tới khi công tắc từ báo'],
    ['Lỗi khi nạp firmware', 'IO12 là chân strapping → rút servo khi nạp lần đầu'],
  ]);
  col(6.78, 'mdiAlertCircle', C.accent3, 'Hạn chế hiện tại', [
    ['Cảnh báo “ESP32 offline” chưa từng gửi', 'Automation chờ “off”, thực tế mất kết nối là “unavailable”'],
    ['MQTT chưa mã hóa', 'Cổng 1883; đã có cấu hình TLS mẫu nhưng chưa dùng'],
    ['RFID chỉ so UID', 'UID thẻ có thể bị sao chép'],
    ['Đo dòng chưa tin cậy', 'ACS712-20A sai số ±0,1–0,2 A, từng ghi giá trị vô lý'],
    ['Chưa nạp OTA được', 'HA và ESP32 khác mạng → phải nạp qua USB'],
  ]);
}

// =====================================================================
// S13 · Kết luận & hỏi đáp
// =====================================================================
{
  const s = newSlide('KET_LUAN', 'Kết quả & đánh giá');
  kicker(s, '12 · KẾT LUẬN', true);
  s.addText('Kết quả đạt được và hướng phát triển', { placeholder: 'title' });
  T(s, 'ĐÃ ĐẠT ĐƯỢC', { x: 0.6, y: 1.6, w: 6, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: C.accent2 });
  const done = [
    'Hệ thống chạy trên mạch thật: 1 ESP32, 8 cảm biến, tích hợp Home Assistant qua MQTT; 13/13 ca test từ xa đạt',
    'Kịch bản an toàn chạy cục bộ: cửa RFID có chống kẹt, báo cháy và báo gas',
    'Lịch sử trong MariaDB, dashboard 5 trang có mô hình 3D, thông báo điện thoại',
  ];
  done.forEach((t, i) => {
    const y = 2.05 + i * 1.0;
    s.addImage({ data: icon('mdiCheckCircle', HEX.accent2), x: 0.6, y: y + 0.02, w: 0.45, h: 0.45 });
    T(s, t, { x: 1.25, y, w: 5.3, h: 0.85, fontSize: 16, color: C.background1 });
  });
  box(s, { x: 7.0, y: 1.6, w: 5.73, h: 3.25, fill: { color: C.background1, transparency: 92 }, line: { color: '3B5578', width: 1 } });
  T(s, 'HƯỚNG PHÁT TRIỂN — ĐỀ XUẤT, CHƯA LÀM', { x: 7.3, y: 1.8, w: 5.2, h: 0.3, fontSize: 13, bold: true, charSpacing: 1, color: 'FCD34D' });
  T(s, bullets([
    'Bật MQTT qua TLS (cổng 8883)',
    'Sửa cảnh báo offline theo trạng thái “unavailable”',
    'Xác thực mạnh hơn: thẻ có mã hóa hoặc thêm mã PIN',
    'Chạy đủ bộ kịch bản test và ghi kết quả',
    'Đưa ESP32 và HA về cùng mạng để nạp OTA',
  ], { space: 12 }), { x: 7.3, y: 2.25, w: 5.2, h: 2.5, fontSize: 15, color: C.background1 });
  T(s, 'Cảm ơn thầy cô đã lắng nghe · Hỏi & đáp', { x: 0.6, y: 5.65, w: 12.13, h: 0.7, fontSize: 28, bold: true, align: 'center', valign: 'middle', color: C.background1 });
}

// ---------- Ghi file ----------
(async () => {
  await pres.writeFile({ fileName: DECK });
  await applyTheme(DECK, THEME);
  // Ghi chú thuyết trình dạng Markdown (cùng nguồn notes.js)
  const toSec = (t) => { const [m, s] = t.split(':').map(Number); return m * 60 + s; };
  const total = NOTES.reduce((a, n) => a + toSec(n.time), 0);
  const md = [
    '# Smarthome — Ghi chú thuyết trình (bản nháp)', '',
    `Tổng thời gian dự kiến: **${Math.floor(total / 60)} phút ${total % 60} giây** cho ${NOTES.length} slide (mục tiêu 10–15 phút, còn ≈ 2 phút cho demo hoặc câu hỏi).`, '',
    'Nội dung trùng với phần Notes trong `SmartHome_Project_Report.pptx`. Số liệu: xem `SmartHome_Evidence_Map.md`.', '',
    ...NOTES.flatMap((n, i) => [
      `## Slide ${i + 1} · ${n.title} — khoảng ${n.time}`, '',
      ...n.say.map((p) => p), '',
      ...(n.detail.length ? ['**Chi tiết không có trên slide:**', '', ...n.detail.map((d) => '- ' + d), ''] : []),
      ...(n.next ? [`**Chuyển ý:** ${n.next}`, ''] : []),
    ]),
  ].join('\n');
  fs.writeFileSync(path.join(OUT, 'SmartHome_Presentation_Notes.md'), md);
  console.log('Đã ghi', DECK, '·', NOTES.length, 'slide · tổng', total, 's');
})().catch((e) => { console.error(e); process.exit(1); });
