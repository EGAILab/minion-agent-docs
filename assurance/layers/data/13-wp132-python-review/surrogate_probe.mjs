const value = String.fromCharCode(0xD83D,0xDE00);
console.log(JSON.stringify({length:value.length,utf8:Buffer.from(value,'utf8').toString('hex'),base64:Buffer.from(value,'utf8').toString('base64')}));
