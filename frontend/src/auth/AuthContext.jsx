import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getMe, login as apiLogin, tokenStore } from "../api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function homePathFor(user) {
  if (!user) return "/login";
  if (user.role === "super_admin") return "/admin";
  if (user.company?.status !== "approved") return "/status";
  return "/dashboard";
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const refresh = useCallback(async () => {
    const me = await getMe();
    setUser(me);
    return me;
  }, []);

  useEffect(() => {
    if (tokenStore.get()) {
      refresh().catch(() => tokenStore.clear()).finally(() => setLoading(false));
    }
    const onLogout = () => setUser(null);
    window.addEventListener("nexus-logout", onLogout);
    return () => window.removeEventListener("nexus-logout", onLogout);
  }, [refresh]);

  async function login(email, password) {
    const res = await apiLogin(email, password);
    tokenStore.set(res.token);
    setUser(res.user);
    return res.user;
  }

  function logout() {
    tokenStore.clear();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
