# Environment Configuration Note

## Important: .env File Not Tracked in Git

The `deployment/docker/.env` file is intentionally excluded from version control (listed in `.gitignore`) because it contains sensitive information like passwords and API keys.

## Changes Made for Personal Use

The following settings were changed in `deployment/docker/.env` for Claude Code CLI personal use:

```bash
# Disabled for personal use (no authentication needed)
API_AUTH_ENABLED=false

# Disabled for personal use (no rate limiting needed)
RATE_LIMIT_ENABLED=false

# Disabled for personal use (no conversation state needed)
CONVERSATION_STATE_ENABLED=false

# MCP server enabled for Claude CLI
MCP_ENABLED=true
```

## How to Apply These Settings

If you're setting up a new environment or need to update your `.env` file:

1. Copy the example file:
   ```bash
   cd deployment/docker
   cp .env.example .env
   ```

2. Edit `.env` and set these values:
   ```bash
   API_AUTH_ENABLED=false
   RATE_LIMIT_ENABLED=false
   CONVERSATION_STATE_ENABLED=false
   MCP_ENABLED=true
   ```

3. Keep the other settings (database passwords, URLs, etc.) as generated or configured for your environment.

## Why These Settings?

- **API_AUTH_ENABLED=false**: No authentication needed for personal local use
- **RATE_LIMIT_ENABLED=false**: No rate limiting needed for single-user personal use
- **CONVERSATION_STATE_ENABLED=false**: Not needed for MCP tool usage (Claude CLI doesn't use this)
- **MCP_ENABLED=true**: Required for Claude Code CLI integration

## Security Note

These settings are appropriate for **personal local use only**. If you deploy this server in a shared or production environment, you should:
- Enable API authentication (`API_AUTH_ENABLED=true`)
- Set a strong API key
- Enable rate limiting
- Review all security settings

## Reference

See `deployment/docker/.env.example` for all available configuration options and their default values.

