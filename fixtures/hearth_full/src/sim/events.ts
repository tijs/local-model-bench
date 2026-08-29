import type { Settlement } from "../types";

export const RAID_INTERVAL = 5;
export const RAID_MIN_POPULATION = 8;
export const RAID_STONE_LOSS = 10;
/** A watchtower halves raid losses (rounded down) — it does not prevent
 * a raid from being "due," only softens the damage once one lands. */
export const WATCHTOWER_RAID_REDUCTION = 2;

export const DROUGHT_INTERVAL = 11;
export const DROUGHT_FOOD_LOSS = 8;

/**
 * A raid strikes every RAID_INTERVAL turns, but only once the settlement is
 * large enough to be worth raiding (population >= RAID_MIN_POPULATION) —
 * deterministic (a function of turn number and population, not randomness)
 * so the simulation stays reproducible and testable. Never takes stone
 * below 0. A watchtower halves the loss (rounded down) but does not
 * change whether a raid is due in the first place.
 */
export function applyRaidIfDue(settlement: Settlement): { settlement: Settlement; raided: boolean } {
  const due = settlement.turn > 0
    && settlement.turn % RAID_INTERVAL === 0
    && settlement.population >= RAID_MIN_POPULATION;
  if (!due) {
    return { settlement, raided: false };
  }
  const hasWatchtower = settlement.buildings.includes("watchtower");
  const loss = hasWatchtower
    ? Math.floor(RAID_STONE_LOSS / WATCHTOWER_RAID_REDUCTION)
    : RAID_STONE_LOSS;
  return {
    settlement: {
      ...settlement,
      resources: {
        ...settlement.resources,
        stone: Math.max(0, settlement.resources.stone - loss),
      },
    },
    raided: true,
  };
}

/**
 * A drought strikes every DROUGHT_INTERVAL turns, unconditionally
 * (unlike raids, it isn't gated on population — a drought doesn't care
 * how big the settlement is), reducing food by a flat amount. Also
 * deterministic, for the same testability reason as raids. Never takes
 * food below 0.
 */
export function applyDroughtIfDue(settlement: Settlement): { settlement: Settlement; drought: boolean } {
  const due = settlement.turn > 0 && settlement.turn % DROUGHT_INTERVAL === 0;
  if (!due) {
    return { settlement, drought: false };
  }
  return {
    settlement: {
      ...settlement,
      resources: {
        ...settlement.resources,
        food: Math.max(0, settlement.resources.food - DROUGHT_FOOD_LOSS),
      },
    },
    drought: true,
  };
}
