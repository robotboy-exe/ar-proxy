# Task: fix AgentRouter errors in opencode1-ar

## Rules
- Probe first (read files, read-only commands). No edits until a
  probe shows the cause. Do not guess.
- Before any edit: back up the file and show me the exact change.
- Never open or print ~/.local/share/opencode1/opencode/auth.json.
- Do not touch v2 (plain `opencode`) or its config.
- Termux has no /tmp. Use ~.
- Stop and report after each probe.
- Evidence is in ~/ar-proxy/evidence/. Do not
  delete it.

## Setup
- Proxy: ~/ar-proxy/proxy.py on 127.0.0.1:8787. It forwards to
  agentrouter.org and drops "data: null" lines from streams.
  Log: ~/ar-proxy/proxy.log. AR_DEBUG=1 saves full requests and
  responses as req_N.json and resp_N.txt (numbering restarts at 1
  each time the proxy starts, so a new debug run overwrites files).
- ~/ar-proxy/oc.json is the override file. ~/.local/bin/opencode1-ar
  starts the proxy and runs opencode1 with that override.
- opencode1 config: ~/.config/opencode1/opencode/opencode.jsonc
- Model: agentrouter/deepseek-v4-flash. A playwright MCP server
  named playwright-cdp is configured for opencode1 (find where).
- You are running inside opencode-guysoft on an OpenRouter model.
  Do not edit Guysoft's own config.

## Failure 1: "Invalid schema" 400
Seen in proxy.log at 20:32 (requests #2 and #3 of that run):
  Invalid schema for function 'playwright-cdp_browser_close':
  null is not of type "array"
The tool list (36 tools) is sent with every request, so after this
starts, every message in that session fails. Request #1 of that run
succeeded with the same 36 tools.
Later finding: in evidence/req_3.json (a different session),
browser_close is defined as {"type":"object","properties":{},
"$schema":"https://json-schema.org/draft/2020-12/schema",
"additionalProperties":false} with NO "required" field, and that
request had no schema error. Not yet known: which field was null
at 20:32, and what differs between the two sessions.

## Failure 2: "thinking" 400
Session ses_ef75b86c4ffeRm9GykAWwNRsdX, evidence/ files req_1..3.
- Request #2: roles system, user, assistant, tool. HTTP 200, ended
  with a tool call.
- Request #3: roles system, user, assistant, tool, assistant, tool.
  HTTP 400: "The `content[].thinking` in the thinking mode must be
  passed back to the API."
- The wording suggests reasoning text was returned by the model and
  not sent back, but that is unverified.

## Probes to run first
1. In evidence/resp_2.txt: does the streamed reply contain non-null
   reasoning_content?
2. In evidence/req_3.json: do the assistant messages include a
   reasoning_content (or similar) field?
3. In evidence/proxy-tail.log: find the 20:32 schema errors and see
   what the proxy recorded around them.
4. Decide from the results whether the proxy can fix each failure
   (for example by changing the request body), or whether
   opencode1's config needs a setting. Prefer a small proxy fix.

## Done when
A multi-turn session through opencode1-ar, using playwright-cdp
tools (open a page, then close it), runs with no HTTP 400 in
proxy.log. I will run that test myself in the TUI.

## UPDATE 2026-10-05 (read STATE.md first for handoff)
Both original 400s were root-caused to endpoint-family fan-out on the
OpenAI path (`/v1/chat/completions`); the correct fix is the Anthropic
gateway (`@ai-sdk/anthropic`), already applied in ~/ar-proxy/oc.json
(backup oc.json.bak). USER's TUI test: provider switch works (opencode1
now speaks Anthropic) but opencode1 v1.18.33 posts to `/messages`
(no `/v1`), so the proxy forwarded the HTML admin page — prompt 1
failed. Next action (proposed, awaiting go): change oc.json baseURL to
`http://127.0.0.1:8787/v1` so the path becomes the proven-working
`/v1/messages`.
