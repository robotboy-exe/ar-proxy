# PENDING — AgentRouter 400 fix on opencode1-ar (handoff 2026-10-05)

Read `PLAN.md` first (technical history), then `BRIEF.md` (rules). All BRIEF rules still apply:
probe first; back up + plain-language + diff + **wait for go** before any edit; never open
`~/.local/share/opencode1/opencode/auth.json`; don't touch v2/`opencode` or Guysoft config;
use `~` not `/tmp`; `evidence/` is read-only; never print any API key/env var; when testing
AgentRouter with curl always send
`-H 'User-Agent: opencode/1.18.33 ai-sdk/provider-utils/4.0.23 runtime/bun/1.4.0'`
(a 401 without it means nothing). The key is fixed — do not investigate auth.

Model: only `agentrouter/deepseek-v4-flash`. Never use gpt-5.6-sol / build provider.

## STATUS — Edit 2 (baseURL `/v1`) APPLIED 10:14; awaiting USER TUI retest

Steering change works: opencode1 now speaks Anthropic protocol, but its bundled `@ai-sdk/anthropic`
posts to `{baseURL}/messages`, so with the base URL at the root the proxy forwarded `/messages`
→ agentrouter returned the admin console HTML (HTTP 200, 1586 B) — prompt 1 failed. Fix: base
URL now `http://127.0.0.1:8787/v1` so the path is the proven-working `/v1/messages`.
(Backup of pre-edit state: `oc.json.bak2`. Diff recorded below.)

