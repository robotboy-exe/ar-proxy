# CLI test for opencode1-ar (agent-run, non-interactive)

Agent-driven equivalent of `TUI-TEST.md`: proves Edit 2 (Anthropic
family, `POST /v1/messages`) works across a multi-turn session from
the CLI, so USER only needs the final TUI pass. Prompts are the same
five as TUI-TEST.md.

## Environment (agent shell gotchas)

- The agent's `$HOME` is redirected to `.opencode-guysoft`, so every
  command below must be prefixed with `HOME=/data/data/com.termux/files/home`.
- The agent shell also exports `PREFIX=/data/data/com.termux/files/home/.opencode-guysoft-prefix`.
  Remove it with `env -u PREFIX`, or opencode1's launcher probes the
  wrong runtime root and dies with "runtime not found"
  (`opencode1` launcher lines 26-31).
- Auth key: `~/.local/share/opencode1/opencode/auth.json` (with real
  HOME). NEVER open or print it.
- Override config: `~/ar-proxy/oc.json` via `OPENCODE_CONFIG`.

## Before starting

1. Proxy up? `pgrep -f ar-proxy/proxy.py`. If not, start with real HOME
   (AGENTS.md): `HOME=/data/data/com.termux/files/home setsid env python
   /data/data/com.termux/files/home/ar-proxy/proxy.py </dev/null >/dev/null 2>&1 &`
2. Baseline: `grep -c "HTTP 4" ~/ar-proxy/proxy.log`
3. NOTE: proxy.py truncates proxy.log at startup when it exceeds 1 MB
   (proxy.py:3), and request numbering restarts at 1 per start. Take
   freshness/absence of the request from BEFORE the run.
4. Before prompts 2-4 (browser tools): Chromium and CDP must be up.
   Check CDP on the port playwright-cdp MCP uses (opencode.jsonc:
   `--cdp-endpoint=http://127.0.0.1:9222`):
   `pgrep -f lib/chromium/chrome`  (non-zero = no Chromium process)
   `curl -s -o /dev/null -w "%{http_code}\n" -m 5 http://127.0.0.1:9222/json/version`
   Expect `200`. `000` (or curl exit 7, "Connection refused") = CDP down;
   start Chromium on 9222 before continuing.

## The exact command

Prompt 1 (new session):

```
HOME=/data/data/com.termux/files/home env -u PREFIX \
  OPENCODE_CONFIG=/data/data/com.termux/files/home/ar-proxy/oc.json \
  /data/data/com.termux/files/home/.local/bin/opencode1 run \
  "Say test and nothing else." --model agentrouter/deepseek-v4-flash
```

Prompts 2-5 (same session, continue). Capture the session id from the
previous request's log line and pass it:

```
SID=$(grep -o '"x-session-id": "ses_[^"]*"' ~/ar-proxy/proxy.log | tail -1 | cut -d'"' -f4)
HOME=/data/data/com.termux/files/home env -u PREFIX \
  OPENCODE_CONFIG=/data/data/com.termux/files/home/ar-proxy/oc.json \
  /data/data/com.termux/files/home/.local/bin/opencode1 run \
  "<prompt N>" --model agentrouter/deepseek-v4-flash --session "$SID"
```

(`x-session-id` appears in the `req headers` line for every request.
Confirmed: request #3 with `--session` carried history, `n_messages: 3`,
roles `["user","assistant","user"]`.)

## Prompts (send one at a time, in order)

1. `Say test and nothing else.`
   (No tools. Verifies the route works at all. If it fails, stop.)
2. `Open https://example.com with the browser tool and tell me the page title.`
   (One tool call.)
3. `Now go to https://example.org, tell me the main heading, then close the browser.`
   (Several tool calls, ending with browser_close.)
4. `Open https://example.com again, tell me what the page says, then close it.`
   (Reopen after a close, with a longer history.)
5. `Compare the two pages you visited and tell me which has more text. Explain your reasoning.`
   (Reasoning-heavy answer, no tools.)

## How to read proxy.log after each prompt

- New request present? `tail -n 10 ~/ar-proxy/proxy.log` — expect a new
  `#N <time> POST /v1/messages` line (never `/messages`).
- Status? Next `resp: HTTP 200 type=text/event-stream` line (never
  `type=text/html`).
- History carried? The `req body` line shows `n_messages` and `roles` —
  they must grow / include the prior turns from prompt 2 onward.
- Session pinned? The `req headers` line shows the same
  `x-session-id` for prompts 2-5.

## Pass

- Each prompt produces a new `POST /v1/messages` line and matching
  `resp: HTTP 200 type=text/event-stream` (JSON/SSE, never `text/html`).
- Zero `HTTP 400` / `Invalid schema` / `content[].thinking` in the run
  window. Count: `grep -c "HTTP 4" ~/ar-proxy/proxy.log` before vs after.
- `ODD[no-choices]` lines are expected/harmless (proxy.py flags
  Anthropic-format lines; see AGENTS.md).
- Model output sanity: prompt 1 returns "test".

## Fail signs / what to do

- No new `POST /v1/messages` line → the run did not reach the proxy;
  check the model/provider name and that the proxy is up (invalid test).
- `resp: HTTP 200 type=text/html` → wrong path (AgentRouter web console);
  check oc.json baseURL ends in `/v1`.
- `HTTP 4xx` → copy the exact error text and `tail -n 30` of the log.
- `HTTP 503` → wrong/offline model on the AgentRouter side.
- `401 unauthorized client` → key/identification problem; do NOT print
  any key. Recheck env and that auth.json exists (real HOME).
- Browser tool fails while the log is clean → Playwright problem, not
  this fix. (CLI runs may not have Playwright's display needs; if so,
  note it and hand prompts 2-4 to the USER's TUI pass.)

## Undo (revert config if needed)

What each file holds (grep of `npm`/`baseURL` only):

- `oc.json` (current): `npm`=@ai-sdk/anthropic, `baseURL`=http://127.0.0.1:8787/v1
  — Edit 2 state, posts to `/v1/messages`. This is the state being tested.
- `oc.json.bak2`: `npm`=@ai-sdk/anthropic, `baseURL`=http://127.0.0.1:8787
  — state right after Edit 1, BEFORE the `/v1` edit (posts to `/messages`; this
  is the 04:40 FAILED TUI state).
- `oc.json.bak`: no `npm` key, `baseURL`=http://127.0.0.1:8787/v1
  — the ORIGINAL pre-Edit-1 config (OpenAI-compatible family).

- Revert only Edit 2 (back to root baseURL → `/messages`):
  `cp ~/ar-proxy/oc.json.bak2 ~/ar-proxy/oc.json`
- Restore the original pre-fix config:
  `cp ~/ar-proxy/oc.json.bak ~/ar-proxy/oc.json`