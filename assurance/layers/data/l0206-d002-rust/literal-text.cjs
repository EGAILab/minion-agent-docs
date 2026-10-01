// Supplement to the merged authority: JSON.parse accepts literal UTF-16 units.
const units = [34, 0xd800, 0xd83d, 0xde00, 0xdc00, 34];
const value = JSON.parse(String.fromCharCode(...units));
console.log(JSON.stringify(Array.from({ length: value.length }, (_, i) => value.charCodeAt(i))));
for (const invalid of [[0xd800], [34, 92, 0xd800, 34]]) {
  try { JSON.parse(String.fromCharCode(...invalid)); throw Error('invalid text accepted'); }
  catch (error) { if (!(error instanceof SyntaxError)) throw error; console.log('rejected'); }
}
