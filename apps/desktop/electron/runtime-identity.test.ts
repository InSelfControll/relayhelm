import assert from 'node:assert/strict'
import { test } from 'vitest'
import { defaultRuntimeHome, desktopProtocol, desktopDeepLinkSchemes } from './runtime-identity'

test('Windows default never adopts the upstream Hermes install', () => {
  const existing = new Set(['C:\\Local\\hermes'])
  assert.equal(defaultRuntimeHome('win32', 'C:\\User', 'C:\\Local', p => existing.has(p)), 'C:\\Local\\relayhelm')
  existing.add('C:\\User\\.relayhelm')
  assert.equal(defaultRuntimeHome('win32', 'C:\\User', 'C:\\Local', p => existing.has(p)), 'C:\\User\\.relayhelm')
  existing.add('C:\\Local\\relayhelm')
  assert.equal(defaultRuntimeHome('win32', 'C:\\User', 'C:\\Local', p => existing.has(p)), 'C:\\Local\\relayhelm')
})

test('POSIX and missing LOCALAPPDATA use the standalone home', () => {
  assert.equal(defaultRuntimeHome('linux', '/home/user', undefined, () => false), '/home/user/.relayhelm')
  assert.equal(defaultRuntimeHome('win32', 'C:\\User', undefined, () => false), 'C:\\User\\.relayhelm')
})

test('packaged and development protocol registration accepts the corresponding Relayhelm links', () => {
  for (const development of [false, true]) {
    assert.ok(desktopDeepLinkSchemes(development).includes(desktopProtocol(development)))
    assert.ok(desktopDeepLinkSchemes(development).includes('relayhelm'))
    assert.ok(!desktopDeepLinkSchemes(development).includes('hermes'))
  }
  assert.equal(desktopProtocol(false), 'relayhelm')
})


test('backend ownership recognizes the new CLI and rejects an upstream CLI', async () => {
  const { backendCommandMatches } = await import('./backend-ownership')
  assert.equal(backendCommandMatches('C:\\Relayhelm\\relayhelm.exe serve --port 0'), true)
  assert.equal(backendCommandMatches('/usr/bin/hermes serve --port 0'), false)
  assert.equal(backendCommandMatches('python -m hermes_cli.main serve --port 0'), true)
})
