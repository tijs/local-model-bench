import type { Bookmark } from "./types.ts";

export function mergeImports(existing: Bookmark[], incoming: Bookmark[]): Bookmark[] {
  const result = existing.map((b) => ({ ...b, tags: [...b.tags] }));

  for (const inc of incoming) {
    const match = result.find((b) => b.url === inc.url);
    if (match) {
      match.tags = Array.from(new Set([...match.tags, ...inc.tags]));
    } else {
      result.push({ ...inc, tags: [...inc.tags] });
    }
  }

  return result;
}
