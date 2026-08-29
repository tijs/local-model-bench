import type { Settlement } from "../types";
import { produceResources, foodSurplus } from "../resources/production";
import { storageCap, clampToStorageCap } from "../resources/storage";
import { applyRaidIfDue, applyDroughtIfDue } from "./events";

/**
 * Advances one turn, in order: production/consumption happens (upgraded
 * producers count double, see resources/production.ts), resources are
 * capped to current storage capacity, population grows by 1 if there was
 * a genuine food surplus this turn (surplus must be strictly positive —
 * merely breaking even does not grow the population), then a raid may
 * strike, then a drought may strike. Raid and drought are independent —
 * both can land on the same turn if the numbers happen to line up.
 */
export function advanceTurn(settlement: Settlement): { settlement: Settlement; raided: boolean; drought: boolean } {
  const upgrades = settlement.upgrades ?? [];
  const surplus = foodSurplus(settlement.resources, settlement.buildings, settlement.population, upgrades);
  const produced = produceResources(settlement.resources, settlement.buildings, settlement.population, upgrades);
  const cap = storageCap(settlement.buildings);
  const capped = clampToStorageCap(produced, cap);

  const population = surplus > 0 ? settlement.population + 1 : settlement.population;

  const { settlement: afterRaid, raided } = applyRaidIfDue({
    ...settlement,
    resources: capped,
    population,
    turn: settlement.turn + 1,
  });
  const { settlement: afterDrought, drought } = applyDroughtIfDue(afterRaid);

  return { settlement: afterDrought, raided, drought };
}
