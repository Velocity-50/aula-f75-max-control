import { api, message, refreshStatus } from "./api.js";
import { initBoard } from "./board.js";
import { bindHex, syncHex } from "./hex.js";
import { initKeymap } from "./keymap.js";
import { initScreen } from "./screen.js";
import { initSettings } from "./settings.js";

const $ = (selector) => document.querySelector(selector);

const SWATCHES = ["#ffffff", "#ff0000", "#ff4000", "#ffd400", "#00ff40", "#00ffff", "#0080ff", "#8000ff", "#ff00ff", "#ff1493"];
const GROUPS = {
  home: ["a", "s", "d", "f", "j", "k", "l", "semicolon"],
  arrows: ["up", "left", "down", "right"],
  wasd: ["w", "a", "s", "d"],
};

let layout;
let state;
let board;
let keymap;
let applying = false;
let pendingApply = false;
let autoTimer;
let view;
let config = "base";
let section = localStorage.getItem("section") === "config" ? "config" : "lighting";

function keyColor(key) {
  if (state.active === "custom") return state.custom.keys[key.name] ?? state.custom.base;

  const effect = state.effect;

  if (effect.mode === "off") return "#000000";
  if (effect.rainbow) return `hsl(${Math.round((key.x / layout.width) * 330)} 100% 50%)`;

  return effect.color;
}

function isLight(color, level) {
  if (!color.startsWith("#")) return false;

  const [r, g, b] = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16));

  return (0.299 * r + 0.587 * g + 0.114 * b) * (level / 100) > 150;
}

function paintBoard() {
  const brightness = state.active === "custom" ? state.custom.brightness : state.effect.brightness;
  const level = state.active === "effect" && state.effect.mode === "off" ? 0 : 35 + brightness * 13;

  for (const key of layout.keys) {
    const el = board.elements.get(key.name);
    const color = keyColor(key);

    el.style.setProperty("--led", color);
    el.style.setProperty("--level", `${level}%`);
    el.classList.toggle("light", isLight(color, level));
  }
}

function syncControls() {
  const { custom, effect } = state;

  for (const tab of document.querySelectorAll(".tabs button[data-view]")) {
    tab.classList.toggle("active", tab.dataset.view === view);
  }

  $("#custom-panel").hidden = view !== "custom";
  $("#effect-panel").hidden = view !== "effect";
  $("#screen-panel").hidden = view !== "screen";

  syncFooter();

  $("#base-color").value = custom.base;
  $("#custom-brightness").value = custom.brightness;
  $("#custom-brightness-out").textContent = custom.brightness;

  $("#effect-mode").value = effect.mode;
  $("#effect-color").value = effect.color;
  $("#effect-color").disabled = effect.rainbow;
  $('.hex[data-for="effect-color"]').disabled = effect.rainbow;
  $("#effect-rainbow").checked = effect.rainbow;
  $("#effect-brightness").value = effect.brightness;
  $("#effect-brightness-out").textContent = effect.brightness;
  $("#effect-speed").value = effect.speed;
  $("#effect-speed-out").textContent = effect.speed;
  $("#effect-direction").value = effect.direction;
  syncHex();
}

function syncFooter() {
  const shown = {
    "lighting-only": section === "lighting" && view !== "screen",
    "keys-only": section === "config" && config !== "settings",
    "settings-only": section === "config" && config === "settings",
  };

  for (const [name, visible] of Object.entries(shown)) {
    for (const el of document.querySelectorAll(`.${name}`)) el.hidden = !visible;
  }
}

function showConfig(next) {
  if (next === "settings") board.select([]);

  config = next;

  for (const tab of document.querySelectorAll("[data-config]")) {
    tab.classList.toggle("active", tab.dataset.config === config);
  }

  $("#keymap-panel").hidden = config === "settings";
  $("#settings-panel").hidden = config !== "settings";
  syncFooter();

  if (config !== "settings") keymap.show(config);
}

function showSection(next) {
  if (next !== section) board.select([]);

  section = next;
  localStorage.setItem("section", section);

  for (const button of document.querySelectorAll("[data-section]")) {
    button.classList.toggle("active", button.dataset.section === section);
  }

  $("#lighting-section").hidden = section !== "lighting";
  $("#config-section").hidden = section !== "config";
  board.board.classList.toggle("keys", section === "config");

  syncControls();

  if (section === "config") {
    showConfig(config);
  } else {
    board.setDisabled([]);
    paintBoard();
  }
}

