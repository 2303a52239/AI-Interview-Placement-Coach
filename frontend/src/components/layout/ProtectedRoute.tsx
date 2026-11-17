import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Spinner } from "../ui/page";
import AppShell from "./AppShell";

export default function ProtectedRoute({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center bg-paper"><Spinner label="Checking your session..." /></div>;
  if (!user) return <Navigate to="/login" replace />;
  const isStaff = user.role === "admin" || user.role === "placement_officer" || user.is_admin;
  if (adminOnly && !isStaff) return <Navigate to="/dashboard" replace />;
  return <AppShell>{children}</AppShell>;
}
