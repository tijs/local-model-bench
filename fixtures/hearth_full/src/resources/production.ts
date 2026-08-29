import type { BuildingKind, Resources } from "../types";

export const FOOD_PER_FARM = 5;
export const FOOD_PER_POP = 2;
export const STONE_PER_QUARRY = 3;

/**
 * One turn's raw production and consumption, before any storage-cap
 * clamping is applied (see resources/storage.ts) — farms produce food,
 * quarries produce stone, population eats food. Wood is never produced
 * passively; it only ever decreases (building costs) or is capped.
 */
export function produceResources(resources: Resources, buildings: BuildingKind[], population: number): Resources {
  const farms = buildings.filter((b) => b === "farm").length;
  const quarries = buildings.filter((b) => b === "quarry").length;
  const foodProduced = farms * FOOD_PER_FARM;
  const foodConsumed = population * FOOD_PER_POP;
  return {
    wood: resources.wood,
    food: Math.max(0, resources.food + foodProduced - foodConsumed),
    stone: resources.stone + quarries * STONE_PER_QUARRY,
  };
}

/** Net food surplus this turn would produce, before consumption — used by
 * sim/turn.ts to decide whether population grows. */
export function foodSurplus(resources: Resources, buildings: BuildingKind[], population: number): number {
  const farms = buildings.filter((b) => b === "farm").length;
  return farms * FOOD_PER_FARM - population * FOOD_PER_POP;
}
