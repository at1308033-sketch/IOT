"""Sinh flows.json + flows_cred.json cho Node-RED (tab "Smarthome đồ án")."""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys

NR = "/addon_configs/a0d7b954_nodered"
DOC = "/config/smarthome/nodered/flows.json"


def secret(key):
    s = open("/config/secrets.yaml", encoding="utf-8").read()
    return re.search(rf'^{key}:\s*"(.*)"\s*$', s, re.M).group(1)


TAB = "sh_tab"
BROKER = "sh_mqtt_broker"
DB = "sh_mysql"

VN_TIME = r"""
// Giờ Việt Nam (UTC+7, không có giờ mùa hè) dạng 'YYYY-MM-DD HH:MM:SS'
function vn(d) { return new Date(d.getTime() + 7 * 3600e3).toISOString().slice(0, 19).replace('T', ' '); }
// ts của ESP32: '2026-10-05T09:30:12+0700' → giờ VN; sai định dạng / chưa đồng bộ giờ → null
function deviceTs(ts) {
    if (typeof ts !== 'string') return null;
    const m = ts.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})([+-]\d{2})(\d{2})$/);
    if (!m) return null;
    const d = new Date(`${m[1]}T${m[2]}${m[3]}:${m[4]}`);
    if (isNaN(d) || d.getUTCFullYear() < 2024) return null;
    return vn(d);
}
"""

FN_ACCESS = VN_TIME + r"""
const p = msg.payload;
if (typeof p !== 'object' || p === null) { node.warn('Payload không phải JSON'); return null; }
const result = ['granted', 'denied', 'lockout'].includes(p.result) ? p.result : null;
const method = ['rfid', 'remote', 'phone'].includes(p.method) ? p.method : null;
if (!result || !method) { node.warn(['Sự kiện truy cập không hợp lệ', p]); return null; }
// UID thẻ viết hoa; với điện thoại uid là tên máy → giữ nguyên
const uid = (method === 'phone' ? String(p.uid || '') : String(p.uid || '').toUpperCase()).slice(0, 32);
msg.topic = `INSERT INTO access_log (ts_device, ts_server, uid, card_id, holder_name, result, method)
             SELECT ?, ?, ?, c.id, c.holder_name, ?, ?
             FROM (SELECT 1) AS x LEFT JOIN cards c ON c.uid = ?`;
msg.payload = [deviceTs(p.ts), vn(new Date()), uid, result, method, uid];
node.status({ fill: result === 'granted' ? 'green' : 'red', shape: 'dot', text: `${uid || 'từ xa'} · ${result}` });
return msg;
"""

FN_EVENT = VN_TIME + r"""
const p = msg.payload;
if (typeof p !== 'object' || p === null) { node.warn('Payload không phải JSON'); return null; }
const type = String(p.type || '').slice(0, 20);
const kind = String(p.kind || '').slice(0, 20);
const state = String(p.state || '').slice(0, 20);
if (!['door', 'alarm'].includes(type) || !kind || !state) { node.warn(['Sự kiện không hợp lệ', p]); return null; }
msg.topic = 'INSERT INTO events (ts_device, ts_server, type, kind, state) VALUES (?, ?, ?, ?, ?)';
msg.payload = [deviceTs(p.ts), vn(new Date()), type, kind, state];
node.status({ fill: 'blue', shape: 'dot', text: `${type}/${kind}: ${state}` });
return msg;
"""

FN_CARD_CMD = r"""
// Lệnh từ HA: {"action":"add|enable|disable|delete","uid":"AA-BB-CC-DD","name":"Nguyễn Văn A"}
const p = msg.payload;
if (typeof p !== 'object' || p === null) { node.warn('Payload không phải JSON'); return null; }
const uid = String(p.uid || '').trim().toUpperCase();
if (!/^[0-9A-F]{2}(-[0-9A-F]{2}){3,9}$/.test(uid)) { node.warn(`UID không hợp lệ: "${uid}"`); return null; }
const name = String(p.name || '').trim().slice(0, 100);
switch (p.action) {
    case 'add':
        msg.topic = `INSERT INTO cards (uid, holder_name, active) VALUES (?, ?, 1)
                     ON DUPLICATE KEY UPDATE active = 1,
                       holder_name = IF(VALUES(holder_name) = '', holder_name, VALUES(holder_name))`;
        msg.payload = [uid, name];
        break;
    case 'enable':
    case 'disable':
        msg.topic = 'UPDATE cards SET active = ? WHERE uid = ?';
        msg.payload = [p.action === 'enable' ? 1 : 0, uid];
        break;
    case 'delete':
        msg.topic = 'DELETE FROM cards WHERE uid = ?';
        msg.payload = [uid];
        break;
    default:
        node.warn(`Lệnh không hỗ trợ: ${p.action}`);
        return null;
}
node.status({ fill: 'green', shape: 'dot', text: `${p.action} ${uid}` });
return msg;
"""

