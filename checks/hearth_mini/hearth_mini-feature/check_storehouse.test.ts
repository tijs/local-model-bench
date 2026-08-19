import { describe, expect, it } from "vitest";
import { availableBuildings, BUILDING_COSTS } from "../src/sim";
import type { Settlement } from "../src/types";

function settlement(overrides: Partial<Settlement> = {}): Settlement {
  return {
    resources: { wood: 100, food: 10, stone: 100 },
    population: 2,
    buildings: [],
    ...overrides,
  };
}

describe("availableBuildings", () => {
  it("excludes storehouse before a hut is built", () => {
    const result = availableBuildings(settlement());
    expect(result).not.toContain("storehouse");
    expect(result).toContain("hut");
  });

  it("includes storehouse once a hut is built and affordable", () => {
    const s = settlement({ buildings: ["hut"] });
    expect(availableBuildings(s)).toContain("storehouse");
  });

  it("excludes storehouse when unaffordable even with hut built", () => {
    const s = settlement({
      buildings: ["hut"],
      resources: { wood: 0, food: 0, stone: 0 },
    });
    expect(availableBuildings(s)).not.toContain("storehouse");
  });

  it("storehouse cost matches spec", () => {
    expect(BUILDING_COSTS.storehouse).toEqual({ wood: 25, stone: 10 });
  });
});
