# Evaluating an Ollama model candidate

A step-by-step procedure for testing whether a candidate `OLLAMA_CHAT_MODEL` (or
`OLLAMA_EMBEDDING_MODEL`) actually performs well on the machine running this stack, before
committing to it in config. This bypasses the app entirely and talks to the `ollama` service
directly, so retrieval/prompt-building overhead doesn't confound the measurement.

See [architecture.md](architecture.md#ai--rag-pipeline) for *why* the currently-configured models
were chosen; this doc is about *how to test a new candidate*.

## Prerequisites

The `ollama` service must be running: `docker compose up -d ollama`. The container name follows
Docker Compose's `<project>-<service>-<index>` convention — for this repo that's
`living-genie-ollama-1`; substitute your own if the compose project name differs.

## 1. Pull the candidate

```sh
docker exec living-genie-ollama-1 ollama pull <model:tag>
```

Large models can take several minutes; if run through the agent's Bash tool this will often move
to a background task automatically — that's fine, just wait for it to finish before continuing.

## 2. Cold-load timing

The *first* call to a model always pays a one-time load cost (reading weights off disk into
VRAM/RAM). Measure it separately from steady-state latency by calling Ollama's API directly with
`stream: false`, so the response JSON includes timing fields:

```sh
curl -s http://localhost:11434/api/chat -d '{
  "model": "<model:tag>",
  "messages": [{"role": "user", "content": "Say hello in one short sentence."}],
  "stream": false
}'
```

Relevant response fields (all durations in nanoseconds — divide by `1e9` for seconds):
`load_duration`, `prompt_eval_duration` + `prompt_eval_count`, `eval_duration` + `eval_count`
(the last pair is the actual generation cost).

## 3. Warm timing

Repeat the *identical* call. `load_duration` should now be near-zero (Ollama keeps the model
loaded for `OLLAMA_KEEP_ALIVE`, default 5 minutes of idle time) — `eval_duration`/`eval_count`
here reflect the real per-message latency a user would feel, which is the number that actually
matters for deciding if a model is usable.

## 4. Test every language the app needs to support

Don't stop at English. This app must reply in the same language the user wrote in (Traditional
Chinese included), and both quality and latency can differ noticeably by language. Run a second
warm call with a zh-Hant prompt, e.g.:

```sh
curl -s http://localhost:11434/api/chat -d '{
  "model": "<model:tag>",
  "messages": [{"role": "user", "content": "請用一句話跟我打招呼，並簡單介紹你自己。"}],
  "stream": false
}'
```

Read the `message.content` for fluency/correctness, not just the timing fields — watch in
particular for a large `eval_count` relative to how short the visible reply is; some models
generate substantial hidden "thinking" tokens before the final answer, which costs real latency
without being visible in `message.content`.

## 5. Check GPU/VRAM usage

```sh
curl -s http://localhost:11434/api/ps
```

Compare `size_vram` (bytes actually resident on GPU) against `size` (total model size) for the
loaded model. If `size_vram` is much smaller than `size`, most of the model is running on CPU/system
RAM — expect it to be slower, even if it technically "works."

## 6. Watch for hard failures, not just slowness

A response with an `"error"` field instead of a normal `message` means the model **crashed**, not
just ran slow. Check the container logs for the underlying failure:

```sh
docker compose logs ollama --tail 40
```

Look for lines like `llama-server terminated: signal: aborted` or a `GGML_ASSERT(...)` failure —
these are usually the llama.cpp backend hitting an internal limit (e.g., too many tensor splits
when a model is partitioned across CPU+GPU to fit constrained VRAM). Retry once to confirm it's
reproducible before concluding the model doesn't work on this hardware — the `ollama` service
itself typically stays healthy and answerable even after a per-request crash like this, so no
restart is needed between attempts.

## 7. Clean up models you don't adopt

```sh
docker exec living-genie-ollama-1 ollama rm <model:tag> [<model:tag> ...]
docker exec living-genie-ollama-1 ollama list   # confirm they're gone
```

Don't leave test models sitting in the `ollama_data` volume — they're multi-GB each.

## 8. If you do adopt a new model

1. Update `OLLAMA_CHAT_MODEL` (or `OLLAMA_EMBEDDING_MODEL`) in **both** `web-api/.env` (local,
   already-running stack) and `web-api/.env.example` (repo template, so the pin is documented for
   everyone else).
2. `docker compose restart web-api` — env vars are read at startup, so a restart is enough; no
   rebuild needed.
3. Re-verify through the actual UI, not just raw Ollama — app-level prompt construction (system
   prompt, retrieved diary context, conversation history) adds tokens the raw API test above
   doesn't include, so real end-to-end latency will be somewhat higher than the raw numbers.
