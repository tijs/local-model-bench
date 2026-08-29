import type { BuildingKind, Resources } from "../types";
import { BASE_STORAGE_CAP, STOREHOUSE_CAP_BONUS } from "../types";

/**
 * The per-resource storage cap: a base amount, plus a bonus for every
 * "storehouse" built (each one adds the same flat bonus — there's no
 * diminishing return for building more than one).
 */
export function storageCap(buildings: BuildingKind[]): number {
  const storehouses = buildings.filter((b) => b === "storehouse").length;
  return BASE_STORAGE_CAP + storehouses * STOREHOUSE_CAP_BONUS;
}

/**
 * Clamps every resource down to the settlement's current storage cap —
 * production beyond capacity is wasted, not stockpiled. Never raises a
 * resource, only lowers it.
 *
 * BUG: only clamps wood and stone, not food — a settlement can stockpile
 * unlimited food regardless of storage capacity.
 */
export function clampToStorageCap(resources: Resources, cap: number): Resources {
  return {
    wood: Math.min(resources.wood, cap),
    food: resources.food,
    stone: Math.min(resources.stone, cap),
  };
}
