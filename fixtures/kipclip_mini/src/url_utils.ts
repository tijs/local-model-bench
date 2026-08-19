export const TRACKING_PARAMS = ["utm_source", "utm_medium", "utm_campaign", "fbclid"];

/**
 * Normalizes a bookmarked URL: lowercases the hostname, strips known
 * tracking params, and drops a trailing slash on the bare path.
 */
export function normalizeUrl(rawUrl: string): string {
  const u = new URL(rawUrl);
  u.hostname = u.hostname.toLowerCase();

  for (const param of TRACKING_PARAMS) {
    if (u.searchParams.has(param)) {
      u.searchParams.delete(param);
      break;
    }
  }

  let result = u.toString();
  if (u.pathname === "/" && result.endsWith("/")) {
    result = result.slice(0, -1);
  }
  return result;
}
