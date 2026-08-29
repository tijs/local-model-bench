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
 * BUG (mutant 3): rounds the halved repair cost DOWN instead of up — only
 * observable on an odd-numbered cost (e.g. storehouse's wood:25 -> should
 * cost 13 to repair, this mutant charges 12). A test that only exercises
 * even costs, or checks "cost is roughly half" without pinning the exact
 * rounding direction, will not catch this.
 */
export function repairBuilding(settlement: Settlement, kind: BuildingKind): Settlement {
  if (!settlement.buildings.includes(kind)) {
    return settlement;
  }
  const cost = BUILDING_REGISTRY[kind].cost;
  const resources = { ...settlement.resources };
  for (const [res, amount] of Object.entries(cost) as [keyof typeof resources, number][]) {
    const repairCost = Math.floor(amount / 2);
    resources[res] = Math.max(0, resources[res] - repairCost);
  }
  return { ...settlement, resources };
}

export function affordsCostOnly(settlement: Settlement, kind: BuildingKind): boolean {
  return canAfford(settlement.resources, BUILDING_REGISTRY[kind].cost);
}
