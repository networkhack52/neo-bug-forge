/**
 * Unit tests for the Neo Bug Forge web API client.
 * global fetch is stubbed so no real network calls are made.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { callBugFix } from "./api";

function mockFetch(response) {
  const fn = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fn);
  return fn;
}

function jsonResponse({ ok = true, status = 200, body = {} }) {
  return { ok, status, json: () => Promise.resolve(body) };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("callBugFix", () => {
  it("posts code/error/language to the public fix endpoint", async () => {
    const fetchFn = mockFetch(jsonResponse({ body: { fixed_code: "x = 1" } }));

    await callBugFix("x=1/0", "ZeroDivisionError", "python");

    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchFn.mock.calls[0];
    expect(url).toMatch(/\/v1\/fix\/public$/);
    expect(opts.method).toBe("POST");
    expect(opts.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(opts.body)).toEqual({
      broken_code: "x=1/0",
      error_message: "ZeroDivisionError",
      language: "python",
    });
  });

  it("returns the parsed JSON body on success", async () => {
    mockFetch(jsonResponse({ body: { fixed_code: "fixed", confidence: 88 } }));
    const result = await callBugFix("code", "err", "js");
    expect(result).toEqual({ fixed_code: "fixed", confidence: 88 });
  });

  it("throws a friendly quota message on HTTP 429", async () => {
    mockFetch(jsonResponse({ ok: false, status: 429, body: {} }));
    await expect(callBugFix("code", "err", "python")).rejects.toThrow(
      /Daily free limit reached/
    );
  });

  it("surfaces the server's detail message on other errors", async () => {
    mockFetch(jsonResponse({ ok: false, status: 422, body: { detail: "broken_code must not be blank" } }));
    await expect(callBugFix("", "err", "python")).rejects.toThrow(
      "broken_code must not be blank"
    );
  });

  it("falls back to a generic error when the body has no detail", async () => {
    mockFetch(jsonResponse({ ok: false, status: 500, body: {} }));
    await expect(callBugFix("code", "err", "python")).rejects.toThrow(
      "API error 500"
    );
  });

  it("does not throw if the error body is not valid JSON", async () => {
    const badBody = {
      ok: false,
      status: 503,
      json: () => Promise.reject(new Error("not json")),
    };
    mockFetch(badBody);
    await expect(callBugFix("code", "err", "python")).rejects.toThrow(
      "API error 503"
    );
  });
});
