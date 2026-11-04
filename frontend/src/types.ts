// Typy odpowiadające schematom Pydantic z backendu (backend/app/schemas.py)

export type RiskProfile = "conservative" | "balanced" | "dynamic";

export const RISK_PROFILE_LABELS: Record<RiskProfile, string> = {
  conservative: "Konserwatywny",
  balanced: "Zrównoważony",
  dynamic: "Dynamiczny",
};

export interface User {
  id: number;
  email: string;
  risk_profile: RiskProfile;
  created_at: string;
}

export interface Portfolio {
  id: number;
  name: string;
  created_at: string;
}