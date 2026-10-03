const fs = require('node:fs/promises');
(async () => {
  const observations = [];
  for (const operation of ['readFile', 'stat', 'realpath', 'mkdir', 'rm']) {
    try {
      await fs[operation]('a\uD800\0');
      throw new Error('unexpected success');
    } catch (error) {
      observations.push({operation, code: error.code, hasPath: Object.hasOwn(error, 'path')});
    }
  }
  console.log(JSON.stringify({node: process.version, observations}, null, 2));
})();
