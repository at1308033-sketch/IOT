"""ESP32 ảo trong Node-RED — dùng khi chưa có mạch.

Phát MQTT y hệt firmware ESPHome (smarthome.yaml): cùng topic `smarthome-doan/...`, cùng discovery
và unique_id → các entity trong HA (sensor.smarthome_*, switch.smarthome_*…) là MỘT. Khi có mạch thật:
tắt "Bật mô phỏng" rồi cắm ESP32 — ESP32 thật nhận lại đúng các entity đó.

Kèm "Bảng mô phỏng ESP32" (topic `smarthome-sim/...`): chỉnh nhiệt độ, độ ẩm, ánh sáng, có người, có lửa,
quẹt thẻ… để thử toàn bộ kịch bản. Được build_flows.py nhúng vào tab "Mô phỏng ESP32".
"""
import json
import os
import sys

sys.path.insert(0, "/usr/local/lib/python3.13/dist-packages")
os.chdir("/")  # tránh esphome/types.py che module chuẩn khi import
from esphome.helpers import sanitize, snake_case  # noqa: E402

SIM_TAB = "sim_tab"
P = "smarthome-doan"
S = "smarthome-sim"

# Entity của firmware: khóa → (loại MQTT, tên trong smarthome.yaml, cấu hình discovery thêm)
ESP = {
    "status": ("binary_sensor", "Kết nối", {"dev_cla": "connectivity", "ent_cat": "diagnostic"}),
    "door": ("binary_sensor", "Cửa chính", {"dev_cla": "door"}),
    "motion": ("binary_sensor", "Chuyển động phòng khách", {"dev_cla": "motion"}),
    "fire": ("binary_sensor", "Báo cháy bếp", {"dev_cla": "smoke"}),
    "gas": ("binary_sensor", "Báo khí gas bếp", {"dev_cla": "gas"}),
    "dark": ("binary_sensor", "Trời tối", {}),
    "buzzer": ("switch", "Còi", {}),
    "strip": ("switch", "LED dây phòng khách", {}),
    "fan": ("switch", "Quạt phòng ngủ", {}),
    "kitchen": ("switch", "Đèn bếp", {}),
    "porch": ("switch", "Đèn hiên", {}),
    "bedroom": ("switch", "Đèn phòng ngủ", {}),
    "auto": ("switch", "Chế độ tự động", {}),
    "open": ("button", "Mở cửa", {}),
    "close": ("button", "Đóng cửa ngay", {}),
    "calib": ("button", "Hiệu chuẩn ACS712 (0 A)", {"ent_cat": "config"}),
    "tag": ("sensor", "Thẻ vừa quẹt", {}),  # text_sensor của ESPHome dùng loại "sensor"
    "temp": ("sensor", "Nhiệt độ phòng ngủ", {"unit_of_meas": "°C", "dev_cla": "temperature", "stat_cla": "measurement"}),
    "hum": ("sensor", "Độ ẩm phòng ngủ", {"unit_of_meas": "%", "dev_cla": "humidity", "stat_cla": "measurement"}),
    "ldr": ("sensor", "Cảm biến ánh sáng", {"unit_of_meas": "%", "icon": "mdi:brightness-5", "stat_cla": "measurement"}),
    "flame": ("sensor", "Mức lửa bếp", {"unit_of_meas": "%", "icon": "mdi:fire", "stat_cla": "measurement"}),
    "gaslvl": ("sensor", "Khí gas bếp", {"unit_of_meas": "%", "icon": "mdi:smoke-detector-variant", "stat_cla": "measurement"}),
    "current": ("sensor", "Dòng tổng 5V", {"unit_of_meas": "A", "dev_cla": "current", "stat_cla": "measurement"}),
    "power": ("sensor", "Công suất tiêu thụ", {"unit_of_meas": "W", "dev_cla": "power", "stat_cla": "measurement"}),
    "cards": ("sensor", "Số thẻ hợp lệ", {"icon": "mdi:card-account-details", "ent_cat": "diagnostic"}),
}
ENT = {k: {"comp": c, "obj": sanitize(snake_case(n)), "name": n, "extra": x} for k, (c, n, x) in ESP.items()}
# Entity đã bỏ khỏi firmware (05/10/2026: bỏ 2 đèn RGB) → gửi discovery rỗng để HA xóa
REMOVED = [("light", sanitize(snake_case(n))) for n in ("RGB phòng khách", "RGB phòng ngủ")]

