export type ResourceKind = "wood" | "food" | "stone";
export type Resources = Record<ResourceKind, number>;

export type BuildingKind = "hut" | "farm" | "quarry" | "storehouse" | "watchtower" | "mine";

export interface BuildingDef {
  cost: Partial<Resources>;
  /** Another building that must already exist before this one is
   * available, or null if there's no prerequisite. */
  requires: BuildingKind | null;
}

export interface Settlement {
  resources: Resources;
  population: number;
  buildings: BuildingKind[];
  /** How many turns have elapsed — used by event scheduling. */
  turn: number;
  /**
   * Which built buildings have been upgraded to tier 2 — optional and
   * omitted entirely by most callers/tests, since tier defaults to 1
   * (no bonus) for anything not listed here. A building must appear in
   * `buildings` before it can appear here; see buildings/upgrades.ts.
   */
  upgrades?: BuildingKind[];
}

export interface TurnRecord {
  turn: number;
  before: Resources;
  after: Resources;
  populationBefore: number;
  populationAfter: number;
  raided: boolean;
  drought: boolean;
}

export const BASE_STORAGE_CAP = 50;
export const STOREHOUSE_CAP_BONUS = 50;

/** Building an already-built kind's upgrade costs its own base cost
 * again — see buildings/upgrades.ts. Only tiers 1 (base) and 2 (upgraded)
 * exist; there is no tier 3. */
export const MAX_UPGRADE_TIER = 2;
export const UPGRADE_OUTPUT_MULTIPLIER = 2;
