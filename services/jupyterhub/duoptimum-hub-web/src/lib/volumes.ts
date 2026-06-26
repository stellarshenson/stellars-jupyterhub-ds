import type { Volume } from '../services/types'

/* Single source of truth for "does this user have manageable volumes" - gates the
 * Manage-volumes affordance everywhere it appears (home hero, mobile, admin list).
 * Pure (no React) so it is unit-testable. */
export function hasVolumes(volumes: Volume[] | undefined | null): boolean {
  return (volumes?.length ?? 0) > 0
}
