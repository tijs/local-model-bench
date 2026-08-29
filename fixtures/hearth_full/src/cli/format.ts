import type { Settlement, TurnRecord } from "../types";
import { storageCap, storageUtilization } from "../resources/storage";
import { upgradeTier } from "../buildings/upgrades";
import { ALL_BUILDING_KINDS } from "../buildings/registry";

export function formatSettlement(settlement: Settlement): string {
  const { wood, food, stone } = settlement.resources;
  return `turn ${settlement.turn} | pop ${settlement.population} | `
    + `wood ${wood} food ${food} stone ${stone} | ${settlement.buildings.join(", ") || "no buildings"}`;
}

export function formatHistory(history: TurnRecord[]): string {
  return history
    .map((r) => {
      const tags = [r.raided ? "RAIDED" : null, r.drought ? "DROUGHT" : null].filter(Boolean);
      const suffix = tags.length ? ` (${tags.join(", ")})` : "";
      return `turn ${r.turn}: pop ${r.populationBefore} -> ${r.populationAfter}${suffix}`;
    })
    .join("\n");
}

/** One line per built building, noting its tier if upgraded — e.g.
 * "farm (tier 2)" vs plain "farm" for a non-upgraded one. */
export function formatBuildings(settlement: Settlement): string {
  if (settlement.buildings.length === 0) {
    return "no buildings";
  }
  return settlement.buildings
    .map((kind) => {
      const tier = upgradeTier(settlement, kind);
      return tier > 1 ? `${kind} (tier ${tier})` : kind;
    })
    .join(", ");
}

/** A storage-utilization line per resource, as a rounded percentage —
 * e.g. "wood 42% | food 100% | stone 8%". */
export function formatStorageUtilization(settlement: Settlement): string {
  const cap = storageCap(settlement.buildings);
  const utilization = storageUtilization(settlement.resources, cap);
  return (Object.entries(utilization) as [string, number][])
    .map(([kind, fraction]) => `${kind} ${Math.round(fraction * 100)}%`)
    .join(" | ");
}

/** A full multi-line status block combining settlement, building, and
 * storage-utilization summaries — what a CLI's `status` subcommand
 * would print. */
export function formatStatusBlock(settlement: Settlement): string {
  return [
    formatSettlement(settlement),
    `buildings: ${formatBuildings(settlement)}`,
    `storage: ${formatStorageUtilization(settlement)}`,
  ].join("\n");
}

/** Every building kind not yet built, for a "what could I build next"
 * CLI hint — independent of affordability or prerequisites, which
 * buildings/availability.ts already answers separately. */
export function formatUnbuiltKinds(settlement: Settlement): string {
  const unbuilt = ALL_BUILDING_KINDS.filter((kind) => !settlement.buildings.includes(kind));
  return unbuilt.length ? unbuilt.join(", ") : "none — every kind is built at least once";
}
