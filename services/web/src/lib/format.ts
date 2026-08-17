/**
 * Display formatting and risk presentation.
 *
 * These lived at the bottom of `lib/api.ts` between the alert client and the
 * auth client, so every component that wanted `formatCurrency` imported the
 * whole API surface.
 *
 * Note on scale: risk scores are 0-1 everywhere — in the database, over the
 * wire and here. Percentages are produced only at render time.
 */

export type RiskCategory = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

/** Thresholds are the presentation-layer bands, applied to a 0-1 score. */
const RISK_THRESHOLDS: ReadonlyArray<[number, RiskCategory]> = [
  [0.8, "CRITICAL"],
  [0.6, "HIGH"],
  [0.3, "MEDIUM"],
  [0, "LOW"],
];

const RISK_STYLES: Record<RiskCategory, string> = {
  LOW: "text-emerald-700 bg-emerald-100 dark:text-emerald-300 dark:bg-emerald-950",
  MEDIUM: "text-amber-700 bg-amber-100 dark:text-amber-300 dark:bg-amber-950",
  HIGH: "text-orange-700 bg-orange-100 dark:text-orange-300 dark:bg-orange-950",
  CRITICAL: "text-red-700 bg-red-100 dark:text-red-300 dark:bg-red-950",
};

const NEUTRAL_STYLE = "text-slate-600 bg-slate-100 dark:text-slate-300 dark:bg-slate-800";

/** Band a 0-1 risk score. A missing score is treated as LOW; 0 is a real LOW. */
export function getRiskCategory(score?: number | null): RiskCategory {
  if (score === undefined || score === null || Number.isNaN(score)) return "LOW";
  for (const [threshold, category] of RISK_THRESHOLDS) {
    if (score >= threshold) return category;
  }
  return "LOW";
}

/** Tailwind classes for a risk badge. Accepts any casing. */
export function getRiskColor(category: string): string {
  return RISK_STYLES[category?.toUpperCase() as RiskCategory] ?? NEUTRAL_STYLE;
}

/** Format a 0-1 score as a percentage. */
export function formatRiskScore(score?: number | null, fractionDigits = 1): string {
  if (score === undefined || score === null || Number.isNaN(score)) return "—";
  return `${(score * 100).toFixed(fractionDigits)}%`;
}

export function formatCurrency(amount?: number | null, currency = "INR"): string {
  if (amount === undefined || amount === null || Number.isNaN(amount)) return "—";
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    // An unknown ISO code would otherwise throw a RangeError mid-render.
    return `${currency} ${amount.toFixed(2)}`;
  }
}

/** Compact currency for dense tables and stat tiles: ₹1.2Cr, ₹45.6L, ₹12.3K. */
export function formatCompactCurrency(amount?: number | null, currency = "INR"): string {
  if (amount === undefined || amount === null || Number.isNaN(amount)) return "—";
  const symbol = currency === "INR" ? "₹" : `${currency} `;
  const absolute = Math.abs(amount);
  const sign = amount < 0 ? "-" : "";
  if (currency === "INR") {
    if (absolute >= 1e7) return `${sign}${symbol}${(absolute / 1e7).toFixed(1)}Cr`;
    if (absolute >= 1e5) return `${sign}${symbol}${(absolute / 1e5).toFixed(1)}L`;
  } else if (absolute >= 1e9) {
    return `${sign}${symbol}${(absolute / 1e9).toFixed(1)}B`;
  } else if (absolute >= 1e6) {
    return `${sign}${symbol}${(absolute / 1e6).toFixed(1)}M`;
  }
  if (absolute >= 1e3) return `${sign}${symbol}${(absolute / 1e3).toFixed(1)}K`;
  return `${sign}${symbol}${absolute.toFixed(2)}`;
}

export function formatNumber(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN").format(value);
}

/**
 * Absolute date/time.
 *
 * The previous version passed an unvalidated string to `Intl.DateTimeFormat`,
 * so a null or malformed timestamp rendered as "Invalid Date".
 */
export function formatDate(value?: string | Date | null): string {
  const date = toDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatDateOnly(value?: string | Date | null): string {
  const date = toDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

/** "3 minutes ago" / "in 2 hours". */
export function formatRelativeTime(value?: string | Date | null): string {
  const date = toDate(value);
  if (!date) return "—";

  const seconds = (date.getTime() - Date.now()) / 1000;
  const units: ReadonlyArray<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 60 * 60 * 24 * 365],
    ["month", 60 * 60 * 24 * 30],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
    ["second", 1],
  ];

  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  for (const [unit, secondsPerUnit] of units) {
    if (Math.abs(seconds) >= secondsPerUnit || unit === "second") {
      return formatter.format(Math.round(seconds / secondsPerUnit), unit);
    }
  }
  return "just now";
}

export function toDate(value?: string | Date | null): Date | null {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Title-case a snake_case or kebab-case identifier for display. */
export function humanise(value?: string | null): string {
  if (!value) return "—";
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/** Mask all but the last four characters of an identifier. */
export function maskIdentifier(value?: string | null, visible = 4): string {
  if (!value) return "—";
  if (value.length <= visible) return "•".repeat(value.length);
  return `${"•".repeat(Math.min(value.length - visible, 8))}${value.slice(-visible)}`;
}
