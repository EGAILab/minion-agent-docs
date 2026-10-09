#!/bin/sh
set -eu
export TMP=/tmp TEMP=/tmp TMPDIR=/tmp LD_LIBRARY_PATH=/icu/icu/lib
binary=$(sed -n 's/^.*Running tests\/fs_path_domain.rs (\([^)]*\)).*/\1/p' /logs/test.log | tail -n 1)
test -n "$binary"
runuser -u nobody -- env TMP=/tmp TEMP=/tmp TMPDIR=/tmp LD_LIBRARY_PATH=/icu/icu/lib "$binary" --exact recursive_remove_single_failure_reports_the_inner_native_call --ignored --nocapture > /logs/permission-nonroot.log 2>&1
cat /logs/permission-nonroot.log
