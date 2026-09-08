// During local development Vite proxies /api to FastAPI. This avoids a
// browser-to-database shortcut and guarantees all UI data goes through the
// authenticated backend; deployments can set VITE_API_URL explicitly.
const API_BASE = import.meta.env.VITE_API_URL || "/api";

// Friendly error messages for common HTTP status codes — no raw stack traces
// shown to users. Technical detail stays in the console for debugging.
const FRIENDLY_ERRORS = {
  400: "Invalid request. Please check your input and try again.",
  401: "Your session has expired. Please sign in again.",
  403: "You don't have permission to perform this action.",
  404: "The requested resource was not found.",
  409: "This conflicts with existing data. Please refresh and try again.",
  413: "The file you're uploading is too large.",
  422: "Some fields have invalid values. Please review and correct them.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "Something went wrong on our end. Please try again later.",
  502: "The server is temporarily unavailable. Please try again shortly.",
  503: "Maintenance in progress. Please try again in a few minutes.",
};

function getFriendlyMessage(status, serverDetail) {
  if (serverDetail && status >= 400 && status < 500) {
    return serverDetail;
  }
  return FRIENDLY_ERRORS[status] || `Something unexpected happened (error ${status}).`;
}

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
      ? "The request timed out. Please check your connection and try again."
      : "Unable to reach the server. Please check your network connection.";
    console.error(`API request failed for ${endpoint}:`, error);
    throw new Error(message);
  } finally {
    window.clearTimeout(timeout);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = getFriendlyMessage(response.status, data.detail);
    console.error(`API error ${response.status} for ${endpoint}:`, data.detail || message);
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
