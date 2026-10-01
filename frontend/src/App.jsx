import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import AppShell from "./components/AppShell";
import { RedirectHome, RequireAuth } from "./components/RouteGuards";
import { ToastProvider } from "./components/Toast";
import AdminPage from "./pages/AdminPage";
import AnalystPage from "./pages/AnalystPage";
import DataPage from "./pages/DataPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import StatusPage from "./pages/StatusPage";
import TeamPage from "./pages/TeamPage";

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route element={<RequireAuth><AppShell /></RequireAuth>}>
              <Route path="/admin" element={<RequireAuth roles={["super_admin"]}><AdminPage /></RequireAuth>} />
              <Route path="/status" element={<StatusPage />} />
              <Route path="/dashboard" element={<RequireAuth roles={["company_admin", "member"]} needApproved><AnalystPage /></RequireAuth>} />
              <Route path="/data" element={<RequireAuth roles={["company_admin"]} needApproved><DataPage /></RequireAuth>} />
              <Route path="/team" element={<RequireAuth roles={["company_admin"]} needApproved><TeamPage /></RequireAuth>} />
            </Route>

            <Route path="/" element={<RedirectHome />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
