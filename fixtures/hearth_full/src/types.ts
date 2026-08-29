export type ResourceKind = "wood" | "food" | "stone";
export type Resources = Record<ResourceKind, number>;

export type BuildingKind = "hut" | "farm" | "quarry" | "storehouse";

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
}

export interface TurnRecord {
  turn: number;
  before: Resources;
  after: Resources;
  populationBefore: number;
  populationAfter: number;
  raided: boolean;
}

export const BASE_STORAGE_CAP = 50;
export const STOREHOUSE_CAP_BONUS = 50;
