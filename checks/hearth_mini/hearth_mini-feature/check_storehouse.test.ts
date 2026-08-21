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
    // toEqual([]), not just not.toContain("storehouse") (3rd adversarial
    // review, finding CR3-8): with every resource at 0, hut/farm/quarry
    // are ALSO unaffordable, not just storehouse — the weaker assertion
    // never actually verified that.
    expect(availableBuildings(s)).toEqual([]);
  });

  // Added 2026-08-21 (3rd adversarial review, finding CR3-8): confirmed
  // live that an implementation checking only ONE resource of a
  // multi-resource cost (e.g. only `wood`, silently ignoring `stone`) — a
  // realistic bug, not a contrived one — passed every assertion above.
  // The all-zero-resources case can't catch this because it's short on
  // EVERY resource at once, so a partial check happens to agree with a
  // correct one by coincidence. This isolates a single insufficient
  // resource against an otherwise-plentiful settlement.
  it("excludes storehouse when only ONE required resource is short (wood ok, stone short)", () => {
    const s = settlement({
      buildings: ["hut"],
      resources: { wood: 100, food: 10, stone: 5 },
    });
    const result = availableBuildings(s);
    expect(result).not.toContain("storehouse");
    expect(result).toContain("quarry");
  });

  it("storehouse cost matches spec", () => {
    expect(BUILDING_COSTS.storehouse).toEqual({ wood: 25, stone: 10 });
  });
});
