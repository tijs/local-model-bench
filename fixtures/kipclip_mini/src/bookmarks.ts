import type { Bookmark } from "./types.ts";

export function findByTag(bookmarks: Bookmark[], tag: string): Bookmark[] {
  return bookmarks.filter((b) => b.tags.includes(tag));
}
