# Obsidian Setup Guide for MCP Router

A guide for using Obsidian as your project thinking space alongside VS Code.

---

## What is Obsidian?

Obsidian is a **local-first markdown editor** that excels at:
- **Bi-directional linking** - Connect ideas with `[[wiki-style links]]`
- **Graph view** - Visualize how your notes connect
- **Daily notes** - Capture thoughts chronologically
- **Local files** - Your notes are just `.md` files on disk

Think of it as a **second brain** for messy thinking, while VS Code holds clean, actionable code.

---

## Getting Started

### 1. Install Obsidian

```bash
brew install --cask obsidian
```

### 2. Create Your Vault

A "vault" is just a folder. Create one for your projects:

```bash
mkdir -p ~/Documents/Obsidian/Projects
```

Open Obsidian and select "Open folder as vault" → choose `~/Documents/Obsidian`

### 3. Essential Settings

Go to **Settings** (gear icon):

| Setting | Location | Value |
|---------|----------|-------|
| Default location for new notes | Files & Links | `Inbox/` |
| Use [[Wikilinks]] | Files & Links | ON |
| Detect all file extensions | Files & Links | ON |
| Vim mode (optional) | Editor | ON if you use Vim |

---

## Recommended Folder Structure

```
Obsidian/
├── Daily/                    # Daily notes (auto-generated)
│   └── 2026-01-10.md
├── Inbox/                    # Quick capture, unsorted notes
├── Projects/
│   └── MCP-Router/
│       ├── 00-Index.md       # Project dashboard
│       ├── Requirements.md   # Goals, user stories, constraints
│       ├── Brainstorming.md  # Ideas, what-ifs, explorations
│       ├── Questions.md      # Unresolved questions
│       ├── Research/
│       │   ├── MCP-Protocol.md
│       │   └── Ollama-Integration.md
│       └── Scratch/          # Rough drafts, temporary
├── Resources/                # Reference material
│   ├── Tools/
│   │   ├── Docker.md
│   │   └── FastAPI.md
│   └── Concepts/
│       └── MCP.md
└── Templates/                # Note templates
    ├── Daily.md
    ├── Project-Index.md
    └── Research.md
```

---

## Core Obsidian Concepts

### 1. Wiki-Style Links

Link between notes using double brackets:

```markdown
I'm working on [[MCP-Router]] which uses [[FastAPI]] for the router.
See [[Questions]] for unresolved items.
```

**Why this matters:** Creates a web of connected ideas. Click any link to jump there.

### 2. Tags

Organize with `#tags`:

```markdown
#project/mcp-router
#status/in-progress
#type/research
```

### 3. Frontmatter (YAML)

Add metadata at the top of notes:

```yaml
---
created: 2026-01-10
status: active
tags: [project, mcp-router]
---
```

### 4. Daily Notes

Enable in Settings → Core Plugins → Daily Notes

- Creates a new note each day (e.g., `2026-01-10.md`)
- Great for logging what you worked on
- Link to projects: "Worked on [[MCP-Router]] today"

---

## Essential Plugins

Go to **Settings → Community Plugins → Browse**

### Must-Have (Free)

| Plugin | Purpose |
|--------|---------|
| **Calendar** | Navigate daily notes visually |
| **Dataview** | Query your notes like a database |
| **Templater** | Advanced templates with variables |
| **Periodic Notes** | Weekly/monthly notes |

### Nice-to-Have

| Plugin | Purpose |
|--------|---------|
| **Kanban** | Visual task boards |
| **Excalidraw** | Sketch diagrams |
| **Git** | Sync vault with Git |

---

## Templates

### Daily Note Template

Save as `Templates/Daily.md`:

```markdown
# {{date:YYYY-MM-DD}}

## Today's Focus
-

## Log
-

## Links
- Projects:
- People:

## Tomorrow
-
```

### Project Index Template

Save as `Templates/Project-Index.md`:

```markdown
# {{title}}

**Status:** Active | Paused | Complete
**Started:** {{date:YYYY-MM-DD}}
**Repo:** [GitHub](link)

## Overview
Brief description of the project.

## Quick Links
- [[Requirements]]
- [[Brainstorming]]
- [[Questions]]

## Current Focus
What are you working on right now?

## Recent Activity
```dataview
LIST FROM [[]]
WHERE file.mtime >= date(today) - dur(7 days)
SORT file.mtime DESC
```

## Open Questions
![[Questions#Open]]

```

### Research Template

Save as `Templates/Research.md`:

```markdown
# {{title}}

**Source:**
**Date:** {{date:YYYY-MM-DD}}
**Tags:** #research

## Summary
Key takeaways in 2-3 sentences.

## Notes
Detailed notes here.

## Quotes
> Important quotes from source

## Connections
- Related to: [[]]
- Applies to: [[]]

## Action Items
- [ ]
```

---

## MCP-Router Project Notes

Create these starter notes in `Projects/MCP-Router/`:

