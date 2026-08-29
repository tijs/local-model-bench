import { describe, expect, it } from "vitest";
import { canAfford, deduct } from "../src/resources/costs";
import { storageCap } from "../src/resources/storage";
import { availableBuildings, build } from "../src/buildings";
import { advanceTurn } from "../src/sim/turn";
import { applyRaidIfDue } from "../src/sim/events";
import type { Settlement } from "../src/types";

function settlement(overrides: Partial<Settlement> = {}): Settlement {
  return {
    resources: { wood: 30, food: 10, stone: 10 },
    population: 2,
    buildings: [],
    turn: 0,
    ...overrides,
  };
}

describe("costs", () => {
  it("affords a hut with enough wood", () => {
    expect(canAfford(settlement().resources, { wood: 10 })).toBe(true);
  });

  it("does not afford a farm without enough stone", () => {
    expect(canAfford({ wood: 30, food: 10, stone: 0 }, { wood: 15, stone: 5 })).toBe(false);
  });

  it("deduct subtracts only the listed resources", () => {
    const result = deduct({ wood: 30, food: 10, stone: 10 }, { wood: 10 });
    expect(result).toEqual({ wood: 20, food: 10, stone: 10 });
  });
});

describe("availableBuildings", () => {
  it("excludes storehouse before a hut is built", () => {
    const result = availableBuildings(settlement({ resources: { wood: 100, food: 10, stone: 100 } }));
    expect(result).not.toContain("storehouse");
    expect(result).toContain("hut");
  });

  it("includes storehouse once a hut is built and affordable", () => {
    const s = settlement({ resources: { wood: 100, food: 10, stone: 100 }, buildings: ["hut"] });
    expect(availableBuildings(s)).toContain("storehouse");
  });
});

describe("build", () => {
  it("deducts cost and adds the building", () => {
    const s = build(settlement(), "hut");
    expect(s.resources.wood).toBe(20);
    expect(s.buildings).toEqual(["hut"]);
  });

  it("throws when the building isn't available", () => {
    expect(() => build(settlement({ resources: { wood: 0, food: 0, stone: 0 } }), "hut")).toThrow();
  });
});

describe("storageCap", () => {
  it("is the base cap with no storehouses", () => {
    expect(storageCap([])).toBe(50);
  });

  it("adds a flat bonus per storehouse built", () => {
    expect(storageCap(["hut", "storehouse", "storehouse"])).toBe(150);
  });
});

describe("advanceTurn", () => {
  it("grows population on a real surplus", () => {
    const s = settlement({
      resources: { wood: 0, food: 10, stone: 0 },
      buildings: ["farm", "farm"], // produces 10, consumes 4 -> surplus 6
      population: 2,
    });
    const { settlement: next } = advanceTurn(s);
    expect(next.population).toBe(3);
  });

  it("does not grow population when food surplus is exactly zero", () => {
    const s = settlement({
      resources: { wood: 0, food: 10, stone: 0 },
      buildings: ["farm", "farm"], // produces 10, consumes 10 -> surplus 0
      population: 5,
    });
    const { settlement: next } = advanceTurn(s);
    expect(next.population).toBe(5);
  });

  it("increments the turn counter", () => {
    const { settlement: next } = advanceTurn(settlement({ turn: 3 }));
    expect(next.turn).toBe(4);
  });
});

describe("applyRaidIfDue", () => {
  it("does not raid a small settlement", () => {
    const { raided } = applyRaidIfDue(settlement({ turn: 5, population: 3 }));
    expect(raided).toBe(false);
  });

  it("raids a large settlement on a due turn", () => {
    const { settlement: after, raided } = applyRaidIfDue(
      settlement({ turn: 5, population: 8, resources: { wood: 0, food: 0, stone: 20 } }),
    );
    expect(raided).toBe(true);
    expect(after.resources.stone).toBe(10);
  });

  it("does not raid on a turn that isn't due", () => {
    const { raided } = applyRaidIfDue(settlement({ turn: 6, population: 8 }));
    expect(raided).toBe(false);
  });
});
