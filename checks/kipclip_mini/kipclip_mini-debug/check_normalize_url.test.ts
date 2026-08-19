import { assertEquals } from "@std/assert";
import { normalizeUrl } from "../src/url_utils.ts";

Deno.test("strips every tracking param, not just the first match", () => {
  const result = normalizeUrl(
    "https://Example.com/post?utm_source=x&fbclid=y&id=123",
  );
  assertEquals(result, "https://example.com/post?id=123");
});

Deno.test("still strips a single tracking param correctly", () => {
  const result = normalizeUrl("https://example.com/post?utm_source=x&id=1");
  assertEquals(result, "https://example.com/post?id=1");
});
