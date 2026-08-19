import { describe, expect, it } from "vitest";
import { advanceTurn } from "../src/sim";
import type { Settlement } from "../src/types";

describe("advanceTurn population growth", () => {
  it("does not grow population when food surplus is exactly zero", () => {
    const s: Settlement = {
      resources: { wood: 0, food: 10, stone: 0 },
      population: 5,
      buildings: ["farm", "farm"], // produces 10 food, consumes 10 -> surplus 0
    };
    const next = advanceTurn(s);
    expect(next.population).toBe(5);
  });

  it("still grows population when there is a real surplus", () => {
    const s: Settlement = {
      resources: { wood: 0, food: 10, stone: 0 },
      population: 2,
      buildings: ["farm", "farm"], // produces 10, consumes 4 -> surplus 6
    };
    const next = advanceTurn(s);
    expect(next.population).toBe(3);
  });
});
