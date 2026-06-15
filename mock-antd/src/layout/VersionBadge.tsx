import { VERSION } from '../theme/tokens'

export function VersionBadge() {
  return (
    <div className="oh-version-badge" title="OptimumHub version">
      OptimumHub {VERSION}
    </div>
  )
}
