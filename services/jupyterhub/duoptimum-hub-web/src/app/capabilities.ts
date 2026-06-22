/* Platform capability flags, read synchronously from the hub-injected shell
 * (window.jhdata) so they are available before any fetch. The portal sets these
 * from the hub's startup detection; mock/dev (no jhdata) defaults to "supported"
 * so the design pages and the proxy dev server still demo the GPU widgets. */

/** True when the platform has GPU (the gpuinfo sidecar found one at hub start).
 * Every GPU widget gates on this instead of inferring from a lazy device list. */
export function gpuSupported(): boolean {
  const d = typeof window !== 'undefined' ? window.jhdata : undefined
  // Live shell (jhdata present) is authoritative - hide GPU widgets unless the
  // hub flagged a GPU. Only mock/dev (no jhdata) defaults to supported for demos.
  return d ? !!d.gpu_enabled : true
}

/** The platform admin username (JUPYTERHUB_ADMIN_USERNAME), or '' under mock/dev. */
export function adminUser(): string {
  const d = typeof window !== 'undefined' ? window.jhdata : undefined
  return d?.admin_user ?? ''
}

/** Configurable hub display name (JUPYTERHUB_BRANDING_HUB_NAME) - the logo tooltip and the
 * login/signup screen text. Falls back to the product default when unset (mock/dev
 * or an empty env value). */
export function hubName(): string {
  const d = typeof window !== 'undefined' ? window.jhdata : undefined
  return d?.hub_name || 'DuOptimum Hub'
}

/** Effective admin: the persistent admin flag OR the platform admin username.
 * The platform grants admin at login via post_auth_hook without writing the
 * persistent User.admin row, so `user.admin` alone is False for the real admin. */
export function isAdminUser(name: string, persistentAdmin: boolean): boolean {
  return persistentAdmin || (!!name && name === adminUser())
}
