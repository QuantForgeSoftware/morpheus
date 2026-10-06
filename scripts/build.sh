#!/usr/bin/env bash
#
# Build the Morpheus C analyzer (bin/cruncher) on macOS or Linux.
#
# Handles the two things the raw makefiles don't:
#   * modern clang treats several Perseus-era constructs as errors;
#   * macOS may resolve a broken CommandLineTools SDK, so we point at the Xcode SDK.
#
# The flex-based stemlib builders are built separately with `make -C src stemtools`
# (they need flex + libfl); the analyzer itself does not.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/src"

EXTRA=""
if [ "$(uname -s)" = "Darwin" ]; then
  SDK=""
  # Prefer a full Xcode SDK: the CommandLineTools SDK is sometimes malformed
  # (its libSystem.tbd can fail the linker with a TAPI "unknown architecture").
  for candidate in /Applications/Xcode*.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk; do
    if [ -d "$candidate" ]; then SDK="$candidate"; break; fi
  done
  if [ -z "$SDK" ]; then
    SDK="$(xcrun --show-sdk-path 2>/dev/null || true)"
  fi
  if [ -n "${SDK}" ] && [ -d "${SDK}" ]; then
    export SDKROOT="$SDK"
    EXTRA="-isysroot $SDK"
  fi
fi

DEFAULT_CFLAGS="-std=gnu89 -fcommon -Wno-return-type -Wno-implicit-function-declaration \
-Wno-incompatible-function-pointer-types -Wno-int-conversion -Wno-implicit-int \
-Wno-deprecated-non-prototype"
export CFLAGS="${CFLAGS:-$DEFAULT_CFLAGS} ${EXTRA}"

make clean >/dev/null 2>&1 || true
make
make install

echo
echo "Built $ROOT/bin/cruncher"
echo "Try:  echo 'a)/nqrwpos' | MORPHLIB=$ROOT/stemlib $ROOT/bin/cruncher -S"
