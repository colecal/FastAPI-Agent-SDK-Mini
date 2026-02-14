#!/usr/bin/env bash
set -euo pipefail

# Build a GitHub Pages-friendly static bundle into ./docs
# Source of truth: ./static

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

rm -rf docs
mkdir -p docs
cp -a static/. docs/

# Make Pages serve files as-is (no Jekyll processing)
touch docs/.nojekyll

# Safety patch: ensure assets are relative so it works under /<repo>/
perl -0777 -i -pe 's#href="/styles\.css"#href="./styles.css"#g; s#src="/app\.js"#src="./app.js"#g; s#href="/docs"#href="./"#g; s#href="/api/#href="./api/#g; s#fetch\('/api/#fetch\('./api/#g' docs/index.html docs/app.js 2>/dev/null || true
