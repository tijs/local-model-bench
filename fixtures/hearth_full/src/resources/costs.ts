import type { Resources } from "../types";

export function canAfford(resources: Resources, cost: Partial<Resources>): boolean {
  return (Object.entries(cost) as [keyof Resources, number][]).every(
    ([res, amount]) => resources[res] >= amount,
  );
}

export function deduct(resources: Resources, cost: Partial<Resources>): Resources {
  const next = { ...resources };
  for (const [res, amount] of Object.entries(cost) as [keyof Resources, number][]) {
    next[res] -= amount;
  }
  return next;
}

/** Adds `amount` to `resources[kind]` — the inverse of deducting a single
 * resource, used by resources/production.ts and sim/trade.ts (added by
 * the market feature) rather than each hand-rolling the spread. */
export function credit(resources: Resources, kind: keyof Resources, amount: number): Resources {
  return { ...resources, [kind]: resources[kind] + amount };
}

/** Sums a list of per-building costs into one combined cost — e.g. "what
 * would it cost to build a farm AND a quarry right now." Partial costs
 * missing a resource are treated as 0 for that resource, same convention
 * canAfford/deduct already use. */
export function totalCost(costs: Partial<Resources>[]): Partial<Resources> {
  const total: Partial<Resources> = {};
  for (const cost of costs) {
    for (const [res, amount] of Object.entries(cost) as [keyof Resources, number][]) {
      total[res] = (total[res] ?? 0) + amount;
    }
  }
  return total;
}

/** How much MORE of each resource would be needed to afford `cost` right
 * now — empty object if already affordable. Never returns a negative
 * amount for a resource that's already sufficient. */
export function shortfall(resources: Resources, cost: Partial<Resources>): Partial<Resources> {
  const missing: Partial<Resources> = {};
  for (const [res, amount] of Object.entries(cost) as [keyof Resources, number][]) {
    const gap = amount - resources[res];
    if (gap > 0) {
      missing[res] = gap;
    }
  }
  return missing;
}
