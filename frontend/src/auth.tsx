import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "./api";
import type { RiskProfile, User } from "./types";
import { AuthContext } from "./useAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Bez tokenu nie ma na co czekać - od razu "nie ładuje"
  const [loading, setLoading] = useState(() => getToken() !== null);

  // Po odświeżeniu strony: jeśli mamy token, pobieramy dane użytkownika
  useEffect(() => {
    if (!getToken()) return;
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const { access_token } = await api<{ access_token: string }>("/auth/login", { method: "POST", body });
    setToken(access_token);
    setUser(await api<User>("/auth/me"));
  }, []);

  const register = useCallback(
    async (email: string, password: string, riskProfile: RiskProfile) => {
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, risk_profile: riskProfile }),
      });
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}