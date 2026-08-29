export { advanceTurn } from "./turn";
export {
  applyRaidIfDue, applyDroughtIfDue,
  RAID_INTERVAL, RAID_MIN_POPULATION, RAID_STONE_LOSS, WATCHTOWER_RAID_REDUCTION,
  DROUGHT_INTERVAL, DROUGHT_FOOD_LOSS,
} from "./events";
export {
  recordTurn, raidCount, droughtCount, netPopulationChange, netResourceChange, eventfulTurns,
} from "./history";
export { buildReport, summarizeHistory } from "./report";
export type { SettlementReport, HistorySummary } from "./report";