# Bảng điều khiển mô phỏng
PANEL = {
    "enable": ("switch", "Bật mô phỏng", "switch.mo_phong_bat", {"icon": "mdi:chip"}),
    "temp": ("number", "Nhiệt độ phòng ngủ", "number.mo_phong_nhiet_do",
             {"min": 10, "max": 45, "step": 0.5, "unit_of_meas": "°C", "mode": "slider", "icon": "mdi:thermometer"}),
    "hum": ("number", "Độ ẩm phòng ngủ", "number.mo_phong_do_am",
            {"min": 20, "max": 95, "step": 1, "unit_of_meas": "%", "mode": "slider", "icon": "mdi:water-percent"}),
    "light": ("number", "Ánh sáng ngoài trời", "number.mo_phong_anh_sang",
              {"min": 0, "max": 100, "step": 5, "unit_of_meas": "%", "mode": "slider", "icon": "mdi:white-balance-sunny"}),
    "motion": ("switch", "Có người ở phòng khách", "switch.mo_phong_co_nguoi", {"icon": "mdi:walk"}),
    "fire": ("switch", "Có lửa ở bếp", "switch.mo_phong_co_lua", {"icon": "mdi:fire"}),
    "gas": ("number", "Khí gas trong bếp", "number.mo_phong_khi_gas",
            {"min": 0, "max": 100, "step": 5, "unit_of_meas": "%", "mode": "slider", "icon": "mdi:smoke-detector-variant"}),
    "uid": ("text", "UID thẻ để quẹt", "text.mo_phong_uid", {"min": 0, "max": 32, "icon": "mdi:card-text"}),
    "swipe": ("button", "Quẹt thẻ theo UID", "button.mo_phong_quet_uid", {"icon": "mdi:nfc-search-variant"}),
    "swipe_ok": ("button", "Quẹt thẻ hợp lệ", "button.mo_phong_quet_hop_le", {"icon": "mdi:card-account-details"}),
    "swipe_bad": ("button", "Quẹt thẻ lạ", "button.mo_phong_quet_the_la", {"icon": "mdi:card-remove"}),
}

