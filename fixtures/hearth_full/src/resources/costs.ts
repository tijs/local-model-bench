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
