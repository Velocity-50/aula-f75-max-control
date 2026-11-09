export const MOD_LABELS = { ctrl: "Ctrl", shift: "Shift", alt: "Alt", win: "Win" };

const MODIFIER_OF_CODE = {
  ControlLeft: "ctrl",
  ControlRight: "ctrl",
  ShiftLeft: "shift",
  ShiftRight: "shift",
  AltLeft: "alt",
  AltRight: "alt",
  MetaLeft: "win",
  MetaRight: "win",
};

// modifiers held during a keydown, minus the one the pressed key itself is
export function heldMods(event) {
  const held = { ctrl: event.ctrlKey, shift: event.shiftKey, alt: event.altKey, win: event.metaKey };

  delete held[MODIFIER_OF_CODE[event.code]];

  return Object.keys(held).filter((mod) => held[mod]);
}

export function createKeyIndex(options) {
  const byCode = new Map(options.keys.map((key) => [key.code, key.name]));
  const labels = new Map(options.keys.map((key) => [key.name, key.label]));

  return {
    nameForCode: (code) => byCode.get(code),
    label: (name) => labels.get(name) ?? name.replaceAll("_", " "),
  };
}
