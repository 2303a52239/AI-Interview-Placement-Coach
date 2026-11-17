import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getMe, loginUser, logoutUser, registerUser, tokens } from "../services/api";

export interface AppUser {
  id: number;
  name: string;
  email: string;
  is_admin: boolean;
  role: "student" | "placement_officer" | "admin";
  profile?: Record<string, any>;
}

interface AuthValue {
  user: AppUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!tokens.access() && !tokens.refresh()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await getMe(); // the API client refreshes an expired access token transparently
      setUser(res.data);
    } catch (err: any) {
      // Only a rejected session ends it. A rate limit, outage or network blip must not log the user out.
      if (err?.response?.status === 401 || err?.response?.status === 403) {
        tokens.clear();
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refreshUser(); }, [refreshUser]);

  const login = async (email: string, password: string) => {
    const res = await loginUser({ email, password });
    tokens.save(res.data.access_token, res.data.refresh_token);
    await refreshUser();
  };

  const register = async (name: string, email: string, password: string) => {
    const res = await registerUser({ name, email, password });
    tokens.save(res.data.access_token, res.data.refresh_token);
    await refreshUser();
  };

  const logout = async () => {
    try { await logoutUser(); } catch { /* the token may already be invalid; clearing locally is what matters */ }
    tokens.clear();
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
