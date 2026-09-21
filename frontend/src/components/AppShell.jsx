import { BarChart3, LogOut, ShieldCheck, Users } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { CompanyLogo } from "./ui";

const ROLE_LABEL = { super_admin: "Super Admin", company_admin: "Company Admin", member: "Member" };

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const approved = user.company?.status === "approved";

  const links = [];
  if (user.role === "super_admin") links.push({ to: "/admin", label: "Companies", icon: ShieldCheck });
  if (approved) links.push({ to: "/dashboard", label: "Analyst", icon: BarChart3 });
  if (approved && user.role === "company_admin") links.push({ to: "/team", label: "Team", icon: Users });

  return (
    <div className="h-screen flex flex-col">
      <nav className="h-14 shrink-0 flex items-center justify-between px-5 border-b border-[var(--border)] bg-white">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="grid place-items-center w-8 h-8 rounded-lg bg-[var(--series-1)] text-white"><BarChart3 size={16} /></span>
            <span className="font-extrabold tracking-tight">Nexus AI</span>
          </div>
          <div className="flex items-center gap-1">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
                    isActive ? "bg-[var(--series-1)]/10 text-[var(--series-1)]" : "text-[var(--ink-secondary)] hover:bg-[var(--page)]"
                  }`
                }
              >
                <Icon size={15} /> {label}
              </NavLink>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {user.company && (
            <div className="flex items-center gap-2 pr-3 border-r border-[var(--border)]">
              <CompanyLogo company={user.company} size={28} />
              <span className="text-sm font-semibold">{user.company.name}</span>
            </div>
          )}
          <div className="text-right leading-tight">
            <div className="text-[13px] font-semibold">{user.full_name}</div>
            <div className="text-[11px] text-[var(--ink-muted)]">
              {ROLE_LABEL[user.role]}{user.designation ? ` · ${user.designation}` : ""}
            </div>
          </div>
          <button
            onClick={() => { logout(); navigate("/login"); }}
            title="Log out"
            className="grid place-items-center w-9 h-9 rounded-lg text-[var(--ink-muted)] hover:bg-[var(--status-critical-bg)] hover:text-[var(--status-critical)] transition-colors"
          >
            <LogOut size={16} />
          </button>
        </div>
      </nav>
      <div className="flex-1 min-h-0">
        <Outlet />
      </div>
    </div>
  );
}
