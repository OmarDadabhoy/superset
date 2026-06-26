'use strict';

/**
 * Stub for vm2 – this package has been removed from the Superset dependency
 * tree due to known sandbox-escape CVEs (CVE-2023-37466, CVE-2023-37903).
 *
 * If you see this error, a transitive dependency attempted to use vm2 at
 * runtime. Please open an issue or find an alternative that does not rely
 * on vm2.
 */

const MSG =
  'vm2 has been removed from Superset due to critical CVEs. ' +
  'See https://github.com/nicknisi/vm2/issues/533';

class VM {
  constructor() {
    throw new Error(MSG);
  }
}

class VMScript {
  constructor() {
    throw new Error(MSG);
  }
}

class NodeVM {
  constructor() {
    throw new Error(MSG);
  }
}

module.exports = { VM, VMScript, NodeVM };
