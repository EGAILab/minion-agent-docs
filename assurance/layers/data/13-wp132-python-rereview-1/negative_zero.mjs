import { readFileSync } from 'node:fs';
const source = readFileSync('/pi/packages/coding-agent/src/core/tools/edit.ts','utf8');
const single = source.slice(source.indexOf('function isSingleEditInput('), source.indexOf('export interface EditToolDetails'));
const prepare = source.slice(source.indexOf('function prepareEditArguments('), source.indexOf('function validateEditInput('));
const stripped = (single + prepare).replaceAll(': unknown','').replace(': value is SingleEditInput','').replace(': EditToolInput','').replaceAll(' as Record<string, unknown>','').replaceAll(' as LegacyEditToolInput','').replaceAll(' as EditToolInput','');
const fn = new Function(stripped + ';return prepareEditArguments;')();
for (const token of ['-0', '-0.0', '-0e0']) {
  const value = fn({path:'f', edits:'{"oldText":"a","newText":"b","extra":' + token + '}' }).edits[0].extra;
  console.log(token, 'negativeZero', Object.is(value, -0), 'reciprocal', 1/value);
}
