import type { Settlement } from "../types";
import { produceResources, foodSurplus } from "../resources/production";
import { storageCap, clampToStorageCap } from "../resources/storage";
import { applyRaidIfDue } from "./events";

/**
 * Advances one turn: production/consumption happens, resources are capped
 * to current storage capacity, a raid may strike, and population grows by
 * 1 if there was a genuine food surplus this turn (surplus must be
 * strictly positive — merely breaking even does not grow the population).
 */
export function advanceTurn(settlement: Settlement): { settlement: Settlement; raided: boolean } {
  const surplus = foodSurplus(settlement.resources, settlement.buildings, settlement.population);
  const produced = produceResources(settlement.resources, settlement.buildings, settlement.population);
  const cap = storageCap(settlement.buildings);
  const capped = clampToStorageCap(produced, cap);

  const population = surplus > 0 ? settlement.population + 1 : settlement.population;

  const { settlement: afterRaid, raided } = applyRaidIfDue({
    ...settlement,
    resources: capped,
    population,
    turn: settlement.turn + 1,
  });

  return { settlement: afterRaid, raided };
}
