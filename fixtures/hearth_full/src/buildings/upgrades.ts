import type { BuildingKind, Settlement } from "../types";
import { MAX_UPGRADE_TIER } from "../types";
import { canAfford, deduct } from "../resources/costs";
import { BUILDING_REGISTRY } from "./registry";

/** 1 (base) if `kind` isn't in `settlement.upgrades`, otherwise 2 — there
 * is no tier above 2, so this never returns anything else. */
export function upgradeTier(settlement: Settlement, kind: BuildingKind): number {
  return settlement.upgrades?.includes(kind) ? MAX_UPGRADE_TIER : 1;
}

/**
 * True only if `kind` is actually built, not already upgraded, and the
 * settlement can afford the upgrade cost (the building's own base cost,
 * paid a second time — see BUILDING_REGISTRY).
 */
export function canUpgrade(settlement: Settlement, kind: BuildingKind): boolean {
  if (!settlement.buildings.includes(kind)) {
    return false;
  }
  if (upgradeTier(settlement, kind) >= MAX_UPGRADE_TIER) {
    return false;
  }
  return canAfford(settlement.resources, BUILDING_REGISTRY[kind].cost);
}

/**
 * Upgrades `kind` to tier 2, deducting its base cost again. Throws if
 * canUpgrade would return false — callers should check first if they
 * want to avoid the throw (mirrors buildings/actions.ts's `build`).
 */
export function upgradeBuilding(settlement: Settlement, kind: BuildingKind): Settlement {
  if (!canUpgrade(settlement, kind)) {
    throw new Error(`cannot upgrade ${kind}: not built, already upgraded, or unaffordable`);
  }
  return {
    ...settlement,
    resources: deduct(settlement.resources, BUILDING_REGISTRY[kind].cost),
    upgrades: [...(settlement.upgrades ?? []), kind],
  };
}

/** Every currently-upgradable building kind — built, not yet tier 2, and
 * affordable to upgrade right now. */
export function upgradableBuildings(settlement: Settlement): BuildingKind[] {
  return settlement.buildings.filter((kind) => canUpgrade(settlement, kind));
}
