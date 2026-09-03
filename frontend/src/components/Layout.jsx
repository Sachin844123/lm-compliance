import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ScanLine,
  FolderSearch,
  Users,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/scan", label: "New Scan", icon: ScanLine },
  { to: "/repository", label: "Repository", icon: FolderSearch },
  { to: "/users", label: "Users", icon: Users, roles: ["admin"] },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-slate-50">
      <aside className="w-64 shrink-0 bg-slate-900 text-slate-200 flex flex-col">
        <div className="flex items-center gap-2 px-5 py-5 border-b border-slate-800">
          <ShieldCheck className="text-emerald-400" size={24} />
          <div>
            <p className="font-semibold text-white leading-tight">LM Compliance</p>
            <p className="text-xs text-slate-400 leading-tight">Packaged Commodities</p>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems
            .filter((item) => !item.roles || item.roles.includes(user?.role))
            .map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`
                }
              >
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
        </nav>
        <div className="px-3 py-4 border-t border-slate-800">
          <div className="px-3 mb-3">
            <p className="text-sm font-medium text-white">{user?.full_name}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
          </div>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="flex items-center gap-2 px-3 py-2 w-full rounded-lg text-sm text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-8">{children}</div>
      </main>
    </div>
  );
}
