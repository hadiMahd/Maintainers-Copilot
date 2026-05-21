import { execSync } from 'child_process'
import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'
import { gzipSync } from 'zlib'

const distDir = join(import.meta.dirname, '..', 'dist')
const reportPath = join(import.meta.dirname, '..', '..', 'docs', 'widget-bundle-report.md')

function fileSize(path) {
  if (!existsSync(path)) return 0
  return readFileSync(path).length
}

function gzipSize(path) {
  if (!existsSync(path)) return 0
  return gzipSync(readFileSync(path)).length
}

function toKB(bytes) {
  return (bytes / 1024).toFixed(2)
}

// Find loader.js
const loaderPath = join(distDir, 'assets', 'loader.js')
const loaderRaw = fileSize(loaderPath)
const loaderGzip = gzipSize(loaderPath)

// Find initial widget bundle (first .js file in assets/)
const assetDir = join(distDir, 'assets')
const jsFiles = existsSync(assetDir)
  ? execSync(`ls ${assetDir}/*.js 2>/dev/null || true`, { encoding: 'utf8' })
      .trim()
      .split('\n')
      .filter(Boolean)
  : []

const initialBundle = jsFiles.find(f => f.includes('widget-')) || jsFiles[0] || ''
const bundleRaw = initialBundle ? fileSize(initialBundle) : 0
const bundleGzip = initialBundle ? gzipSize(initialBundle) : 0

const standaloneCount = jsFiles.filter(f => f.includes('widget-')).length
const standalone = standaloneCount === 1

const now = new Date().toISOString()

const report = `# Widget Bundle Size Report

**Measured**: ${now}

| Asset | Raw (KB) | Gzip (KB) | Target | Status |
|-------|----------|-----------|--------|--------|
| \`/widget/loader.js\` | ${toKB(loaderRaw)} | ${toKB(loaderGzip)} | < 5 KB | ${loaderGzip < 5120 ? '✅ PASS' : '❌ FAIL'} |
| Initial widget bundle | ${toKB(bundleRaw)} | ${toKB(bundleGzip)} | ≤ 150 KB | ${bundleGzip <= 153600 ? '✅ PASS' : '❌ FAIL'} |

## Standalone Initial JS

- One standalone initial widget JavaScript bundle: ${standalone ? '✅ YES' : '❌ NO'} (${standaloneCount} found)
- Extra initial JS assets: ${jsFiles.length > 1 ? jsFiles.filter(f => f !== initialBundle).map(f => f.split('/').pop()).join(', ') : 'None'}

## Notes

${bundleGzip > 153600 ? '> Bundle exceeds 150 KB gzip target. Review dependencies and consider code splitting.' : ''}
${!standalone ? '> Multiple initial JS bundles detected. Check Vite manualChunks configuration.' : ''}
`

console.log(`Loader: ${toKB(loaderRaw)} KB raw, ${toKB(loaderGzip)} KB gzip`)
console.log(`Bundle: ${toKB(bundleRaw)} KB raw, ${toKB(bundleGzip)} KB gzip`)
console.log(`Standalone initial JS: ${standalone ? 'Yes' : 'No'}`)

writeFileSync(reportPath, report)
console.log(`Report written to ${reportPath}`)
