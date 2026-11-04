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

export interface Instrument {
  ticker: string;
  name: string;
  index_name: string;
  last_date: string | null;
  last_close: number | null;
  change_1d: number | null;
}

export interface Holding {
  ticker: string;
  name: string;
  sector: string | null;
  quantity: number;
  avg_cost: number;
  cost_basis: number;
  last_close: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  weight: number | null;
}

export interface PortfolioDetail extends Portfolio {
  holdings: Holding[];
  total_value: number;
  total_cost: number;
  unrealized_pnl: number;
  realized_pnl: number;
}

export type RecommendationAction = "ADD" | "REDUCE" | "CONSIDER_SELL";

export interface Recommendation {
  ticker: string;
  name: string;
  sector: string | null;
  action: RecommendationAction;
  score: number | null;
  reasons: string[];
}

export interface RecommendationsResponse {
  model_version: string;
  scores_date: string | null;
  risk_profile: RiskProfile;
  recommendations: Recommendation[];
  disclaimer: string;
}