#!/usr/bin/env bash
#
# Rebuild the compiled Greek stemlibs (steminds/, endtables/, derivs/) from
# stemsrc/. Run after editing a stemsrc file (e.g. adding nom.biblical) or after
# scripts/build_biblical_stemlib.py.
#
# Requires the analyzer tools: run scripts/build.sh first.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

EXTRA=""
if [ "$(uname -s)" = "Darwin" ]; then
  SDK=""
  for candidate in /Applications/Xcode*.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk; do
    if [ -d "$candidate" ]; then SDK="$candidate"; break; fi
  done
  if [ -n "$SDK" ] && [ -d "$SDK" ]; then
    export SDKROOT="$SDK"
    EXTRA="-isysroot $SDK"
  fi
fi
export CFLAGS="${CFLAGS:-}-std=gnu89 -fcommon -Wno-return-type -Wno-implicit-function-declaration \
-Wno-incompatible-function-pointer-types -Wno-int-conversion -Wno-implicit-int \
-Wno-deprecated-non-prototype ${EXTRA}"

# The stemlib build needs the (non-flex) dictionary tools on PATH.
( cd "$ROOT/src/gkdict" && make indexnoms indexcomps indexvbs newlems newlems2 )
cp "$ROOT/src/gkdict/indexnoms" "$ROOT/src/gkdict/indexcomps" "$ROOT/src/gkdict/indexvbs" \
   "$ROOT/src/gkdict/newlems" "$ROOT/src/gkdict/newlems2" "$ROOT/bin/"

cd "$ROOT/stemlib/Greek"
export PATH="$PATH:$ROOT/bin"
export MORPHLIB="$ROOT/stemlib"
# Incremental: rebuilds only what changed (a full `make clean` also regenerates
# the ending tables, which differ between build environments and add noise).
make
make
echo "Rebuilt $ROOT/stemlib/Greek"
