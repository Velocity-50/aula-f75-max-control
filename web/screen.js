const $ = (selector) => document.querySelector(selector);

export function initScreen({ api, message }) {
  let file = null;
  let lastState = null;

  const fitQuery = () => `fit=${encodeURIComponent($("#screen-fit").value)}`;

  async function preview() {
    if (!file) return;

    $("#screen-info").textContent = "Converting…";
    $("#screen-upload").disabled = true;

    try {
      const result = await api(`/api/screen/preview?${fitQuery()}`, { method: "POST", body: file });
      const img = $("#screen-preview");

      img.src = result.image;
      img.hidden = false;
      $("#screen-info").textContent =
        `${result.frames} frame${result.frames === 1 ? "" : "s"} · ${(result.duration_ms / 1000).toFixed(1)} s loop · ` +
        `upload takes about ${result.upload_seconds} s`;
      $("#screen-upload").disabled = lastState === "uploading";
    } catch (error) {
      $("#screen-info").textContent = error.message;
    }
  }

  function choose(chosen) {
    if (!chosen) return;

    file = chosen;
    $("#screen-drop-text").textContent = chosen.name;
    preview();
  }

  function refreshCurrent() {
    const img = $("#screen-current");

    img.onload = () => (img.hidden = false);
    img.onerror = () => (img.hidden = true);
    img.src = `/api/screen/current?t=${Date.now()}`;
  }

  function render(status) {
    const uploading = status.state === "uploading";
    const progress = $("#screen-progress");

    progress.hidden = !uploading;
    progress.value = status.total ? status.done / status.total : 0;
    $("#screen-upload").disabled = uploading || !file;
    $("#screen-resend").disabled = uploading || !status.saved;

    const text = $("#screen-status");
    text.classList.remove("error");

    if (uploading) {
      text.textContent = `Uploading… ${status.done} of ${status.total} chunks`;
    } else if (status.state === "error" && lastState === "uploading") {
      text.textContent = status.error;
      text.classList.add("error");
    } else if (status.state === "done" && lastState === "uploading") {
      text.textContent = `Uploaded ${status.frames} frame${status.frames === 1 ? "" : "s"}`;
      message("Screen updated");
      refreshCurrent();
    }

    lastState = status.state;
  }

  async function poll() {
    try {
      const status = await api("/api/screen");
      render(status);

      if (status.state === "uploading") setTimeout(poll, 500);
    } catch (error) {
      message(error.message, true);
    }
  }

  async function upload(path, options) {
    $("#screen-upload").disabled = true;
    $("#screen-resend").disabled = true;

    try {
      render(await api(path, options));
      setTimeout(poll, 500);
    } catch (error) {
      poll();
      message(error.message, true);
    }
  }

  const drop = $("#screen-drop");

  $("#screen-file").addEventListener("change", (event) => choose(event.target.files[0]));
  $("#screen-fit").addEventListener("change", preview);
  $("#screen-upload").addEventListener("click", () => upload(`/api/screen?${fitQuery()}`, { method: "POST", body: file }));
  $("#screen-resend").addEventListener("click", () => upload("/api/screen/resend", { method: "POST" }));

  drop.addEventListener("dragover", (event) => {
    event.preventDefault();
    drop.classList.add("over");
  });

  drop.addEventListener("dragleave", () => drop.classList.remove("over"));

  drop.addEventListener("drop", (event) => {
    event.preventDefault();
    drop.classList.remove("over");
    choose(event.dataTransfer.files[0]);
  });

  refreshCurrent();
  poll();
}
