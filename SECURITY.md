# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in EthicsBoard AI, please report it
privately rather than opening a public issue.

- Use GitHub's [private vulnerability reporting](https://github.com/Malikasadjaved/ethicsboard-ai/security/advisories/new), or
- Email the maintainer (see the profile at [github.com/Malikasadjaved](https://github.com/Malikasadjaved)).

Please include a description of the issue, steps to reproduce, and the potential
impact. We aim to acknowledge reports within a few days.

## Handling of secrets

This project relies on third-party credentials that must **never** be committed:

- `.env` — API keys for AI/ML API, Featherless AI, and Band configuration
- `agent_config.yaml` — Band agent IDs and API keys

Both are listed in `.gitignore`. Only the `.example` templates are tracked. If you
believe a secret has been committed, rotate the affected key immediately and open a
private report.

## Scope

EthicsBoard AI is a hackathon demonstration project and is **not** intended for
production handling of real protected health information (PHI). Do not submit
real patient data or real IRB protocols containing PHI to a deployed instance.
