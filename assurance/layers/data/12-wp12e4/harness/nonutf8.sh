#!/bin/sh
# parent env holds BAD=0x61 0xFF 0x62; Node copies process.env into an explicit env object (as Pi's getShellEnv does) and spawns od
BAD="$(printf 'a\377b')" node -e '
const {spawnSync}=require("child_process");
const v=process.env.BAD; const units=[...Array(v.length).keys()].map(i=>v.charCodeAt(i).toString(16));
const explicit=spawnSync("sh",["-c","printf %s \"$BAD\" | od -An -tx1"],{env:{...process.env},encoding:"utf8"}).stdout.trim();
const inherited=spawnSync("sh",["-c","printf %s \"$BAD\" | od -An -tx1"],{encoding:"utf8"}).stdout.trim();
console.log(JSON.stringify({parentUnits:units, childBytesExplicitEnv:explicit, childBytesDefaultEnv:inherited}));'
