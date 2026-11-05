import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./useAuth";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import PortfoliosPage from "./pages/PortfoliosPage";
import RegisterPage from "./pages/RegisterPage";
import PortfolioPage from "./pages/PortfolioPage";

/** Wpuszcza tylko zalogowanych; pozostałych przekierowuje do logowania. */
function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="container muted">Ładowanie…</p>;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route path="/" element={<PortfoliosPage />} />
        <Route path="/portfolios/:id" element={<PortfolioPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}