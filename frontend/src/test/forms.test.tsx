import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../services/api", async () => {
  const actual: any = await vi.importActual("../services/api");
  return { ...actual, getMe: vi.fn(), updateProfile: vi.fn(), getReadiness: vi.fn(), getResume: vi.fn(), listRoles: vi.fn(), fetchPhotoBlob: vi.fn(),
    autofillProfile: vi.fn(), uploadPhoto: vi.fn(), deletePhoto: vi.fn(), uploadResume: vi.fn() };
});
import * as api from "../services/api";
import Profile from "../pages/Profile";
import { AuthProvider } from "../context/AuthContext";
import { ThemeProvider } from "../context/ThemeContext";
import { ToastProvider } from "../context/ToastContext";
import { ConfirmProvider } from "../context/ConfirmContext";

const me = { id: 1, name: "Demo Student", email: "d@x.com", role: "student", is_admin: false, profile: { college: "", skills: [], projects: [], certifications: [], internships: [], preferred_companies: [], target_roles: [], target_role: "Software Developer", experience_years: "0" } };

describe("Profile form", () => {
  beforeEach(() => {
    localStorage.clear(); localStorage.setItem("access_token", "t"); vi.clearAllMocks();
    (api.getMe as any).mockResolvedValue({ data: me });
    (api.getReadiness as any).mockResolvedValue({ data: { score: 30, band: "Needs work", profile_gaps: ["Add skills"] } });
    (api.getResume as any).mockRejectedValue(new Error("none"));
    (api.listRoles as any).mockResolvedValue({ data: { roles: ["Software Developer", "Data Analyst"] } });
    (api.updateProfile as any).mockResolvedValue({ data: {} });
  });
  const open = () => render(<ThemeProvider><MemoryRouter><AuthProvider><ToastProvider><ConfirmProvider><Profile /></ConfirmProvider></ToastProvider></AuthProvider></MemoryRouter></ThemeProvider>);

  it("saves edited fields and an added skill", async () => {
    open();
    const college = await screen.findByLabelText("University / college");
    await userEvent.type(college, "IIT Madras");
    await userEvent.type(screen.getByLabelText("CGPA (0-10)"), "8.5");
    await userEvent.click(screen.getByRole("tab", { name: "Skills" }));
    await userEvent.click(screen.getByRole("button", { name: /add skill/i }));
    await userEvent.type(screen.getByLabelText("Skill 1 name"), "Python");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(api.updateProfile).toHaveBeenCalled());
    const payload = (api.updateProfile as any).mock.calls[0][0];
    expect(payload.college).toBe("IIT Madras");
    expect(payload.cgpa).toBe(8.5);
    expect(payload.skills).toEqual([{ name: "Python", proficiency: "intermediate" }]);
  });

  it("rejects a CGPA above 10 without calling the API", async () => {
    open();
    const cgpa = await screen.findByLabelText("CGPA (0-10)");
    await userEvent.type(cgpa, "11");
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText(/CGPA must be between 0 and 10/)).toBeInTheDocument();
    expect(api.updateProfile).not.toHaveBeenCalled();
  });
});
