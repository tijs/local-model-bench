export type ResourceKind = "wood" | "food" | "stone";
export type Resources = Record<ResourceKind, number>;

export type BuildingKind = "hut" | "farm" | "quarry";

export interface Settlement {
  resources: Resources;
  population: number;
  buildings: BuildingKind[];
}
