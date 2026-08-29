import type { BuildingKind, Settlement } from "../types";
import { canAfford, deduct } from "../resources/costs";
import { availableBuildings } from "./availability";
import { BUILDING_REGISTRY } from "./registry";

export function build(settlement: Settlement, kind: BuildingKind): Settlement {
  if (!availableBuildings(settlement).includes(kind)) {
    throw new Error(`cannot build ${kind}: unaffordable or prerequisite missing`);
  }
  return {
    ...settlement,
    resources: deduct(settlement.resources, BUILDING_REGISTRY[kind].cost),
    buildings: [...settlement.buildings, kind],
  };
}

/**
 * Repairs an already-built building for half its original cost (rounded up
 * per resource). No-op if the settlement doesn't have that building. Never
 * takes resources below 0.
 */
export function repairBuilding(settlement: Settlement, kind: BuildingKind): Settlement {
  if (!settlement.buildings.includes(kind)) {
    return settlement;
  }
  const cost = BUILDING_REGISTRY[kind].cost;
  const resources = { ...settlement.resources };
  for (const [res, amount] of Object.entries(cost) as [keyof typeof resources, number][]) {
    const repairCost = Math.ceil(amount / 2);
    resources[res] = Math.max(0, resources[res] - repairCost);
  }
  return { ...settlement, resources };
}

/** True if canAfford would allow `kind` ignoring prerequisites — used by
 * availability tests that want to isolate the cost check from the
 * prerequisite check. */
export function affordsCostOnly(settlement: Settlement, kind: BuildingKind): boolean {
  return canAfford(settlement.resources, BUILDING_REGISTRY[kind].cost);
}

/**
 * Removes the FIRST matching instance of `kind` from the settlement,
 * with no resource refund and no effect on any other building of the
 * same kind still standing. A no-op if the settlement doesn't have one.
 * Any tier-2 upgrade recorded for `kind` is also cleared, since it makes
 * no sense for an upgrade to survive its own building's demolition —
 * unless another instance of the same kind is still standing, in which
 * case the upgrade (which is tracked per-kind, not per-instance) stays.
 */
export function demolish(settlement: Settlement, kind: BuildingKind): Settlement {
  const index = settlement.buildings.indexOf(kind);
  if (index === -1) {
    return settlement;
  }
  const buildings = [...settlement.buildings];
  buildings.splice(index, 1);
  const stillStanding = buildings.includes(kind);
  const upgrades = stillStanding
    ? settlement.upgrades
    : settlement.upgrades?.filter((upgraded) => upgraded !== kind);
  return { ...settlement, buildings, upgrades };
}

/** Total count of `kind` currently standing — buildings/registry.ts and
 * resources/production.ts both need "how many of this kind" rather than
 * just "is at least one built," so this is the shared way to ask. */
export function countOf(settlement: Settlement, kind: BuildingKind): number {
  return settlement.buildings.filter((b) => b === kind).length;
}
