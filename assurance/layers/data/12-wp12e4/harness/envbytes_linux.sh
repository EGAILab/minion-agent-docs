#!/bin/sh
# WP-12.E4 audit 2 (WP12E4-AUD-R002): how pinned Node presents non-UTF-8 POSIX environment bytes, and what a child
# receives when Node passes an explicit env object (as Pi's bash does). Each value is produced by printf in the
# parent shell, so Node receives the raw bytes.  Usage: sh envbytes_linux.sh <out.json>
export V_FF="$(printf 'a\377b')" V_E180="$(printf 'a\341\200')" V_F09080="$(printf 'a\360\220\200')" \
  V_EDA080="$(printf 'a\355\240\200b')" V_C0AF="$(printf 'a\300\257b')" V_BOM="$(printf '\357\273\277a')" \
  V_MIX="$(printf '\342\202\254\341\200\342\202\254')" V_E180B="$(printf 'a\341\200b')"
env "$(printf 'N_\377')=name-invalid" "$(printf 'N_\303\251')=name-valid" node -e '
const {spawnSync}=require("child_process");
const u=(s)=>[...Array(s.length).keys()].map(i=>s.charCodeAt(i).toString(16).padStart(4,"0"));
const keys=Object.keys(process.env).filter(k=>/^(V_|N_)/.test(k)).sort();
const out={runtime:process.version,values:{}};
for(const k of keys){
  const child=spawnSync("sh",["-c","env | grep -a \"^"+k.replace(/[^A-Za-z0-9_]/g,".")+"=\" | od -An -tx1 | tr -d \" \n\""],{env:{...process.env},encoding:"utf8"}).stdout;
  out.values[k]={nameUnits:u(k),valueUnits:u(process.env[k]),childLineBytes:child};
}
require("fs").writeFileSync(process.argv[1],JSON.stringify(out,null,1)+"\n");' "$1"
