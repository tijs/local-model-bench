import type { BuildingKind, Resources, ResourceKind } from "../types";
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

/** How much headroom is left before `kind` hits the given cap — 0 if
 * already at or over cap, never negative. */
export function remainingCapacity(resources: Resources, kind: ResourceKind, cap: number): number {
  return Math.max(0, cap - resources[kind]);
}

/** Fraction (0-1) of the cap currently filled for `kind` — used by the
 * CLI to render a "storage nearly full" style warning. A resource that
 * has climbed past the cap (only possible for the still-buggy food case
 * — see clampToStorageCap above) reports 1, not a value above 1, since a
 * warning about being "over 100% full" would be confusing to show. */
export function utilizationOf(resources: Resources, kind: ResourceKind, cap: number): number {
  if (cap <= 0) {
    return resources[kind] > 0 ? 1 : 0;
  }
  return Math.min(1, resources[kind] / cap);
}

/** utilizationOf for every resource kind at once, keyed the same way
 * Resources itself is. */
export function storageUtilization(resources: Resources, cap: number): Record<ResourceKind, number> {
  return {
    wood: utilizationOf(resources, "wood", cap),
    food: utilizationOf(resources, "food", cap),
    stone: utilizationOf(resources, "stone", cap),
  };
}
