# Onboarding & Setup

Everything SourceryKit needs before you write code: an account, credentials, and a database.
This is the **first** step — nothing else works until the credentials below exist.

## ⚠️ One human step

Registration triggers an **email verification link that only a human can click** — that is
the single step an automated agent cannot do. Everything else (register, login, database
link, project setup) runs non-interactively. If you are an agent: check with
`sourcerykit doctor`, drive the setup below yourself, and ask a human only for the
verification click.

## Setup

```bash
pip install sourcerykit
```

Non-interactive (agents and scripts):

```bash
# 1. register (skip if the account exists) — triggers the verification email
sourcerykit init --register --email you@example.com --password ...

# 2. a HUMAN clicks the verification link in the email

# 3. log in + link the database + name the project
sourcerykit init --email you@example.com --password ... \
  --postgres-url postgresql://user:pass@host:5432/db --project-name my-app

# 4. verify everything works
sourcerykit doctor
```

Interactive: run `sourcerykit init` with no flags and follow the wizard — same steps,
prompted (sign up or log in → verify email → link a **hosted, publicly reachable**
Postgres → name the project → credentials stored).

Full command reference (`init`, `doctor`, `endpoints`, `config`, `trace`): [cli.md](cli.md).

## The credentials

`init` stores credentials at two levels (see [cli.md](cli.md) for the full table):

- **Global config** (OS application directory, shared across projects): the Provably
  **API key** and **organisation id** — issued together at login; never hand-write them.
- **Project `.env`**: `SOURCERYKIT_POSTGRES_URL` (the database SourceryKit records
  intercepts in), `SOURCERYKIT_PROJECT_NAME`, and the bootstrap resource ids.

> [!NOTE]
> The Postgres database must be **hosted and publicly reachable** — the Provably backend
> connects to it directly to generate proofs. `localhost` / `127.0.0.1` will not work.

## Manual configuration (alternative)

Already have credentials? Environment variables override the stored config:

```bash
export PROVABLY_API_KEY="..."
export SOURCERYKIT_ORG_ID="..."
export SOURCERYKIT_POSTGRES_URL="postgresql://user:password@host:5432/db"
```

---

**Next:** run the full flow → [End-to-End Walkthrough](example.md) ·
look up a function → [Public API](src/api.md)
