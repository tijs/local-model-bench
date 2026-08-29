import type { BuildingDef, BuildingKind } from "../types";

/**
 * The single source of truth for what each building costs and what it
 * requires — buildings/availability.ts and buildings/actions.ts both read
 * from this table rather than hardcoding costs themselves, so adding a new
 * building kind here is enough to make it buildable (assuming the type
 * union in types.ts also lists it).
 */
export const BUILDING_REGISTRY: Record<BuildingKind, BuildingDef> = {
  hut: { cost: { wood: 10 }, requires: null },
  farm: { cost: { wood: 15, stone: 5 }, requires: null },
  quarry: { cost: { wood: 20 }, requires: null },
  storehouse: { cost: { wood: 25, stone: 10 }, requires: "hut" },
};
