import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const pyprojectPath = path.resolve(__dirname, '../pyproject.toml')
const pyprojectContents = fs.readFileSync(pyprojectPath, 'utf8')
const versionMatch = pyprojectContents.match(/^version\s*=\s*"([^"]+)"/m)

if (!versionMatch) {
  throw new Error(`Unable to read project version from ${pyprojectPath}`)
}

const appVersion = versionMatch[1]

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
  server: {
    port: 5173,  // Standard Vite port
  },
  build: {
    outDir: 'dist',
    sourcemap: false, // Disable sourcemaps for production
  }
})