SIM_JS = r"""
const P = '__P__', S = '__S__';
const ENT = __ENT__;
const REMOVED = __REMOVED__;
const PANEL = __PANEL__;
const DEV = { ids: 'smarthome-sim', name: 'Smarthome', mf: 'Espressif', mdl: 'ESP32 ảo (Node-RED)', sw: 'mô phỏng' };
const PDEV = { ids: 'smarthome-sim-panel', name: 'Bảng mô phỏng ESP32', mf: 'Smarthome đồ án', mdl: 'Node-RED' };
const byObj = {};
for (const [k, e] of Object.entries(ENT)) byObj[e.comp + '/' + e.obj] = k;

let st = context.get('st');
if (!st) {
    st = { enabled: null, cards: [], sw: { buzzer: false, strip: false, fan: false, kitchen: false, porch: false, bedroom: false, auto: true },
           door: false, servo: false, motion: false, fire: false, gas: false, gasPct: 5, dark: false,
           temp: 27, hum: 65, light: 60, uid: '', wrong: 0, alarm: false, tag: '' };
    context.set('st', st);
}
const timers = context.get('timers') || {};
context.set('timers', timers);
const outs = [];
const out = (topic, payload, retain = false) =>
    outs.push({ topic, payload: typeof payload === 'string' ? payload : JSON.stringify(payload), retain, qos: 1 });
const T = (k, suffix) => `${P}/${ENT[k].comp}/${ENT[k].obj}/${suffix}`;
const pub = (k, v) => out(T(k, 'state'), String(v), true);      // ESPHome giữ (retain) trạng thái
const ppub = (k, v) => out(`${S}/${PANEL[k][0]}/${k}/state`, String(v), true);
const timer = (name, ms, fn) => { clearTimeout(timers[name]); timers[name] = setTimeout(() => { fn(); flush(); }, ms); };
const flush = () => { if (outs.length) { node.send([outs.splice(0)]); } };
const on = st => (st ? 'ON' : 'OFF');
const vnTs = () => new Date(Date.now() + 7 * 3600e3).toISOString().slice(0, 19) + '+0700';
const logAccess = (uid, result, method) => out('smarthome/event/access', { type: 'access', uid, result, method, ts: vnTs() });
const logEvent = (type, kind, state) => out(`smarthome/event/${type}`, { type, kind, state, ts: vnTs() });

// ---------- discovery ----------
function discovery() {
    for (const [comp, obj] of REMOVED) out(`homeassistant/${comp}/smarthome/${obj}/config`, '', true);
    for (const [k, e] of Object.entries(ENT)) {
        const c = { name: e.name, uniq_id: 'ESP' + e.comp + e.obj, avty_t: `${P}/status`, dev: DEV, ...e.extra };
        if (k === 'status') Object.assign(c, { stat_t: `${P}/status`, pl_on: 'online', pl_off: 'offline' });
        else if (e.comp === 'button') Object.assign(c, { cmd_t: T(k, 'command'), pl_prs: 'PRESS' });
        else if (e.comp === 'switch') Object.assign(c, { stat_t: T(k, 'state'), cmd_t: T(k, 'command'), pl_on: 'ON', pl_off: 'OFF' });
        else if (e.comp === 'binary_sensor') Object.assign(c, { stat_t: T(k, 'state'), pl_on: 'ON', pl_off: 'OFF' });
        else Object.assign(c, { stat_t: T(k, 'state') });
        out(`homeassistant/${e.comp}/smarthome/${e.obj}/config`, c, true);
    }
    for (const [k, [comp, name, eid, extra]] of Object.entries(PANEL)) {
        const c = { name, uniq_id: 'smarthome_sim_' + k, default_entity_id: eid, dev: PDEV, ...extra };
        if (comp !== 'button') c.stat_t = `${S}/${comp}/${k}/state`;
        c.cmd_t = `${S}/${comp}/${k}/command`;
        if (comp === 'switch') Object.assign(c, { pl_on: 'ON', pl_off: 'OFF' });
        if (comp === 'button') c.pl_prs = 'PRESS';
        out(`homeassistant/${comp}/smarthome_sim/${k}/config`, c, true);
    }
}
function panelStates() {
    ppub('enable', on(st.enabled)); ppub('temp', st.temp); ppub('hum', st.hum); ppub('light', st.light);
    ppub('motion', on(st.motion)); ppub('fire', on(st.fire)); ppub('gas', st.gasPct); ppub('uid', st.uid);
}

// ---------- mô phỏng thiết bị ----------
function current() {
    const s = st.sw;
    let a = 0.18;                                                    // ESP32 + relay chờ
    for (const k of ['strip', 'fan', 'kitchen', 'porch', 'bedroom']) if (s[k]) a += 0.07;   // cuộn relay
    a += (s.strip ? 0.45 : 0) + (s.fan ? 0.15 : 0) + (s.kitchen ? 0.06 : 0) + (s.porch ? 0.02 : 0) + (s.bedroom ? 0.06 : 0);
    a += (s.buzzer ? 0.03 : 0) + (st.servo ? 0.25 : 0) + 0.15;      // + sấy MQ-2 ~150 mA
    a += (Math.random() - 0.5) * 0.02;
    pub('current', a.toFixed(2)); pub('power', (a * 5).toFixed(2));
}
function setSw(k, v) { st.sw[k] = v; pub(k, on(v)); current(); }
function alarmUpdate() { setSw('buzzer', st.fire || st.gas); }
function sensors() {
    pub('temp', st.temp.toFixed(1)); pub('hum', Math.round(st.hum));
    pub('ldr', Math.round(st.light));                                 // % ánh sáng như firmware
    if (st.light < 27 && !st.dark) { st.dark = true; pub('dark', 'ON'); }
    else if (st.light > 36 && st.dark) { st.dark = false; pub('dark', 'OFF'); }
    pub('flame', st.fire ? 85 : 0);
    pub('gaslvl', Math.round(st.gasPct));
    current();
}
function climate() {
    if (!st.sw.auto) return;
    if (st.temp > 30 && !st.sw.fan) setSw('fan', true);
    else if (st.temp < 29 && st.sw.fan) setSw('fan', false);
}
function setDoor(open) {
    if (st.door === open) return;
    st.door = open; pub('door', on(open)); logEvent('door', 'main', open ? 'open' : 'closed');
}
function servoMove() { st.servo = true; current(); timer('servo', 1500, () => { st.servo = false; current(); }); }
function beep(ms) { setSw('buzzer', true); timer('beep', ms, () => setSw('buzzer', false)); }
function openDoor() {
    beep(100); servoMove();
    timer('doorOpen', 800, () => setDoor(true));
    timer('doorClose', 6500, closeDoor);
}
function closeDoor() {
    clearTimeout(timers.doorClose); clearTimeout(timers.doorOpen); servoMove();
    timer('doorShut', 1200, () => setDoor(false));
}
function swipe(uid) {
    uid = String(uid || '').trim().toUpperCase().replace(/:/g, '-');
    if (!uid) return;
    st.tag = uid; pub('tag', uid);
    if (st.cards.includes(uid)) { st.wrong = 0; openDoor(); logAccess(uid, 'granted', 'rfid'); }
    else if (++st.wrong >= 3) {
        st.wrong = 0; logAccess(uid, 'lockout', 'rfid');
        if (!st.alarm) { st.alarm = true; setSw('buzzer', true); timer('alarm', 4500, () => { st.alarm = false; alarmUpdate(); }); }
    } else { beep(400); logAccess(uid, 'denied', 'rfid'); }
}
function motion(v) {
    st.motion = v; pub('motion', on(v));
    if (!st.sw.auto) return;
    // như firmware: chỉ LED dây; đèn hiên do automation HA theo trời tối/sáng
    if (v && st.dark) { clearTimeout(timers.lightsOff); setSw('strip', true); }
    if (!v) timer('lightsOff', 30000, () => setSw('strip', false));
}
function fire(v) {
    if (st.fire === v) return;
    st.fire = v; pub('fire', on(v)); pub('flame', v ? 85 : 0);
    logEvent('alarm', 'fire', v ? 'on' : 'off'); alarmUpdate();
}
function gasLevel(pct) {
    st.gasPct = pct; pub('gaslvl', Math.round(pct));
    const v = st.gas ? pct > 40 : pct > 50;                            // ngưỡng có trễ 50/40 % như firmware
    if (v === st.gas) return;
    st.gas = v; pub('gas', on(v)); logEvent('alarm', 'gas', v ? 'on' : 'off'); alarmUpdate();
}
function allStates() {
    for (const k of ['buzzer', 'strip', 'fan', 'kitchen', 'porch', 'bedroom', 'auto']) pub(k, on(st.sw[k]));
    pub('door', on(st.door)); pub('motion', on(st.motion)); pub('fire', on(st.fire)); pub('gas', on(st.gas)); pub('dark', on(st.dark));
    pub('tag', st.tag); pub('cards', st.cards.length); sensors(); climate();
}
function setEnabled(v) {
    st.enabled = v; ppub('enable', on(v));
    if (v) { out(`${P}/status`, 'online', true); allStates(); node.status({ fill: 'green', shape: 'dot', text: 'ESP32 ảo đang chạy' }); }
    else {
        for (const t of Object.values(timers)) clearTimeout(t);
        out(`${P}/status`, 'offline', true); node.status({ fill: 'grey', shape: 'ring', text: 'Đã tắt mô phỏng' });
    }
}

// ---------- xử lý tin nhắn ----------
const t = msg.topic || '', p = String(msg.payload ?? '');
const parts = t.split('/');
if (t === 'init') {
    discovery(); panelStates();
    if (st.enabled === null) setEnabled(true); else setEnabled(st.enabled);
} else if (t === 'tick') {
    if (st.enabled) sensors();
} else if (t === 'homeassistant/status') {
    if (p === 'online') { discovery(); panelStates(); if (st.enabled) { out(`${P}/status`, 'online', true); allStates(); } }
} else if (t === 'smarthome/config/cards') {
    st.cards = p === '-' || p === '' ? [] : p.split(',').map(s => s.trim()).filter(Boolean);
    if (st.enabled) pub('cards', st.cards.length);
} else if (parts[0] === S && parts[3] === 'state') {
    // khôi phục giá trị bảng điều khiển (retained) sau khi Node-RED khởi động lại
    const k = parts[2];
    if (k === 'enable' && st.enabled === null) st.enabled = p === 'ON';
    else if (k === 'temp' || k === 'hum' || k === 'light') st[k] = Number(p);
    else if (k === 'gas') st.gasPct = Number(p);
    else if (k === 'uid') st.uid = p;
} else if (parts[0] === S && parts[3] === 'command') {
    const k = parts[2];
    if (k === 'enable') setEnabled(p === 'ON');
    else if (k === 'uid') { st.uid = p; ppub('uid', p); }
    else if (k === 'temp' || k === 'hum' || k === 'light') {
        st[k] = Number(p); ppub(k, p);
        if (st.enabled) { sensors(); if (k === 'temp') climate(); if (k === 'light' && st.motion) motion(true); }
    } else if (k === 'motion') { st.motion = p === 'ON'; ppub('motion', p); if (st.enabled) motion(st.motion); }
    else if (k === 'fire') { ppub('fire', p); if (st.enabled) fire(p === 'ON'); else st.fire = p === 'ON'; }
    else if (k === 'gas') { ppub('gas', p); if (st.enabled) gasLevel(Number(p)); else st.gasPct = Number(p); }
    else if (st.enabled && k === 'swipe') swipe(st.uid);
    else if (st.enabled && k === 'swipe_ok') { if (st.cards.length) swipe(st.cards[0]); else node.warn('Chưa có thẻ hợp lệ nào'); }
    else if (st.enabled && k === 'swipe_bad') swipe(Array.from({ length: 4 }, () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')).join('-'));
} else if (st.enabled && t === 'smarthome/cmd/door') {
    let j = {}; try { j = JSON.parse(p); } catch (e) {}
    if (j.action === 'open') { openDoor(); logAccess(String(j.by || 'Điện thoại').slice(0, 32), 'granted', 'phone'); }
} else if (st.enabled && parts[0] === P && parts[3] === 'command') {
    const k = byObj[parts[1] + '/' + parts[2]];
    if (!k) return null;
    const comp = parts[1];
    if (comp === 'switch') setSw(k, p === 'ON');
    else if (comp === 'button') {
        if (k === 'open') { openDoor(); logAccess('', 'granted', 'remote'); }
        else if (k === 'close') closeDoor();
    }
}
flush();
return null;
"""


