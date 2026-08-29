import type { BuildingDef, BuildingKind } from "../types";

/**
 * The single source of truth for what each building costs and what it
 * requires — buildings/availability.ts and buildings/actions.ts both read
 * from this table rather than hardcoding costs themselves, so adding a new
 * building kind here is enough to make it buildable (assuming the type
 * union in types.ts also lists it).
 *
 * Prerequisite chain, for reference: hut -> storehouse -> watchtower.
 * quarry -> mine is a separate branch (mine is a heavier stone producer
 * that assumes a quarry's basic infrastructure already exists).
 */
export const BUILDING_REGISTRY: Record<BuildingKind, BuildingDef> = {
  hut: { cost: { wood: 10 }, requires: null },
  farm: { cost: { wood: 15, stone: 5 }, requires: null },
  quarry: { cost: { wood: 20 }, requires: null },
  storehouse: { cost: { wood: 25, stone: 10 }, requires: "hut" },
  watchtower: { cost: { wood: 15, stone: 20 }, requires: "storehouse" },
  mine: { cost: { wood: 30, stone: 10 }, requires: "quarry" },
};

/** Every building kind, in a stable declaration order — used by CLI
 * summaries and tests that want to iterate the whole registry rather
 * than hardcode the kind list a second time. */
export const ALL_BUILDING_KINDS = Object.keys(BUILDING_REGISTRY) as BuildingKind[];

export type BuildingCategory = "shelter" | "production" | "storage" | "defense";

/**
 * A rough role classification per building kind, independent of
 * BUILDING_REGISTRY's cost/prerequisite data — used by the CLI to group
 * a settlement's buildings under a heading instead of listing them as
 * one flat, unlabeled list. Deliberately a separate table rather than a
 * new field on BuildingDef: cost/prerequisite are load-bearing simulation
 * data every function in this module depends on, while category is
 * purely a presentation concern that only cli/format.ts should care
 * about.
 */
export const BUILDING_CATEGORY: Record<BuildingKind, BuildingCategory> = {
  hut: "shelter",
  farm: "production",
  quarry: "production",
  mine: "production",
  storehouse: "storage",
  watchtower: "defense",
};

/** Every built building kind matching `category`, in the settlement's own
 * building order (not ALL_BUILDING_KINDS's declaration order) — a plain
 * filter is all this needs, this exists so callers don't have to import
 * BUILDING_CATEGORY themselves just to write the same one-liner. */
export function buildingsInCategory(buildings: BuildingKind[], category: BuildingCategory): BuildingKind[] {
  return buildings.filter((kind) => BUILDING_CATEGORY[kind] === category);
}
