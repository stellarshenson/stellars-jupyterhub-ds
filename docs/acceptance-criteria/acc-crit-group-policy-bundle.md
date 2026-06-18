# Acceptance Criteria - group policy import/export bundle shape

The group policy export/import bundle uses the hierarchy group -> policy[] -> members instead of one flat per-group `config` dict. Each policy is a named section carrying its own settings. The hub still stores and validates a single flat config, so this is purely the on-disk bundle shape, folded on export and unfolded on import.

- [x] **Folded export** - export emits `{groups:[{name, description, priority, policies:[{key, label, settings}]}]}`; each policy carries only the flat keys it owns
  - log: 2026-06-17 `toPolicies` in `lib/policyShape.ts`; `GroupsExport.tsx`
- [x] **Nine sections in backend order** - env_vars, gpu, docker, cpu, mem, sudo, downloads, api_keys, volume_mounts; key ownership matches the backend POLICY_TYPES
  - log: 2026-06-17 `SECTIONS` table
- [x] **Unfolded import** - import merges every section's `settings` back into the flat config the hub PUTs
  - log: 2026-06-17 `fromPolicies`; `Groups.tsx` import maps `policies` -> `config`
- [x] **Round-trips** - an exported bundle re-imports through the same flat config the editor PUTs (hub coerces + validates)
  - log: 2026-06-17 fold/unfold are inverse over the owned keys
- [x] **Legacy bundles still import** - a file with a flat `config` (older export) is still accepted
  - log: 2026-06-17 import uses `policies` when present, else `config`
- [x] **Edge: malformed file** - non-JSON / shapeless file shows "Import failed: …" and writes nothing; same file re-pickable
  - log: 2026-06-17 parse guarded before any write (unchanged)
- [x] **Edge: api_keys nested object** - the `api_keys_pool` nested object travels whole inside the api_keys policy's settings
  - log: 2026-06-17 single-key section
