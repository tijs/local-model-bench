import type { BuildingKind, Resources, Settlement } from "./types";

export const BUILDING_COSTS: Record<BuildingKind, Partial<Resources>> = {
  hut: { wood: 10 },
  farm: { wood: 15, stone: 5 },
  quarry: { wood: 20 },
};

export function canAfford(settlement: Settlement, kind: BuildingKind): boolean {
  const cost = BUILDING_COSTS[kind];
  return (Object.entries(cost) as [keyof Resources, number][]).every(
    ([res, amount]) => settlement.resources[res] >= amount,
  );
}

export function build(settlement: Settlement, kind: BuildingKind): Settlement {
  if (!canAfford(settlement, kind)) {
    throw new Error(`cannot afford ${kind}`);
  }
  const cost = BUILDING_COSTS[kind];
  const resources = { ...settlement.resources };
  for (const [res, amount] of Object.entries(cost) as [keyof Resources, number][]) {
    resources[res] -= amount;
  }
  return {
    ...settlement,
    resources,
    buildings: [...settlement.buildings, kind],
  };
}

export function advanceTurn(settlement: Settlement): Settlement {
  const farms = settlement.buildings.filter((b) => b === "farm").length;
  const foodProduced = farms * 5;
  const foodConsumed = settlement.population * 2;
  const foodSurplus = foodProduced - foodConsumed;

  let population = settlement.population;
  if (foodSurplus >= 0) {
    population += 1;
  }

  const food = Math.max(0, settlement.resources.food + foodSurplus);
  return {
    ...settlement,
    population,
    resources: { ...settlement.resources, food },
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
  const cost = BUILDING_COSTS[kind];
  const resources = { ...settlement.resources };
  for (const [res, amount] of Object.entries(cost) as [keyof Resources, number][]) {
    resources[res] = Math.max(0, resources[res] - amount);
  }
  return { ...settlement, resources };
}
