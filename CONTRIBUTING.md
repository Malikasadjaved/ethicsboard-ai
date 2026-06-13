# Contributing to EthicsBoard AI

Thanks for your interest! This project was built for the Band of Agents Hackathon,
but contributions, issues, and forks are welcome.

## Getting set up

1. Fork and clone the repo.
2. Copy the credential templates and fill in your own values:
   ```bash
   cp .env.example .env
   cp agent_config.yaml.example agent_config.yaml
   ```
   **Never commit `.env` or `agent_config.yaml`** — they are gitignored for a reason.
3. Backend:
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python backend/server.py
   ```
4. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Before opening a pull request

CI runs on every PR and must stay green:

- **Frontend** — `cd frontend && npm run build`
- **Backend** — `python -m compileall agents backend` (no syntax errors)

Please run both locally first. `npm run lint` is also encouraged, though the
hackathon codebase still has some pre-existing lint findings that are not yet
gated in CI.

## Conventions

- Match the style of the surrounding code — naming, comment density, and idiom.
- Keep commit messages in the imperative mood (e.g. "Add HITL escalation guard").
- The frontend uses a non-standard Next.js build; read `frontend/AGENTS.md` before
  touching the build configuration.
- Agents communicate **only** through Band `@mention` routing — never add a direct
  agent-to-agent API call.

## Reporting issues

Open a GitHub issue with steps to reproduce, expected vs. actual behavior, and
the relevant log output (with any credentials redacted).
