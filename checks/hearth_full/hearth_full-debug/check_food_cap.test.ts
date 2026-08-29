import { describe, expect, it } from "vitest";
import { advanceTurn } from "../src/sim/turn";
import type { Settlement } from "../src/types";

describe("food respects storage capacity", () => {
  it("caps food production at the settlement's storage cap, same as wood and stone", () => {
    // No storehouse -> cap is 50. Two farms produce 10 food/turn; with
    // population 0 consuming none, food should climb toward the cap and
    // then hold there, not sail past it.
    let s: Settlement = {
      resources: { wood: 0, food: 45, stone: 0 },
      population: 0,
      buildings: ["farm", "farm"],
      turn: 0,
    };
    for (let i = 0; i < 5; i++) {
      s = advanceTurn(s).settlement;
    }
    expect(s.resources.food).toBeLessThanOrEqual(50);
  });

  it("a storehouse raises the food cap the same way it raises wood/stone caps", () => {
    let s: Settlement = {
      resources: { wood: 0, food: 95, stone: 0 },
      population: 0,
      buildings: ["farm", "farm", "hut", "storehouse"], // cap = 100
      turn: 0,
    };
    for (let i = 0; i < 5; i++) {
      s = advanceTurn(s).settlement;
    }
    expect(s.resources.food).toBeLessThanOrEqual(100);
  });
});
