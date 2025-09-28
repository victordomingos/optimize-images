#!/usr/bin/env bash
set -e

ARCH="$(uname -m)"
BREW_PREFIX=$([[ "$ARCH" == "arm64" ]] && echo "/opt/homebrew" || echo "/usr/local")

brew install libjpeg-turbo

export LDFLAGS="-L${BREW_PREFIX}/opt/jpeg-turbo/lib"
export CPPFLAGS="-I${BREW_PREFIX}/opt/jpeg-turbo/include"

python3.10 -m pip uninstall -y pillow || true

if [[ "$ARCH" == "x86_64" ]]; then
  CFLAGS="${CFLAGS} -mavx2" python3.10 -m pip install --no-cache-dir --force-reinstall --no-binary :all: pillow-simd
else
  python3.10 -m pip install --no-cache-dir --force-reinstall pillow-simd
fi

python3.10 - <<'PY'
from PIL import features
print(features.check_feature("libjpeg_turbo"))
PY