The steering change worked (opencode1 now speaks Anthropic protocol), but opencode1 v1.18.33's
bundled `@ai-sdk/anthropic` posts to `{baseURL}/messages`, so requests hit the proxy at
`/messages` and the proxy forwards to `https://agentrouter.org/messages` which returns the
**AgentRouter admin console HTML** (`type=text/html`, 1586 B, HTTP 200) — not a valid response.
15 identical attempts logged (proxy.log #3006–#3020, 04:39:44–04:40:22).

### Why
- `oc.json` provider `agentrouter` currently has `options.baseURL: "http://127.0.0.1:8787"` (no `/v1`).
- opencode1 anthropic provider appends `/messages` → `http://127.0.0.1:8787/messages`.
- Verified earlier (tiny curl, through this same proxy): `POST /v1/messages` on agentrouter works
  (HTTP 200, real Anthropic `content[].thinking` + signature responses). So the endpoint is fine;
  the **path is short one `/v1` segment**.

### Next action (edit oc.json, then retest)
```diff
- "options":{"baseURL":"http://127.0.0.1:8787"}
+ "options":{"baseURL":"http://127.0.0.1:8787/v1"}
```
~DONE (applied 10:14, oc.json.bak2 backup, valid JSON).~ After editing: restart the proxy
(see environment notes), then USER re-runs the TUI prompt list in a fresh `oc1` session.
Success gates: proxy.log shows `POST /v1/messages` with `resp: HTTP 200` and JSON/SSE (never
`type=text/html`), and NO `HTTP 400` / `Invalid schema` / `content[].thinking` entries.

## History (why we are here)

1. **Original two 400s** (OpenAI path `/v1/chat/completions`):
   - F1 "Invalid schema … browser_close: null is not of type array" — empty-schema tool sometimes
     serialized as `"required": null`.
   - F2 "The `content[].thinking` in the thinking mode must be passed back to the API" — deepseek
     reasoning echo rejected by a strict thinking-mode backend.
2. **Proxy fixes implemented earlier** (`_fix_schema` null→`[]`, `_fix_reasoning`
   reasoning_content→`content[].thinking`) were then **found insufficient**: a live replay of the
   F2 sample produced `422 messages[2]: unknown variant "thinking", expected text/image_url/file`
   (an OpenAI-native serde backend rejects thinking blocks). Root cause of the mess: the OpenAI
   path fans to channels with **contradictory** conventions — no single body satisfies them all.
   `_fix_reasoning` is now dormant (no-op on Anthropic bodies); it is still in proxy.py (Option A:
   leave proxy.py untouched). `_fix_schema` remains a harmless guard.
3. **Routing discovery (docs, agentrouter.org/docs/opencode.html):** endpoint family is chosen
   STATICALLY by provider `npm` + `baseURL`:
   - `@ai-sdk/openai-compatible` + baseURL `…/v1` → `POST /v1/chat/completions`, Bearer auth.
   - `@ai-sdk/anthropic` + baseURL no-`/v1` → `POST /v1/messages`, `x-api-key` auth.
   - Docs: "两类方法并行，不要混用" (run in parallel, don't mix). No per-request pin control.
   - `deepseek-v4-flash` supports **both** families. Wrong/offline model → **503** (no channel).
4. **Anthropic endpoint proven correct for this model** (tiny curl through proxy, 2026-10-05):
   - `POST /v1/messages` minimal → HTTP 200, response is Anthropic extended-thinking
     (`content[].thinking` + `signature`).
   - Passing a prior reasoning turn back as `content[].thinking` **with and without** signature →
     HTTP 200 both. So Anthropic family = one consistent convention; reasoning stays fully preserved.
5. **Edit 1 applied (backup `~/ar-proxy/oc.json.bak`), 02:15:** switched provider to
   `npm:@ai-sdk/anthropic`, baseURL root (no `/v1`), added `models.deepseek-v4-flash`.
   proxy.py untouched. oc.json validated as JSON.
6. **TUI test 04:40 → FAILED (prompt 1)** as described above. This is the current state.

## Current config snapshot

`~/ar-proxy/oc.json` (OpenRouter override, launched via `OPENCODE_CONFIG`):
```json
{"$schema":"https://opencode.ai/config.json","small_model":"openrouter/openrouter/free",
 "agent":{"title":{"model":"openrouter/openrouter/free"}},
 "provider":{"agentrouter":{"npm":"@ai-sdk/anthropic",
   "options":{"baseURL":"http://127.0.0.1:8787"},
   "models":{"deepseek-v4-flash":{"name":"DeepSeek V4 Flash"}}}}}
```
Backups: `oc.json.bak` (original OpenAI path). Proxy `proxy.py` UNCHANGED (still has `_fix_schema`
+ `_fix_reasoning`; both inert for Anthropic bodies).

## Environment facts & gotchas

- Proxy: `~/ar-proxy/proxy.py`, port `127.0.0.1:8787`. Log: `~/ar-proxy/proxy.log`.
- Launcher `oc1` = `~/.local/bin/opencode1-ar`: if no proxy running, it starts `nohup python $HOME/ar-proxy/proxy.py` **without AR_DEBUG** (so req_N/resp_N are NOT captured). The proxy now running (PID 31903, started ~04:39 by oc1) has AR_DEBUG **off**.
- For debug captures: `HOME=/data/data/com.termux/files/home AR_DEBUG=1 setsid env python ~/ar-proxy/proxy.py </dev/null >/dev/null 2>&1 &`. **CRITICAL:** the agent's `$HOME` is redirected to `.opencode-guysoft`; `proxy.py` uses `os.path.expanduser("~/ar-proxy")`, so without the explicit real HOME the proxy crashes on its first log write (`FileNotFoundError …/.opencode-guysoft/ar-proxy/proxy.log`). AR_DEBUG req_/resp_ numbering restarts at 1 on every proxy start (overwrites old files).
- Termux clock is skewed (ps shows 1970 dates); use proxy.log timestamps (real wall clock).
- opencode1 sends `anthropic-version: 2023-06-01`, `x-api-key`, `x-session-id`,
  `x-session-affinity`; proxy forwards headers fine (redacts auth in log).
- User-Agent observed from TUI: `opencode/1.18.33 ai-sdk/provider-utils/4.0.46 runtime/bun/1.4.0`.
- Sandbox cannot drive the live TUI — USER must run `oc1` tests. Sandbox env key ≠ user shell key; use the replay tool/curl from the USER's shell for authenticated checks.
- opencode1 MCP `playwright-cdp`: `~/.config/opencode1/opencode/opencode.jsonc`.

## Next steps checklist
1. (Go from user) Edit `oc.json` baseURL → `http://127.0.0.1:8787/v1`; backup first; show diff.
2. Restart proxy (optionally AR_DEBUG=1).
3. USER re-runs full TUI prompt list via `oc1` (deepseek-v4-flash + playwright-cdp open→close, several turns).
4. Check proxy.log: `POST /v1/messages`, `resp: HTTP 200`, JSON/SSE not HTML, and zero
   `HTTP 400` / `Invalid schema` / `content[].thinking`.