import type { Settlement, TurnRecord } from "../types";

export function formatSettlement(settlement: Settlement): string {
  const { wood, food, stone } = settlement.resources;
  return `turn ${settlement.turn} | pop ${settlement.population} | `
    + `wood ${wood} food ${food} stone ${stone} | ${settlement.buildings.join(", ") || "no buildings"}`;
}

export function formatHistory(history: TurnRecord[]): string {
  return history
    .map((r) => `turn ${r.turn}: pop ${r.populationBefore} -> ${r.populationAfter}`
      + (r.raided ? " (RAIDED)" : ""))
    .join("\n");
}