FN_LIST_QUERY = r"""
msg.topic = "SELECT COALESCE(GROUP_CONCAT(uid ORDER BY id SEPARATOR ','), '') AS list, COUNT(*) AS n FROM cards WHERE active = 1";
msg.payload = [];
return msg;
"""

FN_LIST_PUBLISH = r"""
const row = (msg.payload && msg.payload[0]) || { list: '', n: 0 };
if (row.list.length > 250) {
    node.error(`Danh sách thẻ dài ${row.list.length} ký tự (> 250) — ESP32 sẽ bỏ qua. Hãy xóa bớt thẻ.`);
}
msg.topic = 'smarthome/config/cards';
// Không gửi chuỗi rỗng: retained rỗng = XÓA tin giữ lại, ESP32 sẽ giữ danh sách cũ. "-" = không có thẻ nào
msg.payload = row.list || '-';
msg.retain = true;
msg.qos = 1;
node.status({ fill: 'green', shape: 'dot', text: `${row.n} thẻ hợp lệ` });
return msg;
"""


def fn(id_, name, code, x, y, wires, outputs=1):
    return {"id": id_, "type": "function", "z": TAB, "name": name, "func": code.strip(),
            "outputs": outputs, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "",
            "libs": [], "x": x, "y": y, "wires": wires}


def mqtt_in(id_, name, topic, x, y, wires):
    return {"id": id_, "type": "mqtt in", "z": TAB, "name": name, "topic": topic, "qos": "1",
            "datatype": "json", "broker": BROKER, "nl": False, "rap": True, "rh": 0,
            "inputs": 0, "x": x, "y": y, "wires": wires}


def mysql(id_, name, x, y, wires):
    return {"id": id_, "type": "mysql", "z": TAB, "mydb": DB, "name": name, "x": x, "y": y,
            "wires": wires}


def comment(id_, name, info, x, y):
    return {"id": id_, "type": "comment", "z": TAB, "name": name, "info": info, "x": x, "y": y,
            "wires": []}


