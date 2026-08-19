/**
 * BUG (mutant 2): forgets to strip leading/trailing dashes.
 */
export function normalizeTag(tag: string): string {
  return tag
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-");
}

/** Sorts tags by usage count descending, ties broken alphabetically. */
export function sortTagsByUsage(counts: Record<string, number>): string[] {
  return Object.entries(counts)
    .sort(([tagA, countA], [tagB, countB]) => {
      if (countB !== countA) return countB - countA;
      return tagA.localeCompare(tagB);
    })
    .map(([tag]) => tag);
}
