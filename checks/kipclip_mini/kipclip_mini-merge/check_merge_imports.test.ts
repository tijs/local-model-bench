import { assertEquals } from "@std/assert";
import { mergeImports } from "../src/import_merge.ts";
import type { Bookmark } from "../src/types.ts";

function bookmark(overrides: Partial<Bookmark> = {}): Bookmark {
  return {
    id: "1",
    url: "https://example.com/a",
    title: "A",
    tags: [],
    createdAt: 0,
    ...overrides,
  };
}

Deno.test("a hostname-case duplicate is merged, not kept as a second entry", () => {
  const existing = [bookmark({ id: "keep", url: "https://example.com/a" })];
  const incoming = [bookmark({ id: "dupe", url: "https://EXAMPLE.com/a" })];
  const result = mergeImports(existing, incoming);
  assertEquals(result.length, 1);
  assertEquals(result[0].id, "keep");
});

Deno.test("a duplicate's tags are the union of both copies, deduplicated", () => {
  const existing = [bookmark({ url: "https://example.com/a", tags: ["news"] })];
  const incoming = [bookmark({ url: "https://EXAMPLE.com/a", tags: ["news", "recipes"] })];
  const result = mergeImports(existing, incoming);
  assertEquals(result.length, 1);
  assertEquals(new Set(result[0].tags), new Set(["news", "recipes"]));
});

Deno.test("a bookmark with no matching URL is appended, not dropped", () => {
  const existing = [bookmark({ id: "old", url: "https://example.com/a" })];
  const incoming = [bookmark({ id: "new", url: "https://example.com/b", tags: ["fresh"] })];
  const result = mergeImports(existing, incoming);
  assertEquals(result.map((b) => b.id), ["old", "new"]);
  assertEquals(result[1].tags, ["fresh"]);
});
