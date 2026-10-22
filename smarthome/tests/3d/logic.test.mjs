import test from "node:test";
import assert from "node:assert/strict";
import {
  KINDS, STATUS, isUnavailable, visualState, tapCall,
  alarmActive, resolveTheme, demoNext, fmtState,
} from "../../../www/smarthome/3d/logic.js";

test("KINDS có đủ 14 thiết bị", () => {
  assert.deepEqual(Object.keys(KINDS).sort(),
    ["bedroom","buzzer","dht","door","fan","flame","gas","gaslvl","ldr","living","pir","porch","rfid","rgb"]);
  assert.equal(KINDS.living.kind, "lamp");
  assert.equal(KINDS.gaslvl.kind, "label");
  assert.equal(KINDS.gaslvl.z, 110);
  assert.deepEqual(KINDS.dht.entities,
    ["sensor.smarthome_nhiet_do_phong_ngu", "sensor.smarthome_do_am_phong_ngu"]);
});

test("unavailable", () => {
  assert.equal(isUnavailable(undefined), true);
  assert.equal(isUnavailable({ state: "unavailable" }), true);
  assert.equal(isUnavailable({ state: "unknown" }), false);
});

test("lamp on/off", () => {
  assert.equal(visualState("lamp", [{ state: "on" }]).on, true);
  assert.equal(visualState("lamp", [{ state: "off" }]).on, false);
});

test("rgb color", () => {
  const v = visualState("rgb", [{ state: "on", attributes: { rgb_color: [255, 0, 0], brightness: 128 } }]);
  assert.deepEqual(v.color, [255, 0, 0]);
  assert.ok(Math.abs(v.brightness - 0.502) < 0.001);
});

test("rgb fallback", () => {
  const v = visualState("rgb", [{ state: "on", attributes: {} }]);
  assert.deepEqual(v.color, [255, 255, 255]);
  assert.equal(v.brightness, 1);
});

test("door", () => {
  const d = (s) => visualState("door", [{ state: s }]);
  assert.deepEqual([d("open").door, d("open").moving], [1, false]);
  assert.deepEqual([d("opening").door, d("opening").moving], [1, true]);
  assert.deepEqual([d("closing").door, d("closing").moving], [0, true]);
  assert.deepEqual([d("closed").door, d("closed").moving], [0, false]);
});

test("label dht", () => {
  const t = { state: "28", attributes: { unit_of_measurement: "°C" } };
  const h = { state: "70", attributes: { unit_of_measurement: "%" } };
  assert.equal(visualState("label", [t, h]).text, "28 °C · 70 %");
  const v = visualState("label", [{ state: "unavailable" }, h]);
  assert.equal(v.text, "— · 70 %");
  assert.equal(v.unavailable, false);
  assert.equal(visualState("label", [{ state: "unavailable" }]).unavailable, true);
});

test("rfid text", () => {
  assert.equal(visualState("rfid", [{ state: "A1-B2" }]).text, "A1-B2");
});

test("tap toggle", () => {
  assert.deepEqual(
    tapCall({ entity: "switch.smarthome_den_hien", tap: "toggle" }, { state: "off" }),
    { domain: "switch", service: "toggle", data: { entity_id: "switch.smarthome_den_hien" } });
  assert.equal(tapCall({ entity: "cover.smarthome_cua", tap: "toggle" }, { state: "closed" }).domain, "cover");
});

test("tap more-info", () => {
  assert.deepEqual(tapCall({ entity: "switch.smarthome_coi", tap: "more-info" }, { state: "off" }),
    { moreInfo: "switch.smarthome_coi" });
  assert.deepEqual(tapCall({ entity: "switch.smarthome_coi", tap: "toggle" }, { state: "unavailable" }),
    { moreInfo: "switch.smarthome_coi" });
});

test("theme", () => {
  assert.equal(resolveTheme("auto", { [STATUS.dark]: { state: "on" } }), "night");
  assert.equal(resolveTheme("auto", { [STATUS.dark]: { state: "unavailable" } }), "day");
  assert.equal(resolveTheme("auto", {}), "day");
  assert.equal(resolveTheme("night", {}), "night");
  assert.equal(resolveTheme("day", { [STATUS.dark]: { state: "on" } }), "day");
});

test("alarm", () => {
  assert.equal(alarmActive({ [STATUS.alarms[1]]: { state: "on" } }), true);
  assert.equal(alarmActive({ [STATUS.alarms[0]]: { state: "off" } }), false);
  assert.equal(alarmActive({}), false);
});

test("demo", () => {
  assert.equal(demoNext("switch.x", { state: "on" }).state, "off");
  assert.equal(demoNext("switch.x", undefined).state, "on");
  assert.equal(demoNext("cover.x", { state: "closed" }).state, "open");
  assert.equal(demoNext("cover.x", { state: "open" }).state, "closed");
  const l = demoNext("light.x", { state: "off", attributes: { rgb_color: [1, 2, 3], brightness: 9 } });
  assert.equal(l.state, "on");
  assert.deepEqual(l.attributes.rgb_color, [1, 2, 3]);
  assert.deepEqual(demoNext("light.x", undefined).attributes.rgb_color, [255, 255, 255]);
  const old = "A1-B2-C3-D4";
  for (let i = 0; i < 50; i++) {
    assert.notEqual(demoNext("sensor.smarthome_the_vua_quet", { state: old }).state, old);
  }
  assert.equal(demoNext("binary_sensor.x", { state: "off" }).state, "on");
});

test("fmtState", () => {
  assert.equal(fmtState({ state: "23", attributes: { unit_of_measurement: "°C" } }), "23 °C");
  assert.equal(fmtState({ state: "on" }), "on");
  assert.equal(fmtState({ state: "unavailable" }), "—");
  assert.equal(fmtState({ state: "unknown" }), "—");
  assert.equal(fmtState(undefined), "—");
});
