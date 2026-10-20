#!/usr/bin/env bash
# Creates this repository's releases from the files make-fixtures.py wrote into DIR.
# Run once; the releases are meant to stay as they are.
#
#   ./publish.sh dist
set -euo pipefail

dir=${1:?usage: publish.sh DIR}
# Publishing order matters: v1.2.1 is a hotfix released after v1.3.0.
tags=(v1.0.0 v1.1.0 v1.2.0 v1.3.0 v1.2.1 v1.4.0-rc.1)

for tag in "${tags[@]}"; do
  flags=()
  [[ $tag == *-* ]] && flags+=(--prerelease)
  gh release create "$tag" "$dir/$tag"/* \
    --target main \
    --title "$tag" \
    --notes "Fixture release for the Kiff action's tests. Do not edit or delete." \
    ${flags[@]+"${flags[@]}"}
  # Keeps the publish times in order to the second.
  sleep 2
done
