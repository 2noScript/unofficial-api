# Unofficial API — Agent Skills

Drop-in skills for any AI agent (Claude, Cursor, ChatGPT, custom SDK). Just **copy a link** below and paste it to your AI — it will fetch the skill and use Unofficial API for you.

> Tip: start with the **unofficial-api** entry skill — it covers setup and links to all capability skills.

## Skills

| Capability | Copy link below and paste to your AI |
|---|---|
| **Entry / Setup** (start here) | https://raw.githubusercontent.com/2noscript/unofficial-api/refs/heads/master/skills/unofficial-api/SKILL.md |
| Chat / code-gen | https://raw.githubusercontent.com/2noscript/unofficial-api/refs/heads/master/skills/unofficial-api-chat/SKILL.md |

## How to use

Paste to your AI (Claude, Cursor, ChatGPT, …):

```
Read this skill and use it: https://raw.githubusercontent.com/2noscript/unofficial-api/refs/heads/master/skills/unofficial-api/SKILL.md
```

Then ask normally — *"chat with DeepSeek R1"*, *"ask Gemini to write code"*, etc.

## Configure your shell once

```bash
export UNOFFICIAL_API_URL="http://localhost:8000"   # default, or your deployed URL
```

Verify: `curl $UNOFFICIAL_API_URL/health` → `{"status":"ok"}`.

## Links

- Source: https://github.com/2noscript/unofficial-api
