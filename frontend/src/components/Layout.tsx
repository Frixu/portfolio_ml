import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { RISK_PROFILE_LABELS } from "../types";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <>
      <header className="header">
        <div className="container header-inner">
          <Link to="/" className="logo">Portfolio ML</Link>
          {user && (
            <div className="header-user">
              <span>{user.email}</span>
              <span className="badge">{RISK_PROFILE_LABELS[user.risk_profile]}</span>
              <button className="link-button" onClick={logout}>Wyloguj</button>
            </div>
          )}
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}