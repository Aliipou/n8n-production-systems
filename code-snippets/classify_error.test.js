import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  BASE_DELAY_S,
  CAP_DELAY_S,
  MAX_ATTEMPTS,
  classify_error,
  compute_next_delay,
} from "./classify_error.js";

const fixture = JSON.parse(
  readFileSync(join(import.meta.dirname, "..", "platform", "libs", "fixtures", "error_cases.json"), "utf8"),
);

function lcg(seed) {
  let state = seed >>> 0;
  return function jitter() {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

describe("classify_error fixture", () => {
  it("matches every shared case", () => {
    for (const testCase of fixture.cases) {
      expect(classify_error(testCase.input), testCase.id).toEqual(testCase.expected);
    }
  });
});

describe("classify_error extras", () => {
  it("treats null input as unknown", () => {
    expect(classify_error(null)).toEqual({
      class: "unknown",
      retry: false,
      idempotent_success: false,
    });
  });

  it("accepts idempotentCreate camelCase for 409 success", () => {
    expect(classify_error({ status: 409, idempotentCreate: true })).toEqual({
      class: "success",
      retry: false,
      idempotent_success: true,
    });
  });
});

describe("compute_next_delay", () => {
  it("uses documented backoff constants", () => {
    expect(MAX_ATTEMPTS).toBe(fixture.backoff.max_attempts);
    expect(BASE_DELAY_S).toBe(fixture.backoff.base_s);
    expect(CAP_DELAY_S).toBe(fixture.backoff.cap_s);
  });

  it("matches shared full-jitter ceilings with jitter 1", () => {
    for (const row of fixture.delay_ceilings) {
      expect(compute_next_delay(row.attempt, BASE_DELAY_S, CAP_DELAY_S, () => 1)).toBe(row.ceiling);
    }
  });

  it("returns 0 when jitter is 0", () => {
    expect(compute_next_delay(4, 2, 300, () => 0)).toBe(0);
  });

  it("scales with a half jitter function", () => {
    expect(compute_next_delay(2, 2, 300, () => 0.5)).toBe(4);
  });

  it("is deterministic with a seeded jitter function", () => {
    const a = compute_next_delay(3, 2, 300, lcg(1));
    const b = compute_next_delay(3, 2, 300, lcg(1));
    const c = compute_next_delay(3, 2, 300, lcg(2));
    expect(a).toBe(b);
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThanOrEqual(16);
    expect(c).not.toBe(a);
  });

  it("defaults base and cap", () => {
    expect(compute_next_delay(0, undefined, undefined, () => 1)).toBe(2);
  });
});
