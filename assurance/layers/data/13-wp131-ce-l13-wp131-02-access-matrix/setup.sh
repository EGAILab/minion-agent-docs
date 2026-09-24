#!/bin/sh
# Builds the access-matrix fixture as the unprivileged user; run from /probe.
set -e
R=/tmp/fx; rm -rf $R; mkdir -p $R; cd $R
printf 'x' > f_ok; printf 'x' > f_000; chmod 000 f_000
mkdir d_ok d_000 d_x d_r
printf 'x' > d_x/inner; printf 'x' > d_r/inner
chmod 000 d_000; chmod 111 d_x; chmod 444 d_r
ln -s f_ok lk_f_ok; ln -s f_000 lk_f_000; ln -s d_ok lk_d_ok; ln -s d_000 lk_d_000
ln -s missing-target dangling; ln -s loop_b loop_a; ln -s loop_a loop_b
echo ready
