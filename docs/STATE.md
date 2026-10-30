# STATE — AgentRouter proxy on opencode1-ar (handoff 2026-10-30)

Read order: `AGENTS.md` first (workspace rules), then `BRIEF.md` (rules + setup),
and `CLI-TEST.md` (approved — read FIRST for the loop phase); `PLAN.md` only when
technical history is needed.

## Status
**Both configured AgentRouter models are operational.** DeepSeek's five-prompt CLI
loop and user TUI pass succeeded (`docs/STATE.md:54-62`, `docs/STATE.md:81-82`).
GPT 5.6 Sol is configured at `oc.json:1`; repeated multi-turn Responses API calls
return HTTP 200 (`proxy.log:2000-2002`, `proxy.log:2016-2019`, `proxy.log:2033-2036`).

## Approved (user)
- proxy.py self-locating fix — `b0f3c55`.
- CLI-TEST.md workflow — `af8a6f3` + this commit; Undo section, Chromium/CDP
  pre-check, playwright preflight all incorporated. Ready to use as the loop
  recipe.

## Done
- Edit 1 (02:15): oc.json provider → `npm:@ai-sdk/anthropic`, baseURL root, backup `oc.json.bak`.
- Edit 2 (10:14): oc.json baseURL → `http://127.0.0.1:8787/v1`, backup `oc.json.bak2`, valid JSON.
- Edit 3 (22:04): proxy.py line 2 → `D = os.path.dirname(os.path.realpath(__file__))`
  (self-locating; `LOG = D + "/proxy.log"` unchanged), backup `proxy.py.bak`.
  Proof: restarted proxy → `#2 22:04:45 POST /v1/messages` → `resp: HTTP 200
  type=text/event-stream`, reply "test". py_compile OK.
- Docs migrated into this repo (`ar-proxy/`): PENDING.md → STATE.md; evidence → `ar-proxy/evidence/`.
- CLI test workflow designed and proven (see `CLI-TEST.md`).
- Edit 4 (6283f75): added `mcp.playwright-cdp` to oc.json — **BUG: placed inside `provider`** (valid JSON, wrong level).
- Edit 5 (7cf6b2b): moved `mcp` to top level of oc.json. **Lesson: check structure by printing key names at each level, not just "valid JSON".**
- Edit 6 (716dc0f): CLI-TEST.md Undo command fixed to use `--source=6283f75~1`.
- Edit 7 (`54c6008`): added the empty assistant-message guard at `proxy.py:53-72`.
- Edit 8 (`d31ca09`): added `agentrouter-gpt/gpt-5.6-sol` through
  `@ai-sdk/openai` at `oc.json:1`; live traffic uses `/v1/responses` and returns
  HTTP 200 (`proxy.log:2000-2002`, `proxy.log:2016-2019`, `proxy.log:2033-2036`).

## Findings
- `start.err` (2026-10-05 01:17): proxy.py crashed with `FileNotFoundError` opening
  `…/.opencode-guysoft/ar-proxy/proxy.log` (proxy.py:6). Cause: proxy started from agent
  shell where `~` = `.opencode-guysoft`. **Explained; do not re-investigate.** Edit 3
  (self-locating `D`) now prevents this class of crash entirely.
- Proxy was NOT running at 13:28 (port 8787 closed) although a stale process matched
  `pgrep -f ar-proxy/proxy.py`; restarted it. A fresh proxy start truncates proxy.log when
  it is >1 MB (proxy.py:3), which wiped the old 51828-line log (TUI evidence #3006–#3020
  is still recorded in this file's history below). Request numbering restarts at 1 per start.
- Agent shell env: `$HOME` → `.opencode-guysoft` AND `PREFIX` → `…/.opencode-guysoft-prefix`.
  `PREFIX` breaks opencode1's runtime probe (`~/.local/bin/opencode1` launcher line 16);
  remove it with `env -u PREFIX` (see CLI-TEST.md).
- **Historical 2026-10-05 baseline:** `#1` was a 404 from the agent's own curl
  `GET /v1/messages`; the baseline `grep -c "HTTP 4"` already counts it. Loop PASSes
  when the count does NOT rise above that baseline. Do not blame a 404 that is `#1`.
- GPT's `@ai-sdk/openai` provider uses `/v1/responses`, not the legacy DeepSeek
  `/v1/chat/completions` path (`oc.json:1`, `proxy.log:2016-2019`).

## CLI test result (agent, 00:19–00:23)
- Prompt 1 "Say test and nothing else.": `#1 00:19:14 POST /v1/messages` → `n_messages: 1` → `resp: HTTP 200 type=text/event-stream`, reply "test".
- Prompt 2 "Open https://example.com...": `#2 00:20:03 POST /v1/messages` → `n_messages: 3` (history carried) → `resp: HTTP 200`, browser tool called (`playwright-cdp_browser_navigate`).
- Prompt 3 "Now go to https://example.org...": `#7 00:21:22 POST /v1/messages` → `n_messages: 7` → `resp: HTTP 200`, multiple browser tools (navigate, find, snapshot, evaluate, close).
- Prompt 4 "Open https://example.com again...": `#11 00:22:35 POST /v1/messages` → `n_messages: 21` → `resp: HTTP 200`, browser tools (navigate, snapshot, close).
- Prompt 5 "Compare the two pages...": `#15 00:23:36 POST /v1/messages` → `n_messages: 29` → `resp: HTTP 200`, reasoning-heavy answer, no tools.
- **All counts unchanged**: `HTTP 4` = 2 (baseline), `HTTP 5` = 0, `relay error` = 1 (baseline BrokenPipeError).
- Zero `HTTP 400` / `Invalid schema` / `content[].thinking`. `ODD[no-choices]` lines present (harmless).
- Session pinned: all requests share `x-session-id: ses_ef1a2e31effeafBnLD7nbo6yvg`.

## Next
The user's TUI pass (`oc1`) done and passed. No further action needed.

## Cleanup — DO NOT DELETE (the user's decision)
Nothing is to be deleted. **Only the user can reverse this decision, never an agent.** Keep:
- `proxy.py.bak` — backup of proxy.py before self-locating fix
- `oc.json.bak` — config before any fix (original OpenAI-compatible family)
- `oc.json.bak2` — the failed version that returned the AgentRouter web page (root baseURL, posts to `/messages`)
- `oc.json.bak-before-gpt` — config before the GPT provider was added
- `proxy.py.bak-before-empty-fix` — proxy before the empty assistant-message guard
- `AGENTS.md.bak-before-gpt-docs`, `docs/BRIEF.md.bak-before-gpt-docs`, and
  `docs/STATE.md.bak-before-gpt-docs` — docs before the 2026-10-30 scope update
- `req_*.json` / `resp_*.txt` — captures from the 400 era (AR_DEBUG=1 runs)
- `start.err` = one old proxy crash at about 01:17 on 2026-10-05, already explained (the agent shell had the wrong HOME), not a live bug.
- `evidence/` = saved prompts and evidence from the 400 era.
- `~/projects/agentrouter-fix` — the OLD copy of this project, kept only for reference. **Never edit it, never run anything from it.** The live project is `~/ar-proxy`.

## TUI test result (user, 2026-10-06)
Prompts 1 and 3 passed in the TUI (`oc1`). AgentRouter 400 fix verified end-to-end.

## GPT runtime result (2026-10-30)
The live opencode session uses `agentrouter-gpt/gpt-5.6-sol` through
`POST /v1/responses`; consecutive tool-bearing turns return HTTP 200
(`proxy.log:2000-2015`, `proxy.log:2016-2032`, `proxy.log:2033-2049`).
