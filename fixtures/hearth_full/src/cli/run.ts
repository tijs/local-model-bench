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
    const { settlement: after, raided } = advanceTurn(current);
    history.push(recordTurn(before, after, raided));
    current = after;
  }
  return { settlement: current, history };
}
