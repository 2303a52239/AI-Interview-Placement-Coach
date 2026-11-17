import { describe, it, expect, beforeEach, vi } from "vitest";
import axios from "axios";
import api, { tokens } from "@/services/api";

/** A fake transport: records requests and answers from a script, so no network is used. */
function fakeAdapter(handler: (config: any) => { status: number; data?: any }) {
  const seen: any[] = [];
  api.defaults.adapter = async (config: any) => {
    seen.push(config);
    const r = handler(config);
    const response = { data: r.data ?? {}, status: r.status, statusText: "", headers: {}, config };
    if (r.status >= 400) { const err: any = new Error("fail"); err.isAxiosError = true; err.config = config; err.response = response; throw err; }
    return response;
  };
  return seen;
}

describe("api client", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });

  it("attaches the bearer token", async () => {
    tokens.save("abc", "ref");
    const seen = fakeAdapter(() => ({ status: 200, data: { ok: true } }));
    await api.get("/users/me");
    expect(seen[0].headers.Authorization).toBe("Bearer abc");
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    tokens.save("expired", "refresh-1");
    vi.spyOn(axios, "post").mockResolvedValue({ data: { access_token: "fresh", refresh_token: "refresh-2" } } as any);
    const seen = fakeAdapter((c) => (c.headers.Authorization === "Bearer fresh" ? { status: 200, data: { id: 1 } } : { status: 401 }));
    const res = await api.get("/users/me");
    expect(res.data).toEqual({ id: 1 });
    expect(seen).toHaveLength(2);
    expect(tokens.access()).toBe("fresh");
    expect(tokens.refresh()).toBe("refresh-2");
  });

  it("clears tokens when refresh fails", async () => {
    tokens.save("expired", "bad");
    vi.spyOn(axios, "post").mockRejectedValue(new Error("nope"));
    fakeAdapter(() => ({ status: 401 }));
    await expect(api.get("/users/me")).rejects.toBeTruthy();
    expect(tokens.access()).toBeNull();
  });

  it("does not try to refresh a failed login", async () => {
    const post = vi.spyOn(axios, "post");
    fakeAdapter(() => ({ status: 401, data: { detail: "Invalid" } }));
    await expect(api.post("/auth/login", {})).rejects.toBeTruthy();
    expect(post).not.toHaveBeenCalled();
  });
});
