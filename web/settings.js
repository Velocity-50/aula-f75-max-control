const $ = (selector) => document.querySelector(selector);

export function initSettings({ api, message }) {
  const fields = document.querySelectorAll("[data-setting]");
  const button = $("#settings-apply");
  let settings;

  function sync() {
    for (const el of fields) {
      const value = settings[el.dataset.setting];

      if (el.type === "checkbox") el.checked = value;
      else el.value = value;
    }

    $("#settings-response-out").textContent = settings.response;
  }

  async function apply() {
    button.disabled = true;
    message("Writing to the keyboard…");

    try {
      settings = await api("/api/settings", { method: "PUT", body: JSON.stringify(settings) });
      message(`Applied ${new Date().toLocaleTimeString()}`);
    } catch (error) {
      message(error.message, true);
    } finally {
      button.disabled = false;
      sync();
    }
  }

  async function load() {
    try {
      settings = await api("/api/settings");
    } catch (error) {
      return message(`Couldn't load settings: ${error.message}`, true);
    }

    for (const el of fields) {
      el.addEventListener(el.type === "checkbox" ? "change" : "input", () => {
        settings[el.dataset.setting] = el.type === "checkbox" ? el.checked : Number(el.value);
        sync();
      });
    }

    button.addEventListener("click", apply);
    button.disabled = false;
    sync();
  }

  button.disabled = true;
  load();
}
