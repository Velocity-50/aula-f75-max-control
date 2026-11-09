const $ = (selector) => document.querySelector(selector);

export async function api(path, options = {}) {
  const headers = typeof options.body === "string" ? { "content-type": "application/json" } : {};
  const response = await fetch(path, { headers, ...options });
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail;
    throw new Error(detail ?? response.statusText);
  }

  return body;
}

export function message(text, isError = false) {
  const el = $("#message");
  el.textContent = text;
  el.classList.toggle("error", isError);
}

export async function refreshStatus() {
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
