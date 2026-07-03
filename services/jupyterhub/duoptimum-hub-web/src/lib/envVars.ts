/* Pure helpers for the env-var editor: the same name blacklist the backend enforces
 * (duoptimum_hub_services.policy.base.is_reserved_env_var + user_env_vars._NAME_RE),
 * mirrored client-side so the editor flags a bad/reserved/duplicate name live instead
 * of only failing on save. The backend is still the authority - this is UX. */

export interface EnvReserved { names: string[]; prefixes: string[] }

// mirrors user_env_vars._NAME_RE (a letter/underscore then alnum/underscore)
const NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/

/** Platform/policy-reserved name - an exact match or a reserved prefix. */
export function isReservedEnvName(name: string, reserved?: EnvReserved): boolean {
  const n = name.trim()
  if (!n || !reserved) return false
  if (reserved.names.includes(n)) return true
  return reserved.prefixes.some((p) => p && n.startsWith(p))
}

/** Per-row validation message, or null when the row is fine. A blank name is not an
 * error (the backend drops blank rows). `allNames` is every row's raw name, for dup
 * detection. */
export function envNameError(name: string, allNames: string[], reserved?: EnvReserved): string | null {
  const n = name.trim()
  if (!n) return null
  if (!NAME_RE.test(n)) return 'Invalid name - letters, digits, underscore; not starting with a digit'
  if (isReservedEnvName(n, reserved)) return 'Reserved - controlled by JupyterHub or the platform'
  if (allNames.filter((x) => x.trim() === n).length > 1) return 'Duplicate name'
  return null
}

/** True if any row has a validation error - the page blocks Save on this. */
export function envVarsHaveErrors(rows: { name: string }[], reserved?: EnvReserved): boolean {
  const names = rows.map((r) => r.name)
  return rows.some((r) => envNameError(r.name, names, reserved) !== null)
}
