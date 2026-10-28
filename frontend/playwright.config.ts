import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
export default defineConfig({
  testDir: './tests/browser',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: '../artifacts/browser-results.json' }]],
  use: {
    ...devices['Desktop Chrome'],
    channel: 'chromium',
    baseURL: 'http://127.0.0.1:4174',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command:
        'uv run uvicorn browser_app:app --app-dir backend/tests --host 127.0.0.1 --port 8001',
      cwd: root,
      env: { PYTHONPATH: 'backend' },
      url: 'http://127.0.0.1:8001/api/live',
      reuseExistingServer: false,
    },
    {
      command: 'npm run preview -- --port 4174',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' },
      url: 'http://127.0.0.1:4174',
      reuseExistingServer: false,
    },
  ],
});
