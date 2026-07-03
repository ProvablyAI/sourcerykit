# Onboarding & Setup

Everything SourceryKit needs before you write code: an account, credentials, and a database.
This is the **first** step — nothing else works until the credentials below exist.

## ⚠️ A human must complete this once

Onboarding creates a Provably account, and the backend sends an **email verification link
that only a human can click**. An automated agent cannot finish this step alone. If you are
an agent, check with `sourcerykit doctor`; if credentials are missing, STOP and ask a human
to run the setup below, then continue once `doctor` passes.

## Run the wizard

```bash
pip install sourcerykit
sourcerykit init          # interactive onboarding wizard
```

The wizard will:

1. **Sign up** (or **log in** to an existing account) with an email address.
2. Prompt the human to **verify that email** — click the link the backend sends. Login does
   not succeed until this is done.
3. Ask for a **hosted, publicly reachable** Postgres URL (see below).
4. Issue your credentials and write them to `.env`.

Already have a verified account? `init` also runs non-interactively:

```bash
sourcerykit init --email you@example.com --password ... --postgres-url postgresql://... --project-name my-app
```

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
