import type { BuildingKind, Settlement } from "../types";
import { canAfford } from "../resources/costs";
import { BUILDING_REGISTRY, ALL_BUILDING_KINDS } from "./registry";

/**
 * Every building kind currently both affordable and unlocked (its
 * prerequisite, if any, is already built) — reads entirely from
 * BUILDING_REGISTRY, so a new building kind with a `requires` entry needs
 * no changes here to have its prerequisite enforced.
 */
export function availableBuildings(settlement: Settlement): BuildingKind[] {
  return ALL_BUILDING_KINDS.filter((kind) => {
    const def = BUILDING_REGISTRY[kind];
    if (def.requires && !settlement.buildings.includes(def.requires)) {
      return false;
    }
    return canAfford(settlement.resources, def.cost);
  });
}

/** True if `kind`'s prerequisite (if any) is already built — independent
 * of affordability, unlike availableBuildings. Used by the CLI to
 * distinguish "locked" (prerequisite missing) from "unlocked but too
 * expensive right now." */
export function isUnlocked(settlement: Settlement, kind: BuildingKind): boolean {
  const requires = BUILDING_REGISTRY[kind].requires;
  return requires === null || settlement.buildings.includes(requires);
}

/** Every building kind whose prerequisite is met but that the settlement
 * can't currently afford — the complement of availableBuildings among
 * unlocked kinds. */
export function unlockedButUnaffordable(settlement: Settlement): BuildingKind[] {
  const available = new Set(availableBuildings(settlement));
  return ALL_BUILDING_KINDS.filter((kind) => isUnlocked(settlement, kind) && !available.has(kind));
}

/** Every building kind still locked behind an unmet prerequisite,
 * regardless of affordability. */
export function lockedBuildings(settlement: Settlement): BuildingKind[] {
  return ALL_BUILDING_KINDS.filter((kind) => !isUnlocked(settlement, kind));
}
