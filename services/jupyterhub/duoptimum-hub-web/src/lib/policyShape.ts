/* Group policy import/export shape: fold the hub's flat per-group config into the
 * hierarchy group -> policy[] -> members, and unfold it back. The hub stores and
 * validates a single flat config dict; this is purely the on-disk bundle shape so
 * each policy reads as its own named section with its settings inside it. */
import type { PolicyConfig } from '../services/types'

export interface PolicySection {
  key: string // policy type key (matches backend POLICY_TYPES)
  label: string // human section name
  settings: Record<string, unknown> // the policy's members (flat config keys it owns)
}

// Policy sections in backend POLICY_TYPES order; `keys` are the flat config members
// that belong to each section (the section's enable flag is just one of its members).
const SECTIONS: { key: string; label: string; keys: string[] }[] = [
  { key: 'env_vars', label: 'Environment variables', keys: ['env_vars_active', 'env_vars'] },
  { key: 'gpu', label: 'GPU access', keys: ['gpu_access', 'gpu_all', 'gpu_device_ids'] },
  { key: 'docker', label: 'Docker access', keys: ['docker_active', 'docker_access', 'docker_limited', 'docker_privileged', 'docker_limited_max_containers', 'docker_limited_max_volumes', 'docker_limited_max_networks', 'docker_limited_max_storage_gb', 'docker_limited_cpu_cap_cores', 'docker_limited_mem_cap_gb', 'docker_limited_allow_dangerous_flags', 'docker_limited_user_compose_project_enabled', 'docker_limited_user_compose_project_allow_override', 'docker_limited_hub_network_access'] },
  { key: 'cpu', label: 'CPU', keys: ['cpu_limit_enabled', 'cpu_limit_cores'] },
  { key: 'mem', label: 'Memory', keys: ['mem_limit_enabled', 'mem_limit_gb', 'mem_swap_disabled'] },
  { key: 'sudo', label: 'System', keys: ['sudo_active', 'sudo_enable', 'user_env_enable'] },
  { key: 'downloads', label: 'File downloads', keys: ['downloads_active', 'downloads_allow'] },
  { key: 'api_keys', label: 'API keys pool', keys: ['api_keys_pool'] },
  { key: 'volume_mounts', label: 'Volume mounts', keys: ['volume_mounts_active', 'volume_mounts'] },
]

// flat config -> ordered policy sections, each carrying only its own members
export function toPolicies(config: PolicyConfig): PolicySection[] {
  const c = (config ?? {}) as Record<string, unknown>
  const out: PolicySection[] = []
  for (const s of SECTIONS) {
    const settings: Record<string, unknown> = {}
    for (const k of s.keys) if (k in c) settings[k] = c[k]
    if (Object.keys(settings).length) out.push({ key: s.key, label: s.label, settings })
  }
  return out
}

// policy sections -> flat config (merge every section's members back together)
export function fromPolicies(policies: PolicySection[]): PolicyConfig {
  const flat: Record<string, unknown> = {}
  for (const p of policies ?? []) Object.assign(flat, p.settings ?? {})
  return flat as PolicyConfig
}
