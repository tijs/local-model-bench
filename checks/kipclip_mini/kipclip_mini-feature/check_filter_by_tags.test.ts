import { assertEquals } from "@std/assert";
import { filterByTags } from "../src/bookmarks.ts";
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

Deno.test("filterByTags requires every given tag (AND semantics)", () => {
  const bookmarks = [
    bookmark({ id: "a", tags: ["news", "tech"] }),
    bookmark({ id: "b", tags: ["news"] }),
    bookmark({ id: "c", tags: ["tech"] }),
  ];
  const result = filterByTags(bookmarks, ["news", "tech"]);
  assertEquals(result.map((b) => b.id), ["a"]);
});

Deno.test("filterByTags with an empty tag list returns everything", () => {
  const bookmarks = [bookmark({ id: "a" }), bookmark({ id: "b" })];
  const result = filterByTags(bookmarks, []);
  assertEquals(result.map((b) => b.id), ["a", "b"]);
});

Deno.test("filterByTags returns nothing when no bookmark has all tags", () => {
  const bookmarks = [bookmark({ id: "a", tags: ["news"] })];
  assertEquals(filterByTags(bookmarks, ["news", "tech"]), []);
});

// Added 2026-08-21 (3rd adversarial review, low finding): confirmed live
// that an implementation matching tags by STRING SUBSTRING
// (`t.includes(tag)`) instead of exact equality passed every test above
// — none of them exercise a tag that's a substring of a different real
// tag. "news" and "newsletter" share that relationship; exact matching
// must tell them apart.
Deno.test("filterByTags requires an EXACT tag match, not a substring", () => {
  const bookmarks = [
    bookmark({ id: "a", tags: ["newsletter"] }),
    bookmark({ id: "b", tags: ["news"] }),
  ];
  assertEquals(filterByTags(bookmarks, ["news"]).map((b) => b.id), ["b"]);
});