function changed() {
  syncControls();
  paintBoard();
  $("#apply").disabled = false;

  if ($("#auto-apply").checked) {
    clearTimeout(autoTimer);
    autoTimer = setTimeout(apply, 400);
  }
}

async function apply() {
  if (applying) {
    pendingApply = true;
    return;
  }

  applying = true;
  $("#apply").disabled = true;
  message("Applying…");

  try {
    await api("/api/state", { method: "PUT", body: JSON.stringify(state) });
    message(`Applied ${new Date().toLocaleTimeString()}`);
  } catch (error) {
    $("#apply").disabled = false;
    message(error.message, true);
  } finally {
    applying = false;

    if (pendingApply) {
      pendingApply = false;
      apply();
    }
  }
}

function bindControls() {
  const bottomRow = Math.max(...layout.keys.map((k) => k.y));
  const groups = {
    ...GROUPS,
    all: layout.keys.map((k) => k.name),
    top: layout.keys.filter((k) => k.y === 0).map((k) => k.name),
    bottom: layout.keys.filter((k) => k.y === bottomRow).map((k) => k.name),
  };

  bindHex();

  for (const button of document.querySelectorAll("[data-section]")) {
    button.addEventListener("click", () => showSection(button.dataset.section));
  }

  for (const tab of document.querySelectorAll("[data-config]")) {
    tab.addEventListener("click", () => showConfig(tab.dataset.config));
  }

  for (const tab of document.querySelectorAll(".tabs button[data-view]")) {
    tab.addEventListener("click", () => {
      if (tab.dataset.view !== view) board.select([]);

      view = tab.dataset.view;

      if (view === "screen") return syncControls();

      state.active = view;
      changed();
    });
  }

  for (const button of document.querySelectorAll("[data-select]")) {
    button.addEventListener("click", () => board.select(groups[button.dataset.select]));
  }

  for (const color of SWATCHES) {
    const swatch = document.createElement("button");
    swatch.className = "swatch";
    swatch.style.background = color;
    swatch.title = color;
    swatch.addEventListener("click", () => {
      $("#paint-color").value = color;
      syncHex();
    });
    $("#swatches").append(swatch);
  }

  $("#paint").addEventListener("click", () => {
    for (const name of board.selected) state.custom.keys[name] = $("#paint-color").value;

    changed();
  });

  $("#unpaint").addEventListener("click", () => {
    for (const name of board.selected) delete state.custom.keys[name];

    changed();
  });

  $("#base-color").addEventListener("input", (event) => {
    state.custom.base = event.target.value;
    changed();
  });

  const numeric = (id, target, field) => {
    $(id).addEventListener("input", (event) => {
      target()[field] = Number(event.target.value);
      changed();
    });
  };

  numeric("#custom-brightness", () => state.custom, "brightness");
  numeric("#effect-brightness", () => state.effect, "brightness");
  numeric("#effect-speed", () => state.effect, "speed");
  numeric("#effect-direction", () => state.effect, "direction");

  for (const mode of layout.modes) $("#effect-mode").append(new Option(mode, mode));

  $("#effect-mode").addEventListener("change", (event) => {
    state.effect.mode = event.target.value;
    changed();
  });

  $("#effect-color").addEventListener("input", (event) => {
    state.effect.color = event.target.value;
    changed();
  });

  $("#effect-rainbow").addEventListener("change", (event) => {
    state.effect.rainbow = event.target.checked;
    changed();
  });

  $("#apply").addEventListener("click", apply);

  $("#clock").addEventListener("click", async () => {
    try {
      await api("/api/clock", { method: "POST" });
      message("Clock synced");
    } catch (error) {
      message(error.message, true);
    }
  });
}

[layout, state] = await Promise.all([api("/api/layout"), api("/api/state")]);
view = state.active;

board = initBoard(layout);
keymap = initKeymap({ api, message, layout, board });
initScreen({ api, message });
initSettings({ api, message });
bindControls();
showSection(section);
refreshStatus();
setInterval(refreshStatus, 5000);
$("#apply").disabled = true;
