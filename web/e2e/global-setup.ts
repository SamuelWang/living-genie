import path from 'node:path';
import { spawnSync } from 'node:child_process';

const WEB_API_ROOT = path.resolve(import.meta.dirname, '../../web-api');

export default function globalSetup() {
  const result = spawnSync('uv', ['run', 'python', 'scripts/init_e2e_db.py'], {
    cwd: WEB_API_ROOT,
    stdio: 'inherit',
    env: process.env,
  });

  if (result.status !== 0) {
    throw new Error('Failed to provision the e2e database (scripts/init_e2e_db.py)');
  }
}
