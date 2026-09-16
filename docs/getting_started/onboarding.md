# Onboarding & Setup

Everything SourceryKit needs before you write code: an account, credentials, and a database.
This is the **first** step — nothing else works until the credentials below exist.

## ⚠️ One human step

Login is **browser-based OAuth**. The only step an automated agent cannot do is the
browser sign-in — a human opens the consent page, signs in (or creates an account on
the Provably web app), and approves. Everything else (database link, project setup)
runs automatically. If you are an agent: **prefer the `sourcerykit init` CLI over
hand-writing config**, run the setup below yourself, and ask a human only to complete
the browser login.

## Setup

```bash
pip install sourcerykit
```

```bash
# Browser OAuth login (one human step). With --sandbox/--project-name the wizard
# continues automatically after the browser login completes.
sourcerykit init --sandbox --project-name my-app

# verify everything works
sourcerykit doctor
```

> [!TIP]
> To use your own PostgreSQL instead of a hosted sandbox, replace `--sandbox` with
> `--postgres-url postgresql://user:pass@host:5432/db`.

> [!NOTE]
> A brand-new account has no organization, so `init` auto-creates one. If the account
> already belongs to **multiple** orgs, `init` prompts you to choose — use a
> single-org account to keep it scriptable.

Interactive: run `sourcerykit init` with no flags and follow the wizard — the browser
login opens, then you create a hosted sandbox and name the project. You can also choose
to link your own PostgreSQL instead.

Full command reference (`init`, `doctor`, `endpoints`, `config`, `trace`): [cli.md](https://provably.ai/docs/getting_started/cli).

## The credentials

`init` stores credentials at two levels (see [cli.md](https://provably.ai/docs/getting_started/cli) for the full table):

- **Global config** (OS application directory, shared across projects): the Provably
  OAuth **access/refresh tokens** and the **organisation id** — issued together at
  login; never hand-write them.
- **Project `.env`**: `SOURCERYKIT_POSTGRES_URL` (the database SourceryKit records
  intercepts in — set automatically for sandbox users), `SOURCERYKIT_PROJECT_NAME`, and
  the bootstrap resource ids (`SOURCERYKIT_MIDDLEWARE_ID`, `…_DATABASE_ID`, `…_SCHEMA_ID`,
  `…_TABLE_ID`, `…_COLLECTION_ID`, `…_INTEGRATION_KEY`).

Inspect stored config any time with `sourcerykit config list`, or validate and repair it
with `sourcerykit doctor` (add `--fix`).

> [!NOTE]
> If using your own PostgreSQL (with `--postgres-url`), the database must be **hosted and
> publicly reachable** — the Provably backend connects to it directly to generate proofs.
> `localhost` / `127.0.0.1` will not work. Sandbox databases are managed by Provably and
> have no such restriction.

## Manual configuration (alternative)

Already have credentials? Environment variables override the stored config:

```bash
export PROVABLY_ACCESS_TOKEN="..."
export PROVABLY_REFRESH_TOKEN="..."
export SOURCERYKIT_ORG_ID="..."
export SOURCERYKIT_POSTGRES_URL="postgresql://user:password@host:5432/db"
```

---

**Next steps:**
- [End-to-End Walkthrough](https://provably.ai/docs/getting_started/end-to-end-walkthrough)
