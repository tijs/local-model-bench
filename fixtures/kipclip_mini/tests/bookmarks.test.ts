import { assertEquals } from "@std/assert";
import { findByTag } from "../src/bookmarks.ts";
import type { Bookmark } from "../src/types.ts";

function bookmark(overrides: Partial<Bookmark> = {}): Bookmark {
  return {
    id: "1",
    url: "https://example.com",
    title: "Example",
    tags: [],
    createdAt: 0,
    ...overrides,
  };
}

Deno.test("findByTag returns only bookmarks with that tag", () => {
  const bookmarks = [
    bookmark({ id: "a", tags: ["news"] }),
    bookmark({ id: "b", tags: ["recipes"] }),
  ];
  const result = findByTag(bookmarks, "news");
  assertEquals(result.map((b) => b.id), ["a"]);
});