### 00-Index.md

```markdown
# MCP Router

**Status:** Active
**Started:** 2026-01-06
**Repo:** [GitHub](file:///Users/visualval/.local/share/mcp-router)

## Overview
A containerized MCP router layer using Colima that enhances prompts via Ollama before forwarding to paid AI services.

## Quick Links
- [[Requirements]]
- [[Brainstorming]]
- [[Questions]]
- Code: `docs/ARCHITECTURE.md`

## Current Phase
Phase 1: Foundation - Docker & FastAPI setup

## Key Decisions
- [[FastAPI]] chosen for async support
- [[Colima]] for Docker on macOS
- Local [[Ollama]] for prompt enhancement

## Open Questions
![[Questions#Open]]
```

### Requirements.md

```markdown
# MCP Router Requirements

## Goals
1. Reduce setup time for LLMs, run them efficiently
2. Enable seamless data sharing between applications
3. Use LLMs as assistants, improving productivity

## Target Users
- Myself (primary)
- Other designers
- AI assistants (Claude, Copilot, Ollama)

## Constraints
- Use professional tech: FastAPI, Docker, LangChain
- Must work with Colima on macOS
- Secrets via Keychain (`ks` CLI)

## User Stories
- As a developer, I want prompts enhanced before hitting Claude MAX
- As a user, I want unified MCP access across Raycast, Obsidian, VS Code
- As a designer, I want ComfyUI → Draw Things pipelines

## Non-Goals
- Cloud deployment (local-first)
- Multi-user support
```

### Brainstorming.md

```markdown
# MCP Router Brainstorming

## Ideas
- [ ] Caching layer for repeated prompts
- [ ] Circuit breaker for failed upstreams
- [ ] Web dashboard for monitoring
- [ ] Prompt enhancement rules per endpoint

## What If...
- What if Ollama is unavailable? → Fallback to direct routing
- What if I need GPU passthrough? → Research Colima GPU support
- What if responses are slow? → Streaming support

## Random Thoughts
- Could this become a plugin for others?
- Integration with Raycast AI?
```

### Questions.md

```markdown
# MCP Router Questions

## Open
- [ ] GPU passthrough for Ollama in Colima - needed?
- [ ] MCP server containers vs native processes during dev?
- [ ] Streaming response support for prompt enhancement?
- [ ] How to handle secrets in containers? (Docker secrets vs env)

## Resolved
- [x] Framework choice → FastAPI (see [[ADR-001]])
- [x] Secret management → `ks` CLI with `gen-env-from-ks.sh`
```

---

## Keyboard Shortcuts

| Action | Mac Shortcut |
|--------|--------------|
| Quick switcher (find notes) | `Cmd + O` |
| Create new note | `Cmd + N` |
| Open command palette | `Cmd + P` |
| Toggle edit/preview | `Cmd + E` |
| Search in all notes | `Cmd + Shift + F` |
| Open daily note | `Cmd + D` (if configured) |
| Insert link | `[[` then type |
| Insert tag | `#` then type |
| Open graph view | Click graph icon in sidebar |

---

## Workflow: Code + Obsidian Together

### Daily Flow

1. **Morning:** Open today's daily note, write focus items
2. **Research:** Capture findings in `Projects/MCP-Router/Research/`
3. **Coding:** Use VS Code with `HISTORY.md` for session logs
4. **End of day:** Update daily note with what you accomplished

### Promoting Content to Code

When an idea is ready to implement:

1. In Obsidian: Mark as ready in `Brainstorming.md`
2. In VS Code: Create `docs/decisions/00X-*.md`
3. Link back: Add note in Obsidian that it was promoted

### Quick Capture

- Random idea? → Add to `Inbox/` folder
- Weekly: Review inbox, file into proper locations

---

## Tips for Beginners

1. **Start simple** - Don't over-organize. Let structure emerge.
2. **Link liberally** - When in doubt, make it a link `[[like this]]`
3. **Use daily notes** - They become your project timeline
4. **Graph view is fun** - But don't obsess over it
5. **Inbox is your friend** - Quick capture, sort later
6. **It's just markdown** - You can always move files to VS Code

---

## Syncing (Optional)

### Option 1: iCloud (Simple)
Put your vault in `~/Documents/` - iCloud syncs automatically

### Option 2: Git (Version Control)

```bash
cd ~/Documents/Obsidian
git init
echo ".obsidian/workspace.json" >> .gitignore
echo ".trash/" >> .gitignore
git add .
git commit -m "Initial vault"
```

### Option 3: Obsidian Sync (Paid)
$8/month, works great but not necessary

---

## Next Steps

1. Create your vault folder
2. Copy the folder structure above
3. Create the MCP-Router project notes
4. Enable Daily Notes plugin
5. Start linking ideas!

Your Obsidian vault and VS Code project will work together:
- **Obsidian:** Thinking, researching, brainstorming
- **VS Code:** Building, documenting, shipping
