import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/services/api", async () => {
  const actual: any = await vi.importActual("@/services/api");
  return { ...actual, getMe: vi.fn(), loginUser: vi.fn(), logoutUser: vi.fn(), registerUser: vi.fn(), getAiStatus: vi.fn().mockResolvedValue({ data: { mode: "mock" } }) };
});
vi.mock("../services/api", async () => {
  const actual: any = await vi.importActual("../services/api");
  return { ...actual, getMe: vi.fn(), loginUser: vi.fn(), logoutUser: vi.fn(), registerUser: vi.fn(), getAiStatus: vi.fn().mockResolvedValue({ data: { mode: "mock" } }) };
});

import * as api from "../services/api";
import { AuthProvider } from "../context/AuthContext";
import { ThemeProvider } from "../context/ThemeContext";
import { ToastProvider } from "../context/ToastContext";
import { ConfirmProvider } from "../context/ConfirmContext";
import ProtectedRoute from "../components/layout/ProtectedRoute";
import Login from "../pages/Login";

const wrap = (initial: string, ui: React.ReactNode) => render(
  <ThemeProvider><MemoryRouter initialEntries={[initial]}><AuthProvider><ToastProvider><ConfirmProvider>{ui}</ConfirmProvider></ToastProvider></AuthProvider></MemoryRouter></ThemeProvider>);

describe("auth flow", () => {
  beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); });

  it("redirects an anonymous visitor from a protected page to login", async () => {
    wrap("/dashboard", <Routes><Route path="/login" element={<div>login page</div>} /><Route path="/dashboard" element={<ProtectedRoute><div>secret</div></ProtectedRoute>} /></Routes>);
    expect(await screen.findByText("login page")).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("keeps non-staff users out of admin routes", async () => {
    localStorage.setItem("access_token", "t");
    (api.getMe as any).mockResolvedValue({ data: { id: 1, name: "Stu", email: "s@x.com", role: "student", is_admin: false } });
    wrap("/admin", <Routes><Route path="/dashboard" element={<div>student home</div>} /><Route path="/admin" element={<ProtectedRoute adminOnly><div>admin area</div></ProtectedRoute>} /></Routes>);
    expect(await screen.findByText("student home")).toBeInTheDocument();
  });

  it("login form submits credentials and shows server errors", async () => {
    (api.loginUser as any).mockRejectedValue({ response: { status: 401, data: { detail: "Invalid email or password." } }, isAxiosError: true });
    wrap("/login", <Routes><Route path="/login" element={<Login />} /></Routes>);
    const email = screen.getByPlaceholderText("you@example.com");
    await userEvent.clear(email);
    await userEvent.type(email, "a@b.com");
    await userEvent.type(screen.getByPlaceholderText("••••••••"), "wrongpass1");
    await userEvent.click(screen.getByRole("button", { name: /sign in|log in/i }));
    await waitFor(() => expect(api.loginUser).toHaveBeenCalledWith({ email: "a@b.com", password: "wrongpass1" }));
    expect(await screen.findByText(/invalid email or password/i)).toBeInTheDocument();
  });
});
