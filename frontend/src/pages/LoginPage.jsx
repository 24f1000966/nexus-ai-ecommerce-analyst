import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { errorMessage } from "../api";
import { homePathFor, useAuth } from "../auth/AuthContext";
import { Button, Field, inputClass } from "../components/ui";
import AuthLayout from "./AuthLayout";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!busy) return setSlow(false);
    const t = setTimeout(() => setSlow(true), 5000);
    return () => clearTimeout(t);
  }, [busy]);

  if (user) return <Navigate to={homePathFor(user)} replace />;

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const u = await login(email, password);
      navigate(homePathFor(u), { replace: true });
    } catch (err) {
      setError(errorMessage(err, "Could not sign in."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <h2 className="text-2xl font-extrabold tracking-tight">Welcome back</h2>
      <p className="text-sm text-[var(--ink-secondary)] mt-1 mb-7">Sign in to your Nexus AI workspace.</p>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Work email">
          <input className={inputClass} type="email" autoComplete="username" value={email}
            onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
        </Field>
        <Field label="Password">
          <input className={inputClass} type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
        </Field>
        {error && <div className="rounded-xl bg-[var(--status-critical-bg)] text-[var(--status-critical)] text-sm px-3.5 py-2.5">{error}</div>}
        <Button type="submit" loading={busy} className="w-full">Sign in</Button>
        {slow && (
          <p className="text-[12.5px] text-center text-[var(--ink-secondary)]">
            Waking up the server — the free host sleeps when idle, so the first sign-in can take up to a minute.
          </p>
        )}
      </form>
      <p className="text-sm text-[var(--ink-secondary)] mt-6 text-center">
        Is your company new to Nexus AI?{" "}
        <Link to="/register" className="font-semibold text-[var(--series-1)] hover:underline">Register your company</Link>
      </p>
    </AuthLayout>
  );
}
