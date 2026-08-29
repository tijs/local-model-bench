import type { Settlement, TurnRecord, BuildingKind } from "../types";
import { storageCap, storageUtilization } from "../resources/storage";
import { stoneOutput, FOOD_PER_FARM, FOOD_PER_POP } from "../resources/production";
import { upgradeTier } from "../buildings/upgrades";
import { raidCount, droughtCount, netPopulationChange } from "./history";

export interface SettlementReport {
  turn: number;
  population: number;
  storageCap: number;
  storageUtilization: Record<string, number>;
  buildingCounts: Partial<Record<BuildingKind, number>>;
  upgradedBuildings: BuildingKind[];
  stoneOutputPerTurn: number;
  foodBalancePerTurn: number;
}

/** How many of each building kind are currently standing, omitting any
 * kind with a count of 0 rather than including it at 0 — a report
 * consumer that wants every kind represented can fall back on
 * buildings/registry.ts's ALL_BUILDING_KINDS itself. */
function countBuildings(buildings: BuildingKind[]): Partial<Record<BuildingKind, number>> {
  const counts: Partial<Record<BuildingKind, number>> = {};
  for (const kind of buildings) {
    counts[kind] = (counts[kind] ?? 0) + 1;
  }
  return counts;
}

/**
 * A point-in-time snapshot of a settlement's overall health — the CLI's
 * `report` subcommand's data source, pulling together storage, building,
 * and production figures that would otherwise need several separate
 * calls stitched together by hand.
 */
export function buildReport(settlement: Settlement): SettlementReport {
  const cap = storageCap(settlement.buildings);
  const upgrades = settlement.upgrades ?? [];
  const uniqueUpgraded = settlement.buildings.filter(
    (kind, index) => upgradeTier(settlement, kind) > 1 && settlement.buildings.indexOf(kind) === index,
  );
  const farms = settlement.buildings.filter((b) => b === "farm").length;
  return {
    turn: settlement.turn,
    population: settlement.population,
    storageCap: cap,
    storageUtilization: storageUtilization(settlement.resources, cap),
    buildingCounts: countBuildings(settlement.buildings),
    upgradedBuildings: uniqueUpgraded,
    stoneOutputPerTurn: stoneOutput(settlement.buildings, upgrades),
    foodBalancePerTurn: farms * FOOD_PER_FARM * (upgrades.includes("farm") ? 2 : 1)
      - settlement.population * FOOD_PER_POP,
  };
}

export interface HistorySummary {
  turnsPlayed: number;
  raids: number;
  droughts: number;
  populationChange: number;
  worstSingleTurnFoodLoss: number;
}

/** Aggregates a full turn history into the handful of numbers a CLI
 * `summary` subcommand would want to print after a long run, instead of
 * making the caller scan the raw per-turn records itself. */
export function summarizeHistory(history: TurnRecord[]): HistorySummary {
  const foodLosses = history.map((r) => Math.max(0, r.before.food - r.after.food));
  return {
    turnsPlayed: history.length,
    raids: raidCount(history),
    droughts: droughtCount(history),
    populationChange: netPopulationChange(history),
    worstSingleTurnFoodLoss: foodLosses.length ? Math.max(...foodLosses) : 0,
  };
}