flows = [
    {"id": TAB, "type": "tab", "label": "Smarthome đồ án", "disabled": False,
     "info": "ESP32 → MQTT → MariaDB (database smarthome).\n"
             "Quản lý thẻ: HA → smarthome/cmd/cards → bảng cards → smarthome/config/cards (retained) → ESP32."},
    {"id": BROKER, "type": "mqtt-broker", "name": "Mosquitto (nội bộ)", "broker": "core-mosquitto",
     "port": "1883", "clientid": "nodered-smarthome", "autoConnect": True, "usetls": False,
     "protocolVersion": "4", "keepalive": "60", "cleansession": True, "autoUnsubscribe": True,
     "birthTopic": "", "closeTopic": "", "willTopic": "", "userProps": "", "sessionExpiry": ""},
    {"id": DB, "type": "MySQLdatabase", "name": "MariaDB smarthome", "host": "core-mariadb",
     "port": "3306", "db": "smarthome", "tz": "+07:00", "charset": "UTF8MB4"},

    comment("c1", "① Lịch sử truy cập → access_log", "", 170, 40),
    mqtt_in("in_access", "smarthome/event/access", "smarthome/event/access", 170, 80, [["fn_access"]]),
    fn("fn_access", "Chuẩn bị INSERT access_log", FN_ACCESS, 430, 80, [["db_access"]]),
    mysql("db_access", "Ghi access_log", 680, 80, [["dbg_err"]]),

    comment("c2", "② Cửa / báo cháy → events", "", 150, 140),
    mqtt_in("in_door", "smarthome/event/door", "smarthome/event/door", 160, 180, [["fn_event"]]),
    mqtt_in("in_alarm", "smarthome/event/alarm", "smarthome/event/alarm", 160, 220, [["fn_event"]]),
    fn("fn_event", "Chuẩn bị INSERT events", FN_EVENT, 430, 200, [["db_event"]]),
    mysql("db_event", "Ghi events", 670, 200, [["dbg_err"]]),

    comment("c3", "③ Quản lý thẻ → cards → gửi danh sách cho ESP32", "", 230, 280),
    mqtt_in("in_cmd", "smarthome/cmd/cards", "smarthome/cmd/cards", 160, 320, [["fn_cmd"]]),
    fn("fn_cmd", "Lệnh thẻ → SQL", FN_CARD_CMD, 400, 320, [["db_cmd"]]),
    mysql("db_cmd", "Cập nhật cards", 610, 320, [["fn_list_q"]]),
    {"id": "inj_start", "type": "inject", "z": TAB, "name": "Khi khởi động + mỗi giờ",
     "props": [], "repeat": "3600", "crontab": "", "once": True, "onceDelay": "5", "topic": "",
     "x": 190, "y": 380, "wires": [["fn_list_q"]]},
    fn("fn_list_q", "Truy vấn thẻ hợp lệ", FN_LIST_QUERY, 830, 340, [["db_list"]]),
    mysql("db_list", "Đọc cards", 1030, 340, [["fn_list_pub"]]),
    fn("fn_list_pub", "Danh sách UID", FN_LIST_PUBLISH, 1210, 340, [["out_cards"]]),
    {"id": "out_cards", "type": "mqtt out", "z": TAB, "name": "smarthome/config/cards (retained)",
     "topic": "", "qos": "", "retain": "", "respTopic": "", "contentType": "", "userProps": "",
     "correl": "", "expiry": "", "broker": BROKER, "x": 1460, "y": 340, "wires": []},

    {"id": "catch_all", "type": "catch", "z": TAB, "name": "Lỗi SQL / MQTT", "scope": None,
     "uncaught": False, "x": 150, "y": 460, "wires": [["dbg_err"]]},
    {"id": "dbg_err", "type": "debug", "z": TAB, "name": "Nhật ký", "active": True,
     "tosidebar": True, "console": True, "tostatus": False, "complete": "true",
     "targetType": "full", "statusVal": "", "statusType": "auto", "x": 920, "y": 460, "wires": []},
]

# Tab "Mô phỏng ESP32" (ESP32 ảo khi chưa có mạch) — xem build_sim.py
import build_sim  # noqa: E402
flows += build_sim.nodes(BROKER)

existing = json.load(open(f"{NR}/flows.json"))
keep = [n for n in existing if n.get("z", "") not in (TAB, build_sim.SIM_TAB)
        and n["id"] not in {x["id"] for x in flows}]
all_flows = keep + flows

creds = {
    BROKER: {"user": "nodered", "password": secret("smarthome_nodered_mqtt_password")},
    DB: {"user": "nodered_rw", "password": secret("smarthome_db_nodered_password")},
}

# Mã hóa giống Node-RED: aes-256-ctr, key = sha256(credentialSecret), iv ngẫu nhiên 16 byte
key = hashlib.sha256(secret("smarthome_nodered_credential_secret").encode()).hexdigest()
iv = os.urandom(16).hex()
enc = subprocess.run(["openssl", "enc", "-aes-256-ctr", "-K", key, "-iv", iv, "-base64", "-A"],
                     input=json.dumps(creds).encode(), capture_output=True, check=True).stdout.decode()

if sys.argv[1:] == ["write"]:
    json.dump(all_flows, open(f"{NR}/flows.json", "w"), ensure_ascii=False, indent=2)
    json.dump({"$": iv + enc}, open(f"{NR}/flows_cred.json", "w"))
    os.makedirs(os.path.dirname(DOC), exist_ok=True)
    json.dump(flows, open(DOC, "w"), ensure_ascii=False, indent=2)
    print("written", len(all_flows), "nodes")
else:
    # tự kiểm tra giải mã
    raw = base64.b64decode(enc)
    dec = subprocess.run(["openssl", "enc", "-d", "-aes-256-ctr", "-K", key, "-iv", iv],
                         input=raw, capture_output=True, check=True).stdout
    assert json.loads(dec) == creds
    print("ok", len(all_flows), "nodes (dry-run)")
