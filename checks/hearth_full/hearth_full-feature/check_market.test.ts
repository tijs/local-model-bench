import { describe, expect, it } from "vitest";
import { availableBuildings, BUILDING_REGISTRY } from "../src/buildings";
import { sellResource } from "../src/sim/trade";
import type { Settlement } from "../src/types";

function settlement(overrides: Partial<Settlement> = {}): Settlement {
  return {
    resources: { wood: 100, food: 10, stone: 100 },
    population: 2,
    buildings: [],
    turn: 0,
    ...overrides,
  };
}

describe("market building", () => {
  it("is not available without a storehouse, even if affordable", () => {
    const result = availableBuildings(settlement());
    expect(result).not.toContain("market");
  });

  it("becomes available once a storehouse is built and it's affordable", () => {
    const s = settlement({ buildings: ["hut", "storehouse"] });
    expect(availableBuildings(s)).toContain("market");
  });

  it("costs match spec", () => {
    expect(BUILDING_REGISTRY.market.cost).toEqual({ wood: 20, stone: 15 });
    expect(BUILDING_REGISTRY.market.requires).toBe("storehouse");
  });
});

describe("sellResource", () => {
  it("throws if no market is built", () => {
    const s = settlement();
    expect(() => sellResource(s, "wood", 10)).toThrow();
  });

  it("converts the sold resource into stone at a 2:1 ratio, rounded down", () => {
    const s = settlement({ buildings: ["hut", "storehouse", "market"], resources: { wood: 30, food: 10, stone: 5 } });
    const next = sellResource(s, "wood", 7); // 7 / 2 -> 3 stone, rounds down
    expect(next.resources.wood).toBe(23);
    expect(next.resources.stone).toBe(8);
  });

  it("never takes the sold resource below 0", () => {
    const s = settlement({ buildings: ["hut", "storehouse", "market"], resources: { wood: 5, food: 10, stone: 0 } });
    const next = sellResource(s, "wood", 100);
    expect(next.resources.wood).toBe(0);
    expect(next.resources.stone).toBe(2); // sold only the 5 actually available -> floor(5/2)
  });
});
