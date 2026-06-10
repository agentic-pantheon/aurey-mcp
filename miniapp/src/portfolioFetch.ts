const MINIAPP_API = "/v1/miniapp/portfolio";
const DASHBOARD_API = "/v1/dashboard/portfolio";
const DASHBOARD_TOKEN_KEY = "aurey_dashboard_token";

export type ChartPeriod = "day" | "week" | "month" | "year" | "max";

export type PortfolioFetchFailure = {
  ok: false;
  fatal: string;
  detailCode: string | null;
};

export type PortfolioFetchSuccess<T> = {
  ok: true;
  snapshot: T;
};

export type PortfolioFetchResult<T> = PortfolioFetchSuccess<T> | PortfolioFetchFailure;

export type PortfolioFetchMode = "telegram" | "local";

export function resolvePortfolioFetchMode(): PortfolioFetchMode {
  if (typeof window === "undefined") return "local";
  const init = window.Telegram?.WebApp?.initData?.trim() ?? "";
  return init.length > 0 ? "telegram" : "local";
}

function readDashboardAuthToken(): string | null {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("token")?.trim();
  if (fromQuery) {
    try {
      sessionStorage.setItem(DASHBOARD_TOKEN_KEY, fromQuery);
    } catch {
      /* ignore */
    }
    return fromQuery;
  }
  try {
    const stored = sessionStorage.getItem(DASHBOARD_TOKEN_KEY)?.trim();
    return stored || null;
  } catch {
    return null;
  }
}

async function parsePortfolioResponse<T>(res: Response): Promise<PortfolioFetchResult<T>> {
  const ct = res.headers.get("content-type") || "";
  let body: Record<string, unknown> = {};
  if (ct.includes("application/json")) {
    body = (await res.json()) as Record<string, unknown>;
  } else if (!res.ok) {
    body = { detail: await res.text() };
  }
  if (!res.ok) {
    const d = body.detail;
    const obj =
      typeof d === "object" && d !== null && !Array.isArray(d) ? (d as Record<string, string>) : null;
    return {
      ok: false,
      fatal: obj?.message || (typeof d === "string" ? d : `${res.status}`),
      detailCode: obj?.code !== undefined ? String(obj.code) : null,
    };
  }
  return { ok: true, snapshot: body as T };
}

export async function fetchPortfolioSnapshot<T>(
  initData: string,
  chartPeriod: ChartPeriod = "month",
): Promise<PortfolioFetchResult<T>> {
  const res = await fetch(MINIAPP_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData, chart_period: chartPeriod }),
  });
  return parsePortfolioResponse<T>(res);
}

export async function fetchDashboardPortfolioSnapshot<T>(
  chartPeriod: ChartPeriod = "month",
): Promise<PortfolioFetchResult<T>> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = readDashboardAuthToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(DASHBOARD_API, {
    method: "POST",
    headers,
    body: JSON.stringify({ chart_period: chartPeriod }),
  });
  return parsePortfolioResponse<T>(res);
}

export function zerionWalletUrl(walletAddress: string): string {
  const addr = walletAddress.trim();
  return `https://app.zerion.io/${encodeURIComponent(addr)}/overview`;
}
