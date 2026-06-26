/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

/**
 * CI guard: ensure that the real vm2 package never re-enters the dependency
 * tree. vm2 is unmaintained and has known sandbox-escape CVEs
 * (CVE-2023-37466, CVE-2023-37903).
 *
 * This script is intended to run in CI (e.g. as a pre-merge check) and
 * exits non-zero if a non-stub version of vm2 is found in node_modules.
 */

'use strict';

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const nodeModules = path.resolve(__dirname, '..', 'node_modules');

// Search for any vm2 installations (top-level or nested)
let found = [];
try {
  const result = execSync(
    `find ${nodeModules} -path "*/vm2/package.json" -not -path "*/scripts/stubs/*"`,
    { encoding: 'utf8', timeout: 30000 },
  ).trim();
  if (result) {
    found = result.split('\n').filter(Boolean);
  }
} catch {
  // find returns non-zero if no matches, which is fine
}

if (found.length === 0) {
  console.log('✓ vm2 is not present in node_modules.');
  process.exit(0);
}

// Check each found instance
for (const pkgPath of found) {
  let pkg;
  try {
    pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
  } catch {
    continue;
  }

  if (pkg.version && pkg.version !== '0.0.0-removed') {
    console.error(
      `✗ FATAL: Real vm2@${pkg.version} detected at ${pkgPath}!\n` +
        '  vm2 has known sandbox-escape CVEs and must not be shipped.\n' +
        '  Remove the dependency that pulls it in, or override it with the local stub.\n' +
        '  See: superset-frontend/scripts/stubs/vm2-stub/\n',
    );
    process.exit(1);
  }
}

console.log(
  '✓ vm2 resolved to local stub (0.0.0-removed). No real vm2 in tree.',
);
process.exit(0);
