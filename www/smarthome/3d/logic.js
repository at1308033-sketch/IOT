// Hàm thuần cho thẻ 3D: ánh xạ state HA -> trạng thái hiển thị (không import gì)

// Loại thiết bị + độ cao gắn z (mm); dht gom 2 entity nhiệt/ẩm
export const KINDS = {
  door: { kind: "door", z: 0 },
  buzzer: { kind: "buzzer", z: 70 },
  pir: { kind: "pir", z: 80 },
  living: { kind: "lamp", z: 86 },
  rgb: { kind: "rgb", z: 80 },
  porch: { kind: "lamp", z: 70 },
  rfid: { kind: "rfid", z: 45 },
  ldr: { kind: "ldr", z: 75 },
  gas: { kind: "gas", z: 60 },
  gaslvl: { kind: "label", z: 110 },
  flame: { kind: "flame", z: 40 },
  fan: { kind: "fan", z: 75 },
  dht: {
    kind: "label", z: 110,
    entities: ["sensor.smarthome_nhiet_do_phong_ngu", "sensor.smarthome_do_am_phong_ngu"],
  },
  bedroom: { kind: "lamp", z: 86 },
};

// Entity trạng thái chung của hệ thống
export const STATUS = {
  link: "binary_sensor.smarthome_ket_noi",
  temp: "sensor.smarthome_nhiet_do_phong_ngu",
  hum: "sensor.smarthome_do_am_phong_ngu",
  gas: "sensor.smarthome_muc_khi_gas",
  power: "sensor.smarthome_cong_suat_tieu_thu",
  dark: "binary_sensor.smarthome_troi_toi",
  alarmButton: "button.smarthome_tat_bao_dong",
  alarms: [
    "binary_sensor.smarthome_bao_chay_bep",
    "binary_sensor.smarthome_bao_khi_gas_bep",
    "binary_sensor.smarthome_bao_dong_dot_nhap",
  ],
  intrusion: "binary_sensor.smarthome_bao_dong_dot_nhap",
};

export const isUnavailable = (st) => !st || st.state === "unavailable";

// "23 °C"; unavailable/unknown/thiếu -> "—"
export function fmtState(st) {
  if (!st || st.state === "unavailable" || st.state === "unknown" || st.state == null) return "—";
  const unit = st.attributes && st.attributes.unit_of_measurement;
  return unit ? `${st.state} ${unit}` : String(st.state);
}

const ON_KINDS = ["lamp", "rgb", "fan", "buzzer", "pir", "gas", "flame", "ldr"];

// sts[0] là entity chính. color/brightness chỉ có nghĩa với rgb
// (loại khác: color null, brightness 1 khi bật, 0 khi tắt); door/moving chỉ cho door.
export function visualState(kind, sts) {
  const st = sts[0];
  const v = {
    unavailable: kind === "label" ? sts.every(isUnavailable) : isUnavailable(st),
    on: ON_KINDS.includes(kind) && !!st && st.state === "on",
    color: null, brightness: 0, door: 0, moving: false, text: null,
  };
  v.brightness = v.on ? 1 : 0;
  if (kind === "rgb" && v.on) {
    const a = st.attributes || {};
    v.color = Array.isArray(a.rgb_color) ? a.rgb_color : [255, 255, 255];
    v.brightness = typeof a.brightness === "number" ? a.brightness / 255 : 1;
  }
  if (kind === "door" && st) {
    v.door = st.state === "open" || st.state === "opening" ? 1 : 0;
    v.moving = st.state === "opening" || st.state === "closing";
  }
  if (kind === "label") v.text = sts.map(fmtState).join(" · ");
  else if (kind === "rfid") v.text = st ? st.state : null;
  return v;
}

// Chạm vào thiết bị: gọi service toggle hoặc mở more-info (khi unavailable luôn more-info)
export function tapCall(dev, st) {
  if (dev.tap === "toggle" && !isUnavailable(st)) {
    return { domain: dev.entity.split(".")[0], service: "toggle", data: { entity_id: dev.entity } };
  }
  return { moreInfo: dev.entity };
}

export const alarmActive = (states) =>
  STATUS.alarms.some((id) => states[id] && states[id].state === "on");

export function resolveTheme(mode, states) {
  if (mode === "day" || mode === "night") return mode;
  const d = states[STATUS.dark];
  return d && d.state === "on" ? "night" : "day";
}

const hex = () => Math.floor(Math.random() * 256).toString(16).toUpperCase().padStart(2, "0");

// Mô phỏng chế độ demo: trả state kế tiếp của entity
export function demoNext(entityId, st) {
  const domain = entityId.split(".")[0];
  const old = st ? st.state : undefined;
  const attributes = (st && st.attributes) || {};
  if (domain === "sensor") {
    let s;
    do { s = [hex(), hex(), hex(), hex()].join("-"); } while (s === old);
    return { state: s, attributes };
  }
  if (domain === "cover") return { state: old === "open" ? "closed" : "open", attributes };
  const state = old === "on" ? "off" : "on";
  if (domain === "light" && state === "on") {
    return {
      state,
      attributes: {
        ...attributes,
        rgb_color: attributes.rgb_color || [255, 255, 255],
        brightness: attributes.brightness ?? 255,
      },
    };
  }
  return { state, attributes };
}
