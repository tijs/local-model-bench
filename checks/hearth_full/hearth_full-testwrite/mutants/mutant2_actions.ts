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
 * BUG (mutant 2): forgets to halve the cost, deducts the full repair cost
 * instead of half.
 */
export function repairBuilding(settlement: Settlement, kind: BuildingKind): Settlement {
  if (!settlement.buildings.includes(kind)) {
    return settlement;
  }
  const cost = BUILDING_REGISTRY[kind].cost;
  const resources = { ...settlement.resources };
  for (const [res, amount] of Object.entries(cost) as [keyof typeof resources, number][]) {
    resources[res] = Math.max(0, resources[res] - amount);
  }
  return { ...settlement, resources };
}

export function affordsCostOnly(settlement: Settlement, kind: BuildingKind): boolean {
  return canAfford(settlement.resources, BUILDING_REGISTRY[kind].cost);
}
