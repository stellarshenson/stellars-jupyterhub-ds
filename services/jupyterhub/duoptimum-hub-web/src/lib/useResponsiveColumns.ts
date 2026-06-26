import { Grid } from 'antd'

/* antd's per-column `responsive` is NOT honoured by our ProTable / DragSortTable usage
 * (the columns never drop), so we apply the tiers ourselves: drop any column whose
 * `responsive` breakpoints are all inactive at the current width. Reuses the `responsive`
 * metadata already declared on each column. Until the breakpoints resolve on first paint
 * (Grid.useBreakpoint returns {} then updates) we show EVERY column - no flash of missing
 * columns at wide widths. */
type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'xxl'

export function useResponsiveColumns<C extends { responsive?: Breakpoint[] }>(columns: C[]): C[] {
  const screens = Grid.useBreakpoint()
  const known = Object.values(screens).some(Boolean)
  if (!known) return columns
  return columns.filter((c) => !c.responsive || c.responsive.some((bp) => screens[bp]))
}