def nodes(broker_id):
    js = (SIM_JS.replace("__P__", P).replace("__S__", S)
          .replace("__ENT__", json.dumps(ENT, ensure_ascii=False))
          .replace("__PANEL__", json.dumps(PANEL, ensure_ascii=False))
          .replace("__REMOVED__", json.dumps(REMOVED)))

    def mqtt_in(id_, topic, y):
        return {"id": id_, "type": "mqtt in", "z": SIM_TAB, "name": topic, "topic": topic, "qos": "1",
                "datatype": "utf8", "broker": broker_id, "nl": True, "rap": True, "rh": 0, "inputs": 0,
                "x": 190, "y": y, "wires": [["sim_core"]]}

    topics = [f"{P}/+/+/command", f"{S}/+/+/command", f"{S}/+/+/state", "smarthome/config/cards",
              "smarthome/cmd/door", "homeassistant/status"]
    return [
        {"id": SIM_TAB, "type": "tab", "label": "Mô phỏng ESP32", "disabled": False,
         "info": "ESP32 ảo thay mạch thật khi chưa có phần cứng. Tắt bằng switch.mo_phong_bat trước khi "
                 "cắm ESP32 thật (hai bên dùng chung topic smarthome-doan/...)."},
        *[mqtt_in(f"sim_in_{i}", tp, 60 + i * 50) for i, tp in enumerate(topics)],
        {"id": "sim_init", "type": "inject", "z": SIM_TAB, "name": "Khởi động (3 s)", "props": [{"p": "topic", "vt": "str"}],
         "topic": "init", "repeat": "", "once": True, "onceDelay": "3", "x": 180, "y": 380, "wires": [["sim_core"]]},
        {"id": "sim_tick", "type": "inject", "z": SIM_TAB, "name": "Cảm biến mỗi 10 s", "props": [{"p": "topic", "vt": "str"}],
         "topic": "tick", "repeat": "10", "once": False, "x": 190, "y": 430, "wires": [["sim_core"]]},
        {"id": "sim_core", "type": "function", "z": SIM_TAB, "name": "ESP32 ảo", "func": js.strip(), "outputs": 1,
         "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [], "x": 480, "y": 240,
         "wires": [["sim_out"]]},
        {"id": "sim_out", "type": "mqtt out", "z": SIM_TAB, "name": "MQTT", "topic": "", "qos": "", "retain": "",
         "respTopic": "", "contentType": "", "userProps": "", "correl": "", "expiry": "", "broker": broker_id,
         "x": 690, "y": 240, "wires": []},
    ]


if __name__ == "__main__":
    for k, e in ENT.items():
        print(f"{k:8s} {e['comp']:13s} {e['obj']:24s} ESP{e['comp']}{e['obj']}")
