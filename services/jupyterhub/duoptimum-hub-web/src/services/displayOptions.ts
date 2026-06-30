/* The options-harness registry: a declarative description of the per-user settings
 * the Settings page renders as accordion panels (one table of feature -> control per
 * panel). Adding an option is one entry here - no new UI code. The PrefsContext
 * persists the chosen values per user (server-side live, localStorage in mock) and
 * resolves stored values against these defaults. The first panel, Display Options,
 * exposes how CPU is normalised on each surface; the chosen mode is read at render
 * by the consuming components (see ServerHero / Home / Servers). */

export type PrefValue = string | number | boolean
export type RawPrefs = Record<string, PrefValue>

interface OptionChoice { value: string; label: string }
interface OptionControl { kind: 'segmented' | 'switch' | 'select' | 'input'; choices?: OptionChoice[] }
export interface DisplayOption { key: string; label: string; help?: string; control: OptionControl; default: PrefValue }
export interface DisplayPanel { key: string; title: string; defaultOpen?: boolean; options: DisplayOption[] }

const CPU_MODE_CHOICES: OptionChoice[] = [
  { value: 'normalized', label: 'Total normalized (0-100%)' },
  { value: 'cores', label: 'Core aggregate (0-N x 100%)' },
]
const CPU_MODE_HELP = 'Total normalized shows a 0-100% figure; core aggregate shows docker/top cores-used (100% = one core, e.g. 1300% = ~13 cores).'

export const SETTINGS_PANELS: DisplayPanel[] = [
  {
    key: 'display',
    title: 'Display Options',
    defaultOpen: false,
    options: [
      // defaults match the CURRENT behaviour so nothing changes until the user opts in:
      // the two status bars are normalised today, the Servers cells show cores-used.
      { key: 'cpuModeServerStatus', label: 'My Server Status CPU', help: CPU_MODE_HELP, control: { kind: 'segmented', choices: CPU_MODE_CHOICES }, default: 'normalized' },
      { key: 'cpuModeHostStatus', label: 'Host Status CPU', help: CPU_MODE_HELP, control: { kind: 'segmented', choices: CPU_MODE_CHOICES }, default: 'normalized' },
      { key: 'cpuModeServersList', label: 'Servers list & widget CPU', help: CPU_MODE_HELP, control: { kind: 'segmented', choices: CPU_MODE_CHOICES }, default: 'cores' },
    ],
  },
]

const ALL_OPTIONS: DisplayOption[] = SETTINGS_PANELS.flatMap((p) => p.options)
export const PREF_DEFAULTS: RawPrefs = Object.fromEntries(ALL_OPTIONS.map((o) => [o.key, o.default]))
