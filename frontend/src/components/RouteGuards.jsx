import { Navigate } from "react-router-dom";
import { homePathFor, useAuth } from "../auth/AuthContext";

export function Splash() {
  return <div className="h-screen grid place-items-center text-sm text-[var(--ink-muted)]">Loading…</div>;
}

// `roles`: allowed roles. `needApproved`: company must be approved (tenant features).
export function RequireAuth({ roles, needApproved = false, children }) {
  const { user, loading } = useAuth();
  if (loading) return <Splash />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homePathFor(user)} replace />;
  if (needApproved && user.company?.status !== "approved") return <Navigate to="/status" replace />;
  return children;
}

export function RedirectHome() {
  const { user, loading } = useAuth();
  if (loading) return <Splash />;
  return <Navigate to={homePathFor(user)} replace />;
}
