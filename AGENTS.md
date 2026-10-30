# AGENTS.md — AgentRouter proxy workspace

Diagnostic/debugging workspace (not app code). Goal: keep opencode1-ar multi-turn
sessions for `agentrouter/deepseek-v4-flash` and `agentrouter-gpt/gpt-5.6-sol`
working through the AgentRouter proxy with zero HTTP 400s. All target files live under
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
- `proxy.py` resolves its log directory from `__file__` (`proxy.py:2`), so the
  redirected `$HOME` no longer changes its log path. Debug start:
  `AR_DEBUG=1 setsid env python /data/data/com.termux/files/home/ar-proxy/proxy.py </dev/null >/dev/null 2>&1 &`
- Termux has no `/tmp`. Use `~` (project dir or `.cache/opencode/tmp`).
- Termux `ps` clock is skewed (shows 1970); use proxy.log wall-clock timestamps.

## Rules (from docs/BRIEF.md — non-negotiable)
- Probe first (read-only). No edits until a probe shows the cause. Do not guess.
- Edits are allowed ONLY to `oc.json`, `proxy.py`, and the `.md` files. Back up
  the target file before editing, and git commit BEFORE and AFTER each edit, each
  message stating what changed and why. Anything else needs user `go`.
- NEVER open/print `~/.local/share/opencode1/opencode/auth.json` or any key/env var.
- Do NOT touch v2 (plain `opencode`) or opencode-guysoft's own config.
- Approved models are `agentrouter/deepseek-v4-flash` and
  `agentrouter-gpt/gpt-5.6-sol` (`oc.json:1`). Always select the explicit provider/model ID.
- `evidence/` in this repo is read-only; never delete. This repo's `.md` handoffs are not read-only.
- Every claim must cite a log line or `file:line` — no uncited assertions.
- Stop and report after each probe.

## Testing (who tests what)
- Agent tests through the CLI; USER does the final TUI pass (`oc1`, per docs/TUI-TEST.md).
- Agent CLI tests ALWAYS pass an explicit model: `--model agentrouter/deepseek-v4-flash`
  or `--model agentrouter-gpt/gpt-5.6-sol`.
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
- `ar-proxy/proxy.py`: `_fix_schema` (null-array-keyword guard), `_fix_reasoning`
  (reasoning echo transform, dormant/inert on Anthropic bodies), and `_fix_empty`
  (empty assistant-message guard) live at `proxy.py:20-72`. Do not expand the reasoning
  rewrite without re-checking `docs/PLAN.md` REVISION 2 rationale.

## Routing facts (root cause)
- Endpoint family is chosen STATICALLY by provider `npm` + `baseURL` (no per-request pin):
  `@ai-sdk/anthropic` + `/v1` → `/v1/messages`; `@ai-sdk/openai` + `/v1` →
  `/v1/responses`; legacy `@ai-sdk/openai-compatible` + `/v1` →
  `/v1/chat/completions`. Current provider declarations are at `oc.json:1`.
- DeepSeek's legacy OpenAI-compatible chat-completions path fanned to contradictory
  thinking conventions and caused the original 400s (`docs/PLAN.md:120-141`). Its proven
  fix remains the Anthropic family, not more proxy rewrites.
- DeepSeek `POST /v1/messages` passed multi-turn CLI and TUI verification
  (`docs/STATE.md:54-62`, `docs/STATE.md:81-82`).
- GPT 5.6 Sol uses the native Responses API; repeated `POST /v1/responses` requests return
  HTTP 200 (`proxy.log:2000-2002`, `proxy.log:2016-2019`, `proxy.log:2033-2036`).
- Traps: wrong/offline model → HTTP 503. Curl tests MUST send the opencode UA header
  `-H 'User-Agent: opencode/1.18.33 ai-sdk/provider-utils/4.0.23 runtime/bun/1.4.0'`
  (401 without it means nothing). Wrong path (missing `/v1`) → AgentRouter returns its
  admin-console HTML (HTTP 200, `type=text/html`) — that is a FAIL signal, not success.

## Verification
- DeepSeek success gate: `POST /v1/messages` + `resp: HTTP 200` JSON/SSE (never
  `text/html`) and zero `HTTP 400` / `Invalid schema` / `content[].thinking`.
- GPT success gate: `POST /v1/responses` + `resp: HTTP 200` SSE and zero HTTP 4xx.
  Responses API event lines produce expected `ODD[non-data-line]` / `ODD[no-choices]`
  diagnostics (`proxy.log:2002-2015`).
- Count errors before vs after a test with `grep -c "HTTP 4" ~/ar-proxy/proxy.log`.
- Sandbox cannot drive the live TUI — USER runs `oc1` and sends prompts; agent only reads logs.
- Sandbox key ≠ user shell key (agentrouter 401s in sandbox); authenticated checks via
  `ar-proxy/replay.py` must run in the USER's shell.
