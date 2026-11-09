const $ = (selector) => document.querySelector(selector);

export function initBoard(layout) {
  const board = $("#board");
  const unit = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--unit"));
  const gap = 4;
  const elements = new Map();
  const selected = new Set();
  const disabled = new Set();
  const listeners = [];

  board.style.width = `${layout.width * unit}px`;
  board.style.height = `${layout.height * unit}px`;

  for (const key of layout.keys) {
    const el = document.createElement("div");
    const label = document.createElement("span");
    const caption = document.createElement("span");

    el.className = "key";
    el.dataset.name = key.name;
    el.title = key.name;
    label.textContent = key.label;
    label.className = "label";
    caption.className = "caption";
    el.append(label, caption);
    Object.assign(el.style, {
      left: `${key.x * unit}px`,
      top: `${key.y * unit}px`,
      width: `${key.w * unit - gap}px`,
      height: `${unit - gap}px`,
    });
    board.append(el);
    elements.set(key.name, el);
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

  const notify = () => listeners.forEach((listener) => listener());
  const hint = $("#selection").textContent;

  function showSelection() {
    const labels = layout.keys.filter((key) => selected.has(key.name)).map((key) => key.label || key.name);

    $("#selection").textContent = labels.length ? `Selected: ${labels.join(", ")}` : hint;
    $("#select-none").disabled = labels.length === 0;
  }

  listeners.push(showSelection);
  $("#select-none").addEventListener("click", () => select([]));

  function select(names) {
    selected.clear();

    for (const name of names) if (!disabled.has(name)) selected.add(name);

    for (const [name, el] of elements) el.classList.toggle("selected", selected.has(name));

    notify();
  }

  function setDisabled(names) {
    disabled.clear();

    for (const name of names) disabled.add(name);

    for (const [name, el] of elements) el.classList.toggle("disabled", disabled.has(name));

    select([...selected]);
  }

  let dragAdds = null;

  const keyAt = (event) => document.elementFromPoint(event.clientX, event.clientY)?.closest(".key");
  const mark = (el) => {
    const name = el.dataset.name;

    if (disabled.has(name)) return;

    dragAdds ? selected.add(name) : selected.delete(name);
    el.classList.toggle("selected", dragAdds);
    notify();
  };

  board.addEventListener("pointerdown", (event) => {
    const el = keyAt(event);

    if (!el || disabled.has(el.dataset.name)) return;

    dragAdds = !selected.has(el.dataset.name);
    mark(el);
  });

  window.addEventListener("pointermove", (event) => {
    if (dragAdds === null) return;

    const el = keyAt(event);

    if (el && board.contains(el)) mark(el);
  });

  window.addEventListener("pointerup", () => (dragAdds = null));

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") select([]);
  });

  return { board, elements, selected, select, setDisabled, onSelect: (listener) => listeners.push(listener) };
}
