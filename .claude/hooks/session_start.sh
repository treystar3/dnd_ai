#!/usr/bin/env bash
# Printed into Claude's context at the start of every session: the facts it needs before touching anything.
v=$(python -c 'import sys;print("%d.%d"%sys.version_info[:2])')
echo "Python: $v (the code needs 3.12+)"
echo "Branch: $(git rev-parse --abbrev-ref HEAD), last commit: $(git log -1 --format='%h %s')"
echo "Highest feature number in the code: f$(grep -rhoE '\(f[0-9]{3,4}' --include='*.py' . | tr -d '(f' | sort -n | tail -1)"
echo "Uncommitted files: $(git status --porcelain | wc -l)"
