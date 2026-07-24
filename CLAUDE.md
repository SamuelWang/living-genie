# CLAUDE.md

## Bash environment

Every `Bash` tool call is automatically wrapped with NVM sourcing by a
`PreToolUse` hook (`~/.claude/hooks/nvm-init.sh`, registered in user-scope
`~/.claude/settings.json`), so `node`/`npm` resolve correctly without any
manual setup. Do not manually prepend NVM sourcing (e.g.
`export NVM_DIR=...; . "$NVM_DIR/nvm.sh"`) to commands — it's redundant.
