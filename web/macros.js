const $ = (selector) => document.querySelector(selector);

const clampDelay = (ms) => Math.min(65535, Math.max(10, Math.round(ms) || 10));

export function initMacros({ options, index, keymap, message, changed }) {
  let current = 0;
  let recording = null;

  const macro = () => keymap.macros[current];
  const budgetUsed = () => (keymap.macros.length + keymap.macros.reduce((sum, m) => sum + m.events.length, 0)) * 8;

  const keySelect = document.createElement("select");

  for (const key of options.keys) keySelect.append(new Option(key.label, key.name));

  for (const button of options.macro_buttons) keySelect.append(new Option(`Mouse ${button.replace("mouse_", "")}`, button));

  const optionLabel = (m, i) => `${i + 1} · ${m.name || "Unnamed"}`;

  function renderBudget() {
    const used = budgetUsed();
    const el = $("#macro-budget");

    el.textContent =
      `Macro memory ${used} of ${options.macro_budget} bytes · ${keymap.macros.length} of ${options.macro_slots} macros`;
    el.classList.toggle("error", used > options.macro_budget);
  }

  function renderEvents() {
    const container = $("#macro-events");

    container.replaceChildren();

    macro()?.events.forEach((event, i) => {
      const row = document.createElement("div");
      const key = keySelect.cloneNode(true);
      const down = document.createElement("select");
      const delay = document.createElement("input");
      const remove = document.createElement("button");

      row.className = "event";
      row.dataset.index = i;
      key.dataset.field = "key";
      key.value = event.key;
      down.dataset.field = "down";
      down.append(new Option("Press", "down"), new Option("Release", "up"));
      down.value = event.down ? "down" : "up";
      delay.dataset.field = "delay";
      Object.assign(delay, { type: "number", min: 10, max: 65535, value: event.delay, title: "Delay after this event (ms)" });
      remove.dataset.action = "delete";
      remove.textContent = "×";
      remove.title = "Delete event";
      row.append(key, down, delay, remove);
      container.append(row);
    });
  }

  function render() {
    const list = $("#macro-list");

    current = Math.max(0, Math.min(current, keymap.macros.length - 1));
    list.replaceChildren(...keymap.macros.map((m, i) => new Option(optionLabel(m, i), i)));
    list.value = current;
    list.disabled = !macro();
    $("#macro-delete").disabled = !macro();
    $("#macro-editor").hidden = !macro();
    $("#macro-name").value = macro()?.name ?? "";
    renderEvents();
    renderBudget();
  }

  function addEvents(events) {
    macro().events.push(...events);
    renderEvents();
    renderBudget();
    changed();
  }

  function stopRecording() {
    if (!recording) return;

    const { log, held } = recording;

    recording = null;
    window.removeEventListener("keydown", onRecord, true);
    window.removeEventListener("keyup", onRecord, true);
    $("#macro-record").textContent = "Record";
    $("#macro-record").classList.remove("recording");

    const end = performance.now();

    for (const key of held) log.push({ key, down: false, t: end });

    addEvents(log.map((e, i) => ({
      key: e.key,
      down: e.down,
      delay: i + 1 < log.length ? clampDelay(log[i + 1].t - e.t) : 10,
    })));
    message(`Recorded ${log.length} event${log.length === 1 ? "" : "s"}`);
  }

  function onRecord(event) {
    event.preventDefault();
    event.stopPropagation();

    const key = index.nameForCode(event.code);
    const down = event.type === "keydown";

    if (event.repeat || !key || (!down && !recording.held.has(key))) return;

    recording.held[down ? "add" : "delete"](key);
    recording.log.push({ key, down, t: event.timeStamp });
  }

  function startRecording() {
    recording = { log: [], held: new Set() };
    window.addEventListener("keydown", onRecord, true);
    window.addEventListener("keyup", onRecord, true);
    $("#macro-record").textContent = "Stop";
    $("#macro-record").classList.add("recording");
    message("Recording: press keys, then Stop");
  }

  function deleteMacro() {
    const doomed = current;
    let removed = 0;

    stopRecording();

    for (const layer of [keymap.base, keymap.fn]) {
      for (const [key, action] of Object.entries(layer)) {
        if (action.kind !== "macro") continue;

        if (action.macro === doomed) {
          delete layer[key];
          removed++;
        } else if (action.macro > doomed) {
          action.macro--;
        }
      }
    }

    keymap.macros.splice(doomed, 1);
    render();
    changed();
    message(`Macro deleted${removed ? ` · removed ${removed} binding${removed === 1 ? "" : "s"} that played it` : ""}`);
  }

  $("#macro-list").addEventListener("change", (event) => {
    stopRecording();
    current = Number(event.target.value);
    render();
  });

  $("#macro-add").addEventListener("click", () => {
    if (keymap.macros.length >= options.macro_slots) return message(`Only ${options.macro_slots} macros fit`, true);

    stopRecording();
    keymap.macros.push({ name: `Macro ${keymap.macros.length + 1}`, events: [] });
    current = keymap.macros.length - 1;
    render();
    changed();
  });

  $("#macro-delete").addEventListener("click", deleteMacro);

  $("#macro-name").addEventListener("input", (event) => {
    macro().name = event.target.value;
    $("#macro-list").selectedOptions[0].textContent = optionLabel(macro(), current);
    changed();
  });

  $("#macro-add-event").addEventListener("click", () => {
    addEvents([{ key: options.keys.find((k) => k.name === "a")?.name ?? options.keys[0].name, down: true, delay: 10 }]);
  });

  $("#macro-add-click").addEventListener("click", () => {
    const button = options.macro_buttons[0];

    addEvents([{ key: button, down: true, delay: 50 }, { key: button, down: false, delay: 10 }]);
  });

  $("#macro-clear").addEventListener("click", () => {
    stopRecording();
    macro().events = [];
    renderEvents();
    renderBudget();
    changed();
  });

  $("#macro-record").addEventListener("click", () => (recording ? stopRecording() : startRecording()));

  $("#macro-events").addEventListener("change", (event) => {
    const row = event.target.closest("[data-index]");
    const field = event.target.dataset.field;

    if (!row || !field) return;

    const target = macro().events[Number(row.dataset.index)];

    if (field === "key") target.key = event.target.value;
    if (field === "down") target.down = event.target.value === "down";
    if (field === "delay") {
      target.delay = clampDelay(Number(event.target.value));
      event.target.value = target.delay;
    }

    changed();
  });

  $("#macro-events").addEventListener("click", (event) => {
    const row = event.target.closest("[data-index]");

    if (!row || event.target.dataset.action !== "delete") return;

    macro().events.splice(Number(row.dataset.index), 1);
    renderEvents();
    renderBudget();
    changed();
  });

  return { render, budgetUsed };
}
