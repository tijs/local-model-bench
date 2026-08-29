import type { BuildingKind, Resources } from "../types";
import { UPGRADE_OUTPUT_MULTIPLIER } from "../types";

export const FOOD_PER_FARM = 5;
export const FOOD_PER_POP = 2;
export const STONE_PER_QUARRY = 3;
export const STONE_PER_MINE = 6;

/** 2 if `kind` is in `upgrades`, otherwise 1 — the shared multiplier both
 * produceResources and foodSurplus apply per upgraded producer. Kept here
 * (rather than importing buildings/upgrades.ts, which itself imports
 * resources/costs.ts) to avoid a resources-depends-on-buildings-depends-
 * on-resources import cycle; buildings/upgrades.ts is the authority on
 * whether a given upgrade is legal to apply, this is just "how much more
 * output does an upgraded producer make." */
function multiplierFor(kind: BuildingKind, upgrades: BuildingKind[]): number {
  return upgrades.includes(kind) ? UPGRADE_OUTPUT_MULTIPLIER : 1;
}

/**
 * One turn's raw production and consumption, before any storage-cap
 * clamping is applied (see resources/storage.ts) — farms produce food,
 * quarries and mines produce stone (mines produce more, per STONE_PER_MINE
 * vs STONE_PER_QUARRY, reflecting their higher build cost), population
 * eats food. Wood is never produced passively; it only ever decreases
 * (building costs) or is capped. `upgrades` defaults to none, matching
 * every settlement that predates the upgrade mechanic.
 */
export function produceResources(
  resources: Resources,
  buildings: BuildingKind[],
  population: number,
  upgrades: BuildingKind[] = [],
): Resources {
  const farms = buildings.filter((b) => b === "farm").length;
  const quarries = buildings.filter((b) => b === "quarry").length;
  const mines = buildings.filter((b) => b === "mine").length;
  const foodProduced = farms * FOOD_PER_FARM * multiplierFor("farm", upgrades);
  const foodConsumed = population * FOOD_PER_POP;
  const stoneProduced = quarries * STONE_PER_QUARRY * multiplierFor("quarry", upgrades)
    + mines * STONE_PER_MINE * multiplierFor("mine", upgrades);
  return {
    wood: resources.wood,
    food: Math.max(0, resources.food + foodProduced - foodConsumed),
    stone: resources.stone + stoneProduced,
  };
}

/** Net food surplus this turn would produce, before consumption — used by
 * sim/turn.ts to decide whether population grows. */
export function foodSurplus(
  resources: Resources,
  buildings: BuildingKind[],
  population: number,
  upgrades: BuildingKind[] = [],
): number {
  const farms = buildings.filter((b) => b === "farm").length;
  return farms * FOOD_PER_FARM * multiplierFor("farm", upgrades) - population * FOOD_PER_POP;
}

/** Raw stone output this turn would produce (quarries + mines, upgrade-
 * adjusted), independent of any storage cap — used by the CLI to explain
 * to a player why their stone stopped climbing even though they still
 * have producers running. */
export function stoneOutput(buildings: BuildingKind[], upgrades: BuildingKind[] = []): number {
  const quarries = buildings.filter((b) => b === "quarry").length;
  const mines = buildings.filter((b) => b === "mine").length;
  return quarries * STONE_PER_QUARRY * multiplierFor("quarry", upgrades)
    + mines * STONE_PER_MINE * multiplierFor("mine", upgrades);
}
