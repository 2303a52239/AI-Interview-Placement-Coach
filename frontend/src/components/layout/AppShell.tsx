import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FileText, Users, Code2, LineChart, ListChecks, History, UserCircle, LogOut, GraduationCap,
  Menu, X, Moon, Sun, Target, Map, Bot, Building2, BarChart3,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useConfirm } from "../../context/ConfirmContext";
import { useTheme } from "../../context/ThemeContext";
import { getAiStatus } from "../../services/api";
import { cn } from "@/lib/utils";

const NAV_GROUPS = [
  { label: "Overview", items: [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/analytics", label: "Analytics", icon: BarChart3 },
    { to: "/performance", label: "Performance", icon: LineChart },
  ] },
  { label: "Profile", items: [
    { to: "/profile", label: "Profile", icon: UserCircle },
    { to: "/resume", label: "Resume", icon: FileText },
  ] },
  { label: "Practice", items: [
    { to: "/interview/hr", label: "HR Interview", icon: Users },
    { to: "/interview/technical", label: "Technical Interview", icon: GraduationCap },
    { to: "/coding", label: "Coding Assessment", icon: Code2 },
    { to: "/history", label: "Interview History", icon: History },
    { to: "/assistant", label: "Study Assistant", icon: Bot },
  ] },
  { label: "Plan", items: [
    { to: "/skill-gap", label: "Skill Gap", icon: Target },
    { to: "/roadmap", label: "Roadmap", icon: Map },
    { to: "/preparation-plan", label: "Preparation Plan", icon: ListChecks },
    { to: "/companies", label: "Company Prep", icon: Building2 },
  ] },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const confirm = useConfirm();
  const [menuOpen, setMenuOpen] = useState(false);
  const [ai, setAi] = useState<{ mode: string; model?: string | null } | null>(null);

  useEffect(() => { getAiStatus().then((r) => setAi(r.data)).catch(() => setAi(null)); }, []);

  const groups = NAV_GROUPS;
  const all = groups.flatMap((g) => g.items);
  const current = all.find((i) => location.pathname === i.to || location.pathname.startsWith(i.to + "/"));

  const handleLogout = async () => {
    const ok = await confirm({ title: "Log out?", message: "Any interview that is in progress will stay unfinished in your history.", confirmLabel: "Log out" });
    if (!ok) return;
    await logout();
    navigate("/login");
  };

  const sidebar = (
    <>
      <div className="border-b border-white/10 px-5 py-6">
        <p className="font-display text-lg leading-tight">Placement<br />Coach</p>
        <p className="mt-1 text-xs text-white/50">AI Interview Intelligence</p>
      </div>
      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4" aria-label="Main navigation">
        {groups.map((g) => (
          <div key={g.label}>
            <p className="mb-1 px-3 text-[11px] uppercase tracking-wider text-white/40">{g.label}</p>
            <div className="space-y-0.5">
              {g.items.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} onClick={() => setMenuOpen(false)}
                  className={({ isActive }) => cn("flex items-center gap-3 rounded-card px-3 py-2 text-sm transition-colors",
                    isActive ? "bg-amber font-medium text-[rgb(23_27_31)]" : "text-white/75 hover:bg-paper-panel/10 hover:text-white")}>
                  <Icon size={16} /> {label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-white/10 px-3 py-4">
        <button onClick={handleLogout} className="flex w-full items-center gap-3 rounded-card px-3 py-2.5 text-sm text-white/75 transition-colors hover:bg-paper-panel/10 hover:text-white">
          <LogOut size={16} /> Log out
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-paper">
      <aside className="hidden w-64 shrink-0 flex-col bg-sidebar text-sidebar-fg lg:flex">{sidebar}</aside>
      {menuOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <aside className="flex w-64 flex-col bg-sidebar text-sidebar-fg">{sidebar}</aside>
          <div className="flex-1 bg-black/50" onClick={() => setMenuOpen(false)} />
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-paper-line bg-paper-panel px-4 sm:px-8">
          <div className="flex items-center gap-3">
            <button className="focus-ring -ml-1.5 rounded-card p-1.5 hover:bg-paper lg:hidden" onClick={() => setMenuOpen((o) => !o)} aria-label={menuOpen ? "Close menu" : "Open menu"}>
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <p className="font-display text-base">{current ? current.label : "Placement Coach"}</p>
          </div>
          <div className="flex items-center gap-3">
            {ai && (
              <span title={ai.mode === "openai" ? `Live model: ${ai.model}` : "Answers are scored by built-in rules, not a language model"}
                className={cn("hidden rounded px-2 py-0.5 text-xs font-medium sm:inline", ai.mode === "openai" ? "bg-teal-light text-teal-dark" : "bg-amber-light text-amber-dark")}>
                {ai.mode === "openai" ? "AI: live model" : "AI: mock mode"}
              </span>
            )}
            <button onClick={toggle} aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"} className="focus-ring rounded-card p-2 hover:bg-paper">
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight">{user?.name}</p>
              <p className="text-xs leading-tight text-ink-faint">{user?.profile?.target_role}</p>
            </div>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber text-sm font-medium text-[rgb(23_27_31)]">{(user?.name || "?").charAt(0).toUpperCase()}</div>
          </div>
        </header>
        <main className="min-w-0 flex-1"><div className="mx-auto max-w-6xl px-4 py-8 sm:px-8">{children}</div></main>
      </div>
    </div>
  );
}
