import type { Settlement, TurnRecord } from "../types";

export function recordTurn(
  before: Settlement,
  after: Settlement,
  raided: boolean,
  drought: boolean,
): TurnRecord {
  return {
    turn: after.turn,
    before: before.resources,
    after: after.resources,
    populationBefore: before.population,
    populationAfter: after.population,
    raided,
    drought,
  };
}

/** Total number of turns in `history` where a raid struck. */
export function raidCount(history: TurnRecord[]): number {
  return history.filter((record) => record.raided).length;
}

/** Total number of turns in `history` where a drought struck. */
export function droughtCount(history: TurnRecord[]): number {
  return history.filter((record) => record.drought).length;
}

/** Net change in population from the first recorded turn's "before" state
 * to the last recorded turn's "after" state — 0 for an empty history. */
export function netPopulationChange(history: TurnRecord[]): number {
  if (history.length === 0) {
    return 0;
  }
  return history[history.length - 1].populationAfter - history[0].populationBefore;
}

/** Net change in a single resource across the whole recorded history,
 * same start/end convention as netPopulationChange. */
export function netResourceChange(history: TurnRecord[], kind: keyof TurnRecord["before"]): number {
  if (history.length === 0) {
    return 0;
  }
  return history[history.length - 1].after[kind] - history[0].before[kind];
}

/** Every turn number on which either a raid or a drought (or both)
 * struck — useful for a CLI timeline view without re-scanning the full
 * history twice for two separate event kinds. */
export function eventfulTurns(history: TurnRecord[]): number[] {
  return history.filter((r) => r.raided || r.drought).map((r) => r.turn);
}
