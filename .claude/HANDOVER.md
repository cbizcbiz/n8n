# Handover: excalidraw-diagram skill + self-hosted Excalidraw login

## Where things are

Repo `cbizcbiz/n8n`, branch `claude/busy-bohr-iswpdz`.

The skill lives in `.claude/skills/excalidraw-diagram/`:

- `SKILL.md`: when to trigger, the workflow, the spec format, layout patterns.
- `scripts/draw.py`: turns a JSON spec into `.excalidraw` and Obsidian `.excalidraw.md` files, plus an optional `--svg` preview. Standard library only.
- `examples/four-cs.json` and `examples/n8n-execution.json`: working specs.

To install it for every project:

```bash
git checkout claude/busy-bohr-iswpdz && git pull origin claude/busy-bohr-iswpdz
cp -r .claude/skills/excalidraw-diagram ~/.claude/skills/
```

## What's verified

- `draw.py` runs and the layout matches the reference screenshot (hub and spoke, dark canvas, labelled arrows).
- The generated `.excalidraw` renders without errors in Excalidraw's own export engine (`@excalidraw/utils` 0.1.5, Excalidraw 0.18).
- Fixed: labels on diagonal arrows used to overlap the line.

## Not verified yet

- **Hand font:** the Virgil font couldn't be downloaded in the cloud container, so the hand font hasn't been seen. It should show on excalidraw.com.
- **Obsidian:** the `.excalidraw.md` hasn't been opened in Obsidian with the Excalidraw plugin yet.
- **Skill trigger:** the skill hasn't been triggered from a fresh Claude Code session on the desktop. Test with "diagram the Four Cs of my second brain".

## Open problem: draw.davejrich.com shows "OIDC is not configured"

This isn't caused by the skill. The self-hosted Excalidraw is set up to require OIDC login, but the OIDC settings are missing.

- **Host:** Hostinger VPS, managed through hPanel.
- **Unknown:** which Excalidraw build is running. ExcaliDash and an Excalidraw MCP fork are the likely candidates, since both have optional OIDC.
- **Couldn't do from the cloud session:** reach the VPS. The proxy blocked the domain and there's no SSH or browser access.

Next steps on the desktop, with browser access to hPanel:

1. hPanel → VPS → Manage → Docker Manager. Find the Excalidraw project and read its compose/environment. If there's no Docker Manager, use Browser terminal and run `docker ps --format "table {{.Names}}\t{{.Image}}"`.
2. Work out the image, then find its auth settings: an auth mode variable, and `OIDC_*` values such as issuer URL, client ID, secret and redirect/base URL.
3. Fix it one of two ways. Either switch to local login or no login (easiest for a personal instance), or fill in the real OIDC values from the identity provider.
4. Redeploy (`docker compose up -d`, or Redeploy in Docker Manager), then load https://draw.davejrich.com and confirm a `.excalidraw` file opens.

Don't paste secrets into chat. Mask them as `***`.
