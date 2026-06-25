# SignalLens Development Process

## Language

All project design, planning, implementation notes, commit messages, code comments, documentation, and collaboration conversation should be kept in English.

## Working Style

1. Start with technical design before application scaffolding.
2. Keep the PRD as the source of product intent.
3. Record important design decisions in `docs/technical_design.md` or later architecture decision records.
4. Keep source connectors modular and compliance-aware.
5. Prefer stable official APIs and RSS feeds before experimental social connectors.
6. Commit small, coherent changes with clear English commit messages.
7. Do not commit secrets, API keys, local environment files, generated caches, or local OS metadata.

## Documentation Expectations

The repository should maintain:

- Product requirements.
- Technical design.
- Source feasibility notes.
- Setup instructions.
- API and data model notes.
- Conversation summaries when they affect product or technical direction.

## Git Workflow

The initial remote is:

```text
git@github.com:ZoeyCai2001/SignalLens.git
```

If SSH authentication is unavailable, use:

```text
https://github.com/ZoeyCai2001/SignalLens.git
```

Main branch:

```text
main
```

Commit message style:

```text
Add initial technical design
```

## MVP Sequence

1. Technical design.
2. Source validation.
3. Backend scaffold and database schema.
4. Core connectors.
5. Watchlist backend.
6. LLM processing.
7. Dashboard frontend.
8. Alerts, digest, and personalization.
