import type { Settlement, TurnRecord } from "../types";

export function recordTurn(
  before: Settlement,
  after: Settlement,
  raided: boolean,
): TurnRecord {
  return {
    turn: after.turn,
    before: before.resources,
    after: after.resources,
    populationBefore: before.population,
    populationAfter: after.population,
    raided,
  };
}

/** Total number of turns in `history` where a raid struck. */
export function raidCount(history: TurnRecord[]): number {
  return history.filter((record) => record.raided).length;
}
