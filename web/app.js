const $ = (selector) => document.querySelector(selector);

const SWATCHES = ["#ffffff", "#ff0000", "#ff7a00", "#ffd400", "#00ff40", "#00ffff", "#0080ff", "#8000ff", "#ff00ff", "#ff1493"];
const GROUPS = {
  home: ["a", "s", "d", "f", "j", "k", "l", "semicolon"],
  arrows: ["up", "left", "down", "right"],
  wasd: ["w", "a", "s", "d"],
};

let layout;
let state;
let selected = new Set();
let keyElements = new Map();
let applying = false;
let pendingApply = false;
let autoTimer;

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "content-type": "application/json" }, ...options });
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail;
    throw new Error(detail ?? response.statusText);
  }

  return body;
}

function renderBoard() {
  const board = $("#board");
  const unit = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--unit"));
  const gap = 4;

  board.style.width = `${layout.width * unit}px`;
  board.style.height = `${layout.height * unit}px`;

  for (const key of layout.keys) {
    const el = document.createElement("div");
    el.className = "key";
    el.dataset.name = key.name;
    el.textContent = key.label;
    el.title = key.name;
    Object.assign(el.style, {
      left: `${key.x * unit}px`,
      top: `${key.y * unit}px`,
      width: `${key.w * unit - gap}px`,
      height: `${unit - gap}px`,
    });
    board.append(el);
    keyElements.set(key.name, el);
  }

  const knob = document.createElement("div");
  knob.className = "knob";
  knob.title = "knob (not configurable)";
  Object.assign(knob.style, {
    left: `${(layout.width - 1) * unit + 2}px`,
    top: "0px",
    width: `${unit - gap - 4}px`,
    height: `${unit - gap - 4}px`,
  });
  board.append(knob);

  let dragAdds = null;

  const keyAt = (event) => document.elementFromPoint(event.clientX, event.clientY)?.closest(".key");
  const mark = (el) => {
    dragAdds ? selected.add(el.dataset.name) : selected.delete(el.dataset.name);
    el.classList.toggle("selected", dragAdds);
  };

  board.addEventListener("pointerdown", (event) => {
    const el = keyAt(event);

    if (!el) return;

    dragAdds = !selected.has(el.dataset.name);
    mark(el);
  });

  window.addEventListener("pointermove", (event) => {
    if (dragAdds === null) return;

    const el = keyAt(event);

    if (el && board.contains(el)) mark(el);
  });

  window.addEventListener("pointerup", () => (dragAdds = null));
}

function select(names) {
  selected = new Set(names);

  for (const [name, el] of keyElements) el.classList.toggle("selected", selected.has(name));
}

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
    const el = keyElements.get(key.name);
    const color = keyColor(key);

    el.style.setProperty("--led", color);
    el.style.setProperty("--level", `${level}%`);
    el.classList.toggle("light", isLight(color, level));
  }
}

function syncControls() {
  const { custom, effect } = state;

  for (const tab of document.querySelectorAll(".tabs button")) {
    tab.classList.toggle("active", tab.dataset.mode === state.active);
  }

  $("#custom-panel").hidden = state.active !== "custom";
  $("#effect-panel").hidden = state.active !== "effect";

  $("#base-color").value = custom.base;
  $("#custom-brightness").value = custom.brightness;
  $("#custom-brightness-out").textContent = custom.brightness;

  $("#effect-mode").value = effect.mode;
  $("#effect-color").value = effect.color;
  $("#effect-color").disabled = effect.rainbow;
  $("#effect-rainbow").checked = effect.rainbow;
  $("#effect-brightness").value = effect.brightness;
  $("#effect-brightness-out").textContent = effect.brightness;
  $("#effect-speed").value = effect.speed;
  $("#effect-speed-out").textContent = effect.speed;
  $("#effect-direction").value = effect.direction;
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

function message(text, isError = false) {
  const el = $("#message");
  el.textContent = text;
  el.classList.toggle("error", isError);
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

async function refreshStatus() {
  const el = $("#status");

  try {
    const { connected } = await api("/api/status");
    el.textContent = connected ? "connected (USB)" : "not found: plug in USB, wired mode";
    el.className = `status ${connected ? "connected" : "disconnected"}`;
  } catch {
    el.textContent = "server offline";
    el.className = "status disconnected";
  }
}

function bindControls() {
  const bottomRow = Math.max(...layout.keys.map((k) => k.y));
  const groups = {
    ...GROUPS,
    all: layout.keys.map((k) => k.name),
    none: [],
    top: layout.keys.filter((k) => k.y === 0).map((k) => k.name),
    bottom: layout.keys.filter((k) => k.y === bottomRow).map((k) => k.name),
  };

  for (const tab of document.querySelectorAll(".tabs button")) {
    tab.addEventListener("click", () => {
      state.active = tab.dataset.mode;
      changed();
    });
  }

  for (const button of document.querySelectorAll("[data-select]")) {
    button.addEventListener("click", () => select(groups[button.dataset.select]));
  }

  for (const color of SWATCHES) {
    const swatch = document.createElement("button");
    swatch.className = "swatch";
    swatch.style.background = color;
    swatch.title = color;
    swatch.addEventListener("click", () => ($("#paint-color").value = color));
    $("#swatches").append(swatch);
  }

  $("#paint").addEventListener("click", () => {
    for (const name of selected) state.custom.keys[name] = $("#paint-color").value;

    changed();
  });

  $("#unpaint").addEventListener("click", () => {
    for (const name of selected) delete state.custom.keys[name];

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

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") select([]);
  });
}

[layout, state] = await Promise.all([api("/api/layout"), api("/api/state")]);

renderBoard();
bindControls();
syncControls();
paintBoard();
refreshStatus();
setInterval(refreshStatus, 5000);
$("#apply").disabled = true;
