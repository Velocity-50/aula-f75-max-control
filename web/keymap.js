import { initMacros } from "./macros.js";
import { MOD_LABELS, createKeyIndex, heldMods } from "./options.js";

const $ = (selector) => document.querySelector(selector);

export function initKeymap({ api, message, layout, board }) {
  const keymap = { base: {}, fn: {}, macros: [] };
  let options;
  let index;
  let macros;
  let saved = "";
  let layer = "base";
  let applying = false;
  let capturing = false;

  const visible = () => !$("#config-section").hidden && !$("#keymap-panel").hidden;
  const dirty = () => JSON.stringify(keymap) !== saved;
  const pick = (list, name) => list.find((item) => item.name === name)?.label ?? name;

  function describe(action) {
    if (action.kind === "key") return [...action.mods.map((m) => MOD_LABELS[m]), index.label(action.key)].join("+");
    if (action.kind === "media") return pick(options.media, action.media);
    if (action.kind === "macro") return `Macro ${action.macro + 1}`;

    return "Off";
  }

  function paint() {
    for (const key of layout.keys) {
      const el = board.elements.get(key.name);
      const action = keymap[layer][key.name];

      el.querySelector(".caption").textContent = action ? describe(action) : "";
      el.classList.toggle("remapped", Boolean(action));
    }
  }

  function syncButtons() {
    $("#keys-apply").disabled = applying || !dirty();
    $("#keys-reset").disabled = Object.keys(keymap[layer]).length === 0;
    $("#assign").disabled = board.selected.size === 0;
  }

  function refreshMacroSelect() {
    const select = $("#action-macro");
    const previous = select.value;

    select.replaceChildren(...keymap.macros.map((m, i) => new Option(`${i + 1} · ${m.name || "Unnamed"}`, i)));

    if (keymap.macros.length === 0) select.append(new Option("No macros yet", ""));
    else select.value = previous && previous < keymap.macros.length ? previous : 0;
  }

  function changed() {
    refreshMacroSelect();
    paint();
    syncButtons();
  }

  function showKind() {
    for (const panel of document.querySelectorAll("[data-kind-panel]")) {
      panel.hidden = panel.dataset.kindPanel !== $("#action-kind").value;
    }
  }

  function loadAction(action) {
    const kind = action?.kind ?? "default";
    const mods = action?.mods ?? [];

    $("#action-kind").value = kind;

    if (kind === "key") $("#action-key").value = action.key;
    if (kind === "media") $("#action-media").value = action.media;

    if (kind === "macro") {
      $("#action-macro").value = action.macro;
      $("#action-mode").value = action.mode;
      $("#action-count").value = action.count;
    }

    for (const box of document.querySelectorAll("[data-mod]")) box.checked = mods.includes(box.dataset.mod);

    showKind();
  }

  function readAction() {
    const kind = $("#action-kind").value;

    if (kind === "key") {
      const mods = [...document.querySelectorAll("[data-mod]")].filter((b) => b.checked).map((b) => b.dataset.mod);

      return { kind, key: $("#action-key").value, mods };
    }

    if (kind === "media") return { kind, media: $("#action-media").value };
    if (kind === "disable") return { kind };

    if (kind === "macro") {
      const count = Math.min(255, Math.max(1, Math.round(Number($("#action-count").value)) || 1));

      return { kind, macro: Number($("#action-macro").value), mode: $("#action-mode").value, count };
    }

    return null;
  }

  function syncSelection() {
    if (!visible()) return;

    const names = [...board.selected];

    $("#keys-selection").textContent = names.length
      ? `Pick an action for the ${layer === "fn" ? "Fn" : "base"} layer`
      : "Select keys on the board";

    if (names.length) loadAction(keymap[layer][names[0]]);

    syncButtons();
  }

  function assign() {
    const action = readAction();

    if (action?.kind === "macro" && keymap.macros.length === 0) return message("Add a macro first", true);

    for (const name of board.selected) {
      if (action) keymap[layer][name] = { ...action };
      else delete keymap[layer][name];
    }

    changed();
    message("Assigned. Apply to write it to the keyboard");
  }

  function stopCapture() {
    capturing = false;
    window.removeEventListener("keydown", onCapture, true);
    $("#capture").textContent = "Press a key";
  }

  function onCapture(event) {
    event.preventDefault();
    event.stopPropagation();
    stopCapture();

    if (event.code === "Escape") return;

    const name = index.nameForCode(event.code);

    if (!name) return message(`${event.code} can't be assigned`, true);

    const mods = heldMods(event);

    $("#action-kind").value = "key";
    $("#action-key").value = name;

    for (const box of document.querySelectorAll("[data-mod]")) box.checked = mods.includes(box.dataset.mod);

    showKind();
  }

  function toggleCapture() {
    if (capturing) return stopCapture();

    capturing = true;
    $("#capture").textContent = "Press a key… (Esc cancels)";
    window.addEventListener("keydown", onCapture, true);
  }

  function replace(next) {
    Object.assign(keymap, { base: next.base ?? {}, fn: next.fn ?? {}, macros: next.macros ?? [] });
    saved = JSON.stringify(keymap);
  }

  async function apply() {
    const used = macros.budgetUsed();

    if (used > options.macro_budget) {
      return message(`Macros use ${used} of ${options.macro_budget} bytes: remove some events or macros`, true);
    }

    applying = true;
    syncButtons();
    message("Writing to the keyboard…");

    try {
      replace(await api("/api/keymap", { method: "PUT", body: JSON.stringify(keymap) }));
      macros.render();
      message(`Applied ${new Date().toLocaleTimeString()}`);
    } catch (error) {
      message(error.message, true);
    } finally {
      applying = false;
      changed();
    }
  }

  function buildEditor() {
    const fill = (id, items) => $(id).append(...items.map(({ name, label }) => new Option(label, name)));

    fill("#action-key", options.keys);
    fill("#action-media", options.media);
    fill("#action-mode", options.macro_modes.map((name) => ({ name, label: name })));

    for (const mod of options.mods) {
      const label = document.createElement("label");
      const box = document.createElement("input");

      box.type = "checkbox";
      box.dataset.mod = mod;
      label.className = "inline";
      label.append(box, ` ${MOD_LABELS[mod]}`);
      $("#action-mods").append(label);
    }
  }

  function bind() {
    $("#action-kind").addEventListener("change", showKind);
    $("#capture").addEventListener("click", toggleCapture);
    $("#assign").addEventListener("click", assign);
    $("#keys-apply").addEventListener("click", apply);
    $("#keys-reset").addEventListener("click", () => {
      const name = layer === "fn" ? "Fn" : "base";

      if (!confirm(`Reset every key on the ${name} layer to its factory action and write it to the keyboard?`)) return;

      keymap[layer] = {};
      apply();
    });

    board.onSelect(syncSelection);
  }

  async function load() {
    try {
      const [loaded, stored] = await Promise.all([api("/api/keymap/options"), api("/api/keymap")]);

      options = loaded;
      replace(stored);
    } catch (error) {
      return message(`Couldn't load key assignments: ${error.message}`, true);
    }

    index = createKeyIndex(options);
    macros = initMacros({ options, index, keymap, message, changed });
    buildEditor();
    bind();
    macros.render();
    refreshMacroSelect();
    showKind();
    if (visible()) show();
  }

  function show(next = layer) {
    layer = next;

    if (!options) return;

    board.setDisabled(options.reserved[layer]);
    paint();
    syncSelection();
    syncButtons();
  }

  load();

  return { show };
}
