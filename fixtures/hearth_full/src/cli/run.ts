import type { Settlement, TurnRecord } from "../types";
import { advanceTurn } from "../sim/turn";
import { recordTurn } from "../sim/history";

/** Runs the simulation forward `turns` times from `initial`, returning the
 * final settlement and a full per-turn history. */
export function simulate(initial: Settlement, turns: number): { settlement: Settlement; history: TurnRecord[] } {
  let current = initial;
  const history: TurnRecord[] = [];
  for (let i = 0; i < turns; i++) {
    const before = current;
    const { settlement: after, raided, drought } = advanceTurn(current);
    history.push(recordTurn(before, after, raided, drought));
    current = after;
  }
  return { settlement: current, history };
}

/**
 * Like simulate, but stops early (returning fewer than `maxTurns` turns of
 * history) the moment `stopWhen` returns true for the settlement AFTER a
 * given turn — useful for "run until population hits N" style CLI
 * commands without the caller having to post-process a full-length run.
 */
export function simulateUntil(
  initial: Settlement,
  maxTurns: number,
  stopWhen: (settlement: Settlement) => boolean,
): { settlement: Settlement; history: TurnRecord[] } {
  let current = initial;
  const history: TurnRecord[] = [];
  for (let i = 0; i < maxTurns; i++) {
    const before = current;
    const { settlement: after, raided, drought } = advanceTurn(current);
    history.push(recordTurn(before, after, raided, drought));
    current = after;
    if (stopWhen(current)) {
      break;
    }
  }
  return { settlement: current, history };
}
