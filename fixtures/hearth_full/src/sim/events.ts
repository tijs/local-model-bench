import type { Settlement } from "../types";

export const RAID_INTERVAL = 5;
export const RAID_MIN_POPULATION = 8;
export const RAID_STONE_LOSS = 10;

/**
 * A raid strikes every RAID_INTERVAL turns, but only once the settlement is
 * large enough to be worth raiding (population >= RAID_MIN_POPULATION) —
 * deterministic (a function of turn number and population, not randomness)
 * so the simulation stays reproducible and testable. Never takes stone
 * below 0.
 */
export function applyRaidIfDue(settlement: Settlement): { settlement: Settlement; raided: boolean } {
  const due = settlement.turn > 0
    && settlement.turn % RAID_INTERVAL === 0
    && settlement.population >= RAID_MIN_POPULATION;
  if (!due) {
    return { settlement, raided: false };
  }
  return {
    settlement: {
      ...settlement,
      resources: {
        ...settlement.resources,
        stone: Math.max(0, settlement.resources.stone - RAID_STONE_LOSS),
      },
    },
    raided: true,
  };
}
