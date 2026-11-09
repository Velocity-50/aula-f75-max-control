function parseHex(text) {
  let hex = text.trim().replace(/^#/, "").toLowerCase();

  if (/^[0-9a-f]{3}$/.test(hex)) hex = [...hex].map((c) => c + c).join("");

  return /^[0-9a-f]{6}$/.test(hex) ? `#${hex}` : null;
}

// copies picker values into their hex fields, leaving the one being typed in alone
export function syncHex() {
  for (const field of document.querySelectorAll(".hex")) {
    if (field === document.activeElement) continue;

    field.value = document.getElementById(field.dataset.for).value;
    field.classList.remove("invalid");
  }
}

export function bindHex() {
  for (const field of document.querySelectorAll(".hex")) {
    const picker = document.getElementById(field.dataset.for);

    picker.addEventListener("input", syncHex);

    field.addEventListener("input", () => {
      const hex = parseHex(field.value);

      field.classList.toggle("invalid", hex === null);

      if (hex === null || hex === picker.value) return;

      picker.value = hex;
      picker.dispatchEvent(new Event("input"));
    });

    field.addEventListener("blur", syncHex);
    field.addEventListener("keydown", (event) => {
      if (event.key === "Enter") field.blur();
    });
  }
}
