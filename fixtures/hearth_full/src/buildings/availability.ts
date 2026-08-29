import type { BuildingKind, Settlement } from "../types";
import { canAfford } from "../resources/costs";
import { BUILDING_REGISTRY } from "./registry";

/**
 * Every building kind currently both affordable and unlocked (its
 * prerequisite, if any, is already built) — reads entirely from
 * BUILDING_REGISTRY, so a new building kind with a `requires` entry needs
 * no changes here to have its prerequisite enforced.
 */
export function availableBuildings(settlement: Settlement): BuildingKind[] {
  return (Object.keys(BUILDING_REGISTRY) as BuildingKind[]).filter((kind) => {
    const def = BUILDING_REGISTRY[kind];
    if (def.requires && !settlement.buildings.includes(def.requires)) {
      return false;
    }
    return canAfford(settlement.resources, def.cost);
  });
}
