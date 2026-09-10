#!/usr/bin/env bash
# Get the repository ready for Render. Run this once, and again whenever you
# change anything under frontend/.
#
#   bash deploy/prepare.sh
#
# It builds the frontend into frontend/out, checks the build actually
# produced an index.html, and commits it. Then you push.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
echo "Project: $ROOT"

if ! command -v npm > /dev/null; then
  echo "npm not found. Install Node.js 18 or newer from https://nodejs.org and run this again."
  exit 1
fi

echo
echo "[1/4] Installing frontend dependencies"
cd "$ROOT/frontend"
npm ci

echo
echo "[2/4] Building the frontend"
npm run build

echo
echo "[3/4] Checking the build"
if [ ! -f "$ROOT/frontend/out/index.html" ]; then
  echo "FAILED: frontend/out/index.html was not created. Fix the build errors above."
  exit 1
fi
FILES=$(find "$ROOT/frontend/out" -type f | wc -l | tr -d ' ')
echo "OK: frontend/out has $FILES files."

echo
echo "[4/4] Committing the build"
cd "$ROOT"
if [ ! -d .git ]; then
  echo "This folder is not a git repository yet. Run:"
  echo "    git init && git add -A && git commit -m 'N.A.V.'"
  echo "then create an empty repo on GitHub and follow its push instructions."
  exit 0
fi
git add -f frontend/out
git add -A
if git diff --cached --quiet; then
  echo "Nothing changed since the last commit."
else
  git commit -q -m "Build frontend for deployment"
  echo "Committed."
fi

echo
echo "Done. Now run:  git push"
echo "Render redeploys automatically on every push."
