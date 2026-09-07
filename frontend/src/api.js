// During local development Vite proxies /api to FastAPI. This avoids a
// browser-to-database shortcut and guarantees all UI data goes through the
// authenticated backend; deployments can set VITE_API_URL explicitly.
const API_BASE = import.meta.env.VITE_API_URL || "/api";

export async function apiRequest(endpoint, options = {}, token = null) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    const message = error.name === "AbortError"
      ? `Request to ${API_BASE}${endpoint} timed out`
      : `Unable to reach the clinical API at ${API_BASE}: ${error.message}`;
    console.error(message, error);
    throw new Error(message);
  } finally {
    window.clearTimeout(timeout);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.detail || `Request failed (${response.status})`;
    console.error(`Clinical API error for ${endpoint}:`, message);
    throw new Error(message);
  }
  return data;
}

export async function downloadPdfReport(endpoint, defaultFilename = "medical_report.pdf", token = null) {
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to download medical PDF report");
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = defaultFilename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}
