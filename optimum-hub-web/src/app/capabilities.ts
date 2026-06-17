/* Platform capability flags, read synchronously from the hub-injected shell
 * (window.jhdata) so they are available before any fetch. The portal sets these
 * from the hub's startup detection; mock/dev (no jhdata) defaults to "supported"
 * so the design pages and the proxy dev server still demo the GPU widgets. */

/** True when the platform has GPU (the gpuinfo sidecar found one at hub start).
 * Every GPU widget gates on this instead of inferring from a lazy device list. */
export function gpuSupported(): boolean {
  const d = typeof window !== 'undefined' ? window.jhdata : undefined
  return d?.gpu_enabled ?? true
}

/** The platform admin username (JUPYTERHUB_ADMIN), or '' under mock/dev. */
export function adminUser(): string {
  const d = typeof window !== 'undefined' ? window.jhdata : undefined
  return d?.admin_user ?? ''
}

/** Effective admin: the persistent admin flag OR the platform admin username.
 * The platform grants admin at login via post_auth_hook without writing the
 * persistent User.admin row, so `user.admin` alone is False for the real admin. */
export function isAdminUser(name: string, persistentAdmin: boolean): boolean {
  return persistentAdmin || (!!name && name === adminUser())
}
