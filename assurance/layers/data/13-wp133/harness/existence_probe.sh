#!/bin/sh
# WP-13.3 CE-WP133-01 (R003): followed existence. Builds one fixture set, then asks, per path:
#   node: existsSync / access(F_OK) / realpathSync          (pinned Pi's discovery and cwd checks)
#   python: EXEC-007 probe_dir_entry's own OS sequence      (lstat; if S_ISLNK, stat), filesystem.py
#           _probe_dir_entry_sync at minion-agent main 4c735ed6, which canonical_path does not replace
# Run as a NON-ROOT user (permission cases).  Usage: sh existence_probe.sh <node|python> <out.json>
set -e
T=$(mktemp -d); export T; cd "$T"
printf x > file; mkdir dir; ln -s file l_file; ln -s dir l_dir; ln -s missing l_dangling
mkfifo fifo; ln -s fifo l_fifo; mkdir locked; printf x > locked/inner; chmod 000 locked
ln -s l_loop2 l_loop1; ln -s l_loop1 l_loop2
cp /bin/sh unlinked; exec 7<unlinked; rm unlinked
cat > paths.txt <<P
$T/file
$T/dir
$T/dir/
$T/l_file
$T/l_dir
$T/l_dangling
$T/fifo
$T/l_fifo
$T/locked/inner
$T/l_loop1
$T/missing
$T/file/child
/proc/$$/fd/7
P
if [ "$1" = node ]; then
node -e '
const fs=require("fs");const out=[];
const ok=(f)=>{try{f();return true}catch(e){return e.code}};
for(const p of fs.readFileSync("paths.txt","utf8").trim().split("\n")){
 out.push({path:p.replace(process.env.T,"$T").replace(/\/proc\/\d+\//,"/proc/PID/"),existsSync:fs.existsSync(p),
  accessF_OK:ok(()=>fs.accessSync(p,fs.constants.F_OK)),realpath:ok(()=>fs.realpathSync(p))});}
fs.writeFileSync(process.argv[1],JSON.stringify({runtime:process.version,uid:process.getuid(),cases:out},null,1)+"\n");' "$2"
else
python3 -c '
import os, stat, json, sys, errno
out=[]
for p in open("paths.txt").read().split():
    try:
        st=os.lstat(p)
        if stat.S_ISLNK(st.st_mode): os.stat(p)
        r=True
    except OSError as e: r=errno.errorcode[e.errno]
    try: os.path.realpath(p, strict=True); rp=True
    except OSError as e: rp=errno.errorcode[e.errno]
    q=p.replace(os.environ["T"],"$T")
    import re; q=re.sub(r"/proc/\d+/","/proc/PID/",q)
    out.append({"path":q,"probe_dir_entry_ok":r,"canonical_path":rp})
json.dump({"runtime":sys.version.split()[0],"uid":os.getuid(),"cases":out},open(sys.argv[1],"w"),indent=1); open(sys.argv[1],"a").write("\n")' "$2"
fi
