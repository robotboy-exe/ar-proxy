#!/usr/bin/env bash
dir="$(dirname "$(readlink -f "$0")")"
[ -f ~/.agentrouter-key ] && . ~/.agentrouter-key
[ -n "$AGENTROUTER_KEY" ] || { echo "AGENTROUTER_KEY is not saved."; exit 1; }
export AR_PORT=8788
if ! ss -ltn | grep -q ":$AR_PORT "; then
  (cd "$dir" && setsid nohup python3 proxy.py >/dev/null 2>&1 &)
  sleep 2
fi
mkdir -p ~/.cache/ar-proxy
sed "s/8787/$AR_PORT/g" "$dir/oc-windows.json" > ~/.cache/ar-proxy/oc-wsl.json
export OPENCODE_CONFIG=~/.cache/ar-proxy/oc-wsl.json
exec opencode
