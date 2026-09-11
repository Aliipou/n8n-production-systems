// snippet: classify_error
// Taxonomy (spec 00 section 4): transient, rate_limited, invalid_data, auth,
// permanent, unknown. HTTP 409 on an idempotent create is class success with
// idempotent_success true (not an error).
// Backoff: full jitter, delay_s = jitter_fn() * min(cap, base * 2^attempt).
// attempt is 0-based. Defaults: base 2 s, cap 300 s, max 6 attempts.
// n8n Code node (Run Once for Each Item):
// return { json: Object.assign({}, $json, classify_error($json)) };

const MAX_ATTEMPTS = 6;
const BASE_DELAY_S = 2;
const CAP_DELAY_S = 300;

const TRANSIENT_STATUS = { 500: 1, 502: 1, 503: 1, 504: 1 };
const RATE_LIMIT_STATUS = { 429: 1 };
const INVALID_STATUS = { 400: 1, 422: 1 };
const AUTH_STATUS = { 401: 1, 403: 1 };
const PERMANENT_STATUS = { 404: 1, 410: 1, 501: 1, 409: 1 };

const TRANSIENT_CODES = {
  etimedout: 1,
  esockettimedout: 1,
  econnreset: 1,
  econnrefused: 1,
  econnaborted: 1,
  epipe: 1,
  eai_again: 1,
  enotfound: 1,
  eai_noname: 1,
  und_err_connect_timeout: 1,
  und_err_headers_timeout: 1,
  und_err_body_timeout: 1,
  timeout: 1,
  timeouterror: 1,
};

const TRANSIENT_MARKERS = [
  "timed out",
  "timeout",
  "deadline exceeded",
  "connection reset",
  "connection refused",
  "socket hang up",
  "econnreset",
  "econnrefused",
  "eai_again",
  "enotfound",
  "temporary failure in name resolution",
  "getaddrinfo",
];

const RATE_LIMIT_MARKERS = [
  "rate_limit",
  "ratelimit",
  "too many requests",
  "too_many_requests",
  "throttl",
  "resource_exhausted",
];

const INVALID_MARKERS = [
  "schema validation",
  "validation error",
  "validation failed",
  "json schema",
  "schema_validation",
  "validation_error",
  "pydantic",
];

function classify_error(input) {
  const parsed = parseInput(input);
  if (parsed.status === 409 && parsed.idempotentCreate) {
    return result("success", false, true);
  }
  if (TRANSIENT_STATUS[parsed.status]) return result("transient", true, false);
  if (RATE_LIMIT_STATUS[parsed.status]) return result("rate_limited", true, false);
  if (INVALID_STATUS[parsed.status]) return result("invalid_data", false, false);
  if (AUTH_STATUS[parsed.status]) return result("auth", false, false);
  if (PERMANENT_STATUS[parsed.status]) return result("permanent", false, false);
  if (isTransient(parsed.code, parsed.blob)) return result("transient", true, false);
  if (hasMarker(parsed.blob, RATE_LIMIT_MARKERS)) return result("rate_limited", true, false);
  if (hasMarker(parsed.blob, INVALID_MARKERS)) return result("invalid_data", false, false);
  return result("unknown", false, false);
}

function compute_next_delay(attempt, base, cap, jitter_fn) {
  const exp = toAttempt(attempt);
  const b = base == null ? BASE_DELAY_S : Number(base);
  const c = cap == null ? CAP_DELAY_S : Number(cap);
  const jitter = jitter_fn == null ? Math.random : jitter_fn;
  return jitter() * Math.min(c, b * Math.pow(2, exp));
}

function result(cls, retry, idempotentSuccess) {
  return { class: cls, retry: retry, idempotent_success: idempotentSuccess };
}

function parseInput(input) {
  const src = input && typeof input === "object" ? input : {};
  const nested = src.error && typeof src.error === "object" ? src.error : {};
  const status = firstStatus(src, nested);
  const code = normCode(firstText(src, nested, ["code", "errno", "errorCode", "error_code"]));
  const message = firstText(src, nested, ["message", "description"]).toLowerCase();
  const errorText = typeof src.error === "string" ? src.error.toLowerCase() : "";
  const blob = (code + " " + message + " " + errorText).replace(/-/g, "_");
  const idempotentCreate =
    src.idempotent_create === true ||
    src.idempotentCreate === true ||
    nested.idempotent_create === true ||
    nested.idempotentCreate === true;
  return { status: status, code: code, blob: blob, idempotentCreate: idempotentCreate };
}

function firstStatus(src, nested) {
  const keys = ["status", "statusCode", "httpCode", "status_code", "http_code"];
  for (let i = 0; i < keys.length; i++) {
    const n = toStatus(src[keys[i]]);
    if (n != null) return n;
    const m = toStatus(nested[keys[i]]);
    if (m != null) return m;
  }
  const msg = String(src.message || nested.message || src.error || "");
  const hit = /status code (\d{3})/i.exec(msg) || /\bHTTP[ /](\d{3})\b/i.exec(msg);
  return hit ? toStatus(hit[1]) : null;
}

function firstText(src, nested, keys) {
  for (let i = 0; i < keys.length; i++) {
    if (typeof src[keys[i]] === "string" && src[keys[i]]) return src[keys[i]];
    if (typeof nested[keys[i]] === "string" && nested[keys[i]]) return nested[keys[i]];
  }
  return "";
}

function toStatus(value) {
  if (value == null || typeof value === "boolean") return null;
  const n = typeof value === "number" ? value : Number(String(value).trim());
  if (!Number.isInteger(n) || n < 100 || n > 599) return null;
  return n;
}

function toAttempt(attempt) {
  const n = Number(attempt);
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.floor(n);
}

function normCode(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/-/g, "_");
}

function isTransient(code, blob) {
  if (TRANSIENT_CODES[code]) return true;
  return hasMarker(blob, TRANSIENT_MARKERS);
}

function hasMarker(blob, markers) {
  for (let i = 0; i < markers.length; i++) {
    if (blob.indexOf(markers[i]) !== -1) return true;
  }
  return false;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    classify_error: classify_error,
    compute_next_delay: compute_next_delay,
    MAX_ATTEMPTS: MAX_ATTEMPTS,
    BASE_DELAY_S: BASE_DELAY_S,
    CAP_DELAY_S: CAP_DELAY_S,
  };
}
