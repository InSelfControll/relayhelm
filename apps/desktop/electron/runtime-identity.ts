import path from 'node:path'

/** Public identity shared by packaged and development protocol registration. */
export function desktopProtocol(development: boolean): string {
  return development ? 'relayhelm-dev' : 'relayhelm'
}

export function desktopDeepLinkSchemes(development: boolean): string[] {
  return development ? ['relayhelm-dev', 'relayhelm'] : ['relayhelm']
}

/** Match the Python/installers' defaults without adopting upstream Hermes state. */
export function defaultRuntimeHome(
  platform: string,
  home: string,
  localAppData: string | undefined,
  directoryExists: (candidate: string) => boolean
): string {
  const paths = platform === 'win32' ? path.win32 : path.posix
  const legacy = paths.join(home, '.relayhelm')
  if (platform === 'win32' && localAppData) {
    const current = paths.join(localAppData, 'relayhelm')
    return !directoryExists(current) && directoryExists(legacy) ? legacy : current
  }
  return legacy
}
