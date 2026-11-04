// Formatowanie liczb w polskim zapisie (Intl - wbudowane w przeglądarkę)

const pln = new Intl.NumberFormat("pl-PL", { style: "currency", currency: "PLN" });
const signedPln = new Intl.NumberFormat("pl-PL", { style: "currency", currency: "PLN", signDisplay: "exceptZero" });
const pct = new Intl.NumberFormat("pl-PL", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
const signedPct = new Intl.NumberFormat("pl-PL", {
  style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero",
});
const number = new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 4 });

const dash = "–";

export const formatPLN = (v: number | null) => (v === null ? dash : pln.format(v));
export const formatSignedPLN = (v: number | null) => (v === null ? dash : signedPln.format(v));
export const formatPct = (v: number | null) => (v === null ? dash : pct.format(v));
export const formatSignedPct = (v: number | null) => (v === null ? dash : signedPct.format(v));
export const formatNumber = (v: number) => number.format(v);

/** Klasa CSS koloru zysku/straty. */
export const pnlClass = (v: number | null) => (v === null || v === 0 ? "" : v > 0 ? "positive" : "negative");