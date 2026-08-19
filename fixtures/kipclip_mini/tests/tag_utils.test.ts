import { assertEquals } from "@std/assert";
import { sortTagsByUsage } from "../src/tag_utils.ts";

Deno.test("sortTagsByUsage sorts by count descending", () => {
  const result = sortTagsByUsage({ b: 1, a: 3, c: 2 });
  assertEquals(result, ["a", "c", "b"]);
});

Deno.test("sortTagsByUsage breaks ties alphabetically", () => {
  const result = sortTagsByUsage({ zebra: 2, apple: 2 });
  assertEquals(result, ["apple", "zebra"]);
});
