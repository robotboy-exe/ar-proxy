# AGENTS.md — AgentRouter 400 fix workspace

Diagnostic/debugging workspace (not app code). Goal: get opencode1-ar
(`agentrouter/deepseek-v4-flash`) multi-turn sessions through the AgentRouter
proxy with zero HTTP 400s. All target files live under
`/data/data/com.termux/files/home/...`.

## Read these first (in order)
At session start, read: `docs/STATE.md` — current status, next actions (read FIRST);
`docs/BRIEF.md` — rules + setup. Read `docs/PLAN.md` only when you need technical history /
root causes / why the endpoint-family switch. `docs/TUI-TEST.md` — the USER-run
verification script (agent cannot drive TUI). `docs/CLI-TEST.md` — read if it exists.
Keep these updated when state changes; they ARE the project's memory.

## CRITICAL environment gotcha
- The agent's `$HOME` is redirected to `.opencode-guysoft`. Real paths are under
  `/data/data/com.termux/files/home/` (e.g. `~/ar-proxy` is NOT the agent's `~/ar-proxy`).
- `proxy.py` uses `os.path.expanduser("~/ar-proxy")`. To start a debug proxy from
  the agent shell you MUST pass the real home, else it crashes on first log write:
  `HOME=/data/data/com.termux/files/home AR_DEBUG=1 setsid env python /data/data/com.termux/files/home/ar-proxy/proxy.py </dev/null >/dev/null 2>&1 &`
- Termux has no `/tmp`. Use `~` (project dir or `.cache/opencode/tmp`).
- Termux `ps` clock is skewed (shows 1970); use proxy.log wall-clock timestamps.

## Rules (from docs/BRIEF.md — non-negotiable)
- Probe first (read-only). No edits until a probe shows the cause. Do not guess.
- Edits are allowed ONLY to `oc.json`, `proxy.py`, and the `.md` files. Back up
  the target file before editing, and git commit BEFORE and AFTER each edit, each
  message stating what changed and why. Anything else needs user `go`.
- NEVER open/print `~/.local/share/opencode1/opencode/auth.json` or any key/env var.
- Do NOT touch v2 (plain `opencode`) or opencode-guysoft's own config.
- Model is only `agentrouter/deepseek-v4-flash`. Never `gpt-5.6-sol` / build provider.
- `evidence/` in this repo is read-only; never delete. This repo's `.md` handoffs are not read-only.
- Every claim must cite a log line or `file:line` — no uncited assertions.
- Stop and report after each probe.

## Testing (who tests what)
- Agent tests through the CLI; USER does the final TUI pass (`oc1`, per docs/TUI-TEST.md).
- Agent CLI tests ALWAYS pass `--model agentrouter/deepseek-v4-flash`.
- A run that produces no new `proxy.log` line is NOT a valid test.

## Checkpoints
A checkpoint is: a phase approved, a test passes or fails, or a file edited. At
each checkpoint, update `docs/STATE.md` without being asked.

## Components (real paths)
- Proxy: `ar-proxy/proxy.py`, binds `127.0.0.1:8787`, forwards to agentrouter.org.
  Log `ar-proxy/proxy.log`. `AR_DEBUG=1` writes `req_N.json`/`resp_N.txt` in the same dir —
  numbering restarts at 1 each start (overwrites old captures).
- Launcher `oc1` = `~/.local/bin/opencode1-ar`: starts proxy (AR_DEBUG OFF) if not
  running, sets `OPENCODE_CONFIG=$HOME/ar-proxy/oc.json`, runs opencode1.
- Override: `ar-proxy/oc.json` (backups `oc.json.bak`, `oc.json.bak2`).
  Current state lives in `docs/STATE.md` (not duplicated here).
- opencode1 config: `~/.config/opencode1/opencode/opencode.jsonc` (playwright-cdp MCP here;
  MCP pkg under `~/.npm/_npx/381cec31605a419a/node_modules/@playwright/mcp`).
- `ar-proxy/proxy.py`: `_fix_schema` (null-array-keyword guard, still active) and
  `_fix_reasoning` (reasoning echo transform, DORMANT/inert on Anthropic bodies) — do not
  re-enable the reasoning rewrite without re-checking docs/PLAN.md REVISION 2 rationale.

## Routing facts (root cause)
- Endpoint family is chosen STATICALLY by provider `npm` + `baseURL` (no per-request pin):
  `@ai-sdk/anthropic` + no `/v1` → `/v1/messages` (x-api-key); `@ai-sdk/openai-compatible`
  + `/v1` → `/v1/chat/completions` (Bearer). Docs ("两类方法并行，不要混用"): run families in
  parallel, don't mix.
- The OpenAI path fans to contradictory backends (thinking-convention conflicts) — that's what
  caused the original 400s. Anthropic family has one consistent contract. Proven fix = switch
  families, NOT more proxy rewrites.
- `POST /v1/messages` through the proxy on this model = HTTP 200 with Anthropic extended
  thinking (`content[].thinking` + `signature`).
- Traps: wrong/offline model → HTTP 503. Curl tests MUST send the opencode UA header
  `-H 'User-Agent: opencode/1.18.33 ai-sdk/provider-utils/4.0.23 runtime/bun/1.4.0'`
  (401 without it means nothing). Wrong path (missing `/v1`) → AgentRouter returns its
  admin-console HTML (HTTP 200, `type=text/html`) — that is a FAIL signal, not success.

## Verification
- Success gates (docs/TUI-TEST.md): proxy.log shows `POST /v1/messages` + `resp: HTTP 200` with
  JSON/SSE (never `text/html`), and zero `HTTP 400` / `Invalid schema` / `content[].thinking`.
  `ODD[no-choices]` lines are expected/harmless. Count errors: `grep -c "HTTP 4" ~/ar-proxy/proxy.log`
  before vs after.
- Sandbox cannot drive the live TUI — USER runs `oc1` and sends prompts; agent only reads logs.
- Sandbox key ≠ user shell key (agentrouter 401s in sandbox); authenticated checks via
  `ar-proxy/replay.py` must run in the USER's shell.
