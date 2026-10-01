import { validateToolArguments } from '/tmp/s/pi/ai/src/utils/validation.ts';
const tool = {name:'probe', parameters:{type:'object',properties:{limit:{type:'number'}},required:['limit']}};
const arguments_ = {limit:Infinity,extra:NaN,negativeZero:-0};
try {
  validateToolArguments(tool,{name:'probe',arguments:arguments_});
  throw Error('Expected validation failure');
} catch (e) {
  console.log(e.message);
  if (!e.message.includes('"limit": null') || !e.message.includes('"extra": null') || !e.message.includes('"negativeZero": 0')) throw e;
}
console.log('runtime originals:',arguments_.limit===Infinity,Number.isNaN(arguments_.extra),Object.is(arguments_.negativeZero,-0));
