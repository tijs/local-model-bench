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
