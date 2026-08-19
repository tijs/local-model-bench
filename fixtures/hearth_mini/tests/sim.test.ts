import { describe, expect, it } from "vitest";
import { build, canAfford } from "../src/sim";
import type { Settlement } from "../src/types";

function settlement(overrides: Partial<Settlement> = {}): Settlement {
  return {
    resources: { wood: 30, food: 10, stone: 10 },
    population: 2,
    buildings: [],
    ...overrides,
  };
}

describe("canAfford / build", () => {
  it("affords a hut with enough wood", () => {
    expect(canAfford(settlement(), "hut")).toBe(true);
  });

  it("does not afford a farm without enough stone", () => {
    const s = settlement({ resources: { wood: 30, food: 10, stone: 0 } });
    expect(canAfford(s, "farm")).toBe(false);
  });

  it("build deducts cost and adds the building", () => {
    const s = build(settlement(), "hut");
    expect(s.resources.wood).toBe(20);
    expect(s.buildings).toEqual(["hut"]);
  });

  it("build throws when unaffordable", () => {
    const s = settlement({ resources: { wood: 0, food: 0, stone: 0 } });
    expect(() => build(s, "hut")).toThrow();
  });
});
