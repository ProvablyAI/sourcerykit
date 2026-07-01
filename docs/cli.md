# SourceryKit CLI Reference

The `sourcerykit` CLI is the command-line interface for configuring, managing, and debugging your SourceryKit integration.

```bash
sourcerykit [COMMAND]
```

Run `sourcerykit --help` to see all available commands.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| [`init`](#sourcerykit-init) | Interactive setup wizard (account, database, project) |
| [`doctor`](#sourcerykit-doctor) | Validate configuration and connectivity |
| [`feedback`](#sourcerykit-feedback) | Submit feedback or bug reports |
| [`logout`](#sourcerykit-logout) | Clear stored session |
| [`version`](#sourcerykit-version) | Print package version |
| [`endpoints add`](#sourcerykit-endpoints-add) | Add a trusted endpoint |
| [`endpoints list`](#sourcerykit-endpoints-list) | List all trusted endpoints |
| [`endpoints remove`](#sourcerykit-endpoints-remove) | Remove a trusted endpoint |
| [`config list`](#sourcerykit-config-list) | Display active configuration |
| [`config set`](#sourcerykit-config-set) | Update configuration variables |
| [`trace list`](#sourcerykit-trace-list) | Show all traces |
| [`trace show`](#sourcerykit-trace-show) | Show trace details and intercepts |

---

## Configuration Files

SourceryKit stores configuration at two levels:

| Config | Location | Scope | Stores |
|--------|----------|-------|--------|
| Global | `typer.get_app_dir("sourcerykit")` (OS application directory) | User-level | `api_key`, `org_id`, `token`, `email` |
| Local | `./.env` (project directory) | Project-level | `SOURCERYKIT_POSTGRES_URL`, `SOURCERYKIT_PROJECT_NAME`, bootstrap IDs |

Global config is shared across all projects. Local config is project-specific and should be added to `.gitignore`.

---

## Commands

### `sourcerykit init`

Interactive setup wizard for account creation/login, database linking, and project initialization.

```bash
sourcerykit init [--email EMAIL] [--password PASSWORD] [--postgres-url URL] [--project-name NAME]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--email` | Account email (non-interactive login) |
| `--password` | Account password |
| `--postgres-url` | Full `postgresql://` URL |
| `--project-name` | Project name |

> [!NOTE]
> `--email` and `--password` must be used together. When provided, the wizard skips the login prompt and authenticates directly. Registration still requires interactive use (email verification).

**What it does:**
- Account setup (register or login)
- API key retrieval
- PostgreSQL database connection
- Project naming
- Bootstrap resource creation

**Input:** Interactive prompts for email, password, database URL, and project name.

```
Welcome to the SourceryKit Wizard! How would you like to proceed?
❯ Log in with an existing account
  Create a new account
  Exit

🔐 Log in to your account
Email address: user@example.com
Password: ********

🛠️  Link your Postgres database
PostgreSQL URL: postgresql://user:pass@host:5432/db

📦 Name your project
Project name: my-project
```

**Non-interactive example (CI/CD):**
```bash
sourcerykit init \
  --email user@example.com \
  --password secret \
  --postgres-url "postgresql://user:pass@host:5432/db" \
  --project-name my-project
```

**Output:** Saves credentials to global config and local `.env` file.

```
🎉 SOURCERYKIT SETUP COMPLETE

 Global config:
   PROVABLY_API_KEY    = ***********************************1234
   SOURCERYKIT_ORG_ID  = abc123

 Local config (.env):
   SOURCERYKIT_PROJECT_NAME    = my-project
   SOURCERYKIT_POSTGRES_URL    = postgresql://user:***@host:5432/db
   SOURCERYKIT_COLLECTION_ID   = col_abc123
   SOURCERYKIT_INTEGRATION_KEY = ***********************************1234
```

---

### `sourcerykit doctor`

Validate configuration and connectivity.

```bash
sourcerykit doctor [--fix]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--fix` | Auto-fix missing bootstrap IDs by running handshake |

> [!TIP]
> Run `sourcerykit doctor --fix` to automatically re-create missing bootstrap IDs without going through the full `init` wizard again.

**Checks performed:**
1. API key validity
2. PostgreSQL connectivity
3. Project name presence
4. Bootstrap IDs presence
5. Collection and resource ID verification
6. Integration key format

**Example output (all checks pass):**
```
🩺 SourceryKit Doctor

  ✅ API key + org: API key valid, org found (1 org(s))
  ✅ PostgreSQL: PostgreSQL connection successful
  ✅ Project name: 'my-project'
  ✅ Bootstrap IDs: All bootstrap IDs present
  ✅ Collection + IDs: Collection 'my-project' verified (middleware, db, schema, table, collection)
  ✅ Integration: Integration key format valid

All 6 checks passed!
```

**Example output (some checks fail):**
```
🩺 SourceryKit Doctor

  ❌ API key + org: API key is invalid or expired — run 'sourcerykit init'
  ❌ PostgreSQL: PostgreSQL connection failed — check your SOURCERYKIT_POSTGRES_URL
  ✅ Project name: 'my-project'
  ❌ Bootstrap IDs: Missing: middleware_id, database_id — run 'sourcerykit doctor --fix'
  ❌ Collection + IDs: Bootstrap IDs missing — run 'sourcerykit doctor --fix'
  ❌ Integration: SOURCERYKIT_INTEGRATION_KEY is missing — run 'sourcerykit doctor --fix'

2/6 checks passed — run 'sourcerykit init' to fix
```

---

### `sourcerykit feedback`

Submit feedback or bug reports.

```bash
sourcerykit feedback [--description TEXT] [--attach-file PATH]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--description` | Feedback description |
| `--attach-file` | Path to file to attach |

**Input:** Interactive prompts for description and optional file attachment.

**Non-interactive example:**
```bash
sourcerykit feedback --description "Found a bug in the init flow" --attach-file logs.txt
```

---

### `sourcerykit logout`

Clear stored session token.

```bash
sourcerykit logout
```

**Output:** Confirmation message. Run `sourcerykit init` to log in again.

---

### `sourcerykit version`

Print the installed package version.

```bash
sourcerykit version
```

**Example output:**
```
v1.0
```

---

### `sourcerykit endpoints`

Manage trusted endpoints (allowed URLs for HTTP interception).

#### Subcommands

##### `sourcerykit endpoints add`

Add a trusted endpoint to the allow-list.

```bash
sourcerykit endpoints add <URL> [--label LABEL]
```

**Arguments:**
| Argument | Required | Description |
|----------|----------|-------------|
| `URL` | Yes | Endpoint URL to trust |

**Options:**
| Option | Description |
|--------|-------------|
| `--label` / `-l` | Optional display label |

**Example:**
```bash
sourcerykit endpoints add https://api.example.com/data --label "Example API"
```

**Output:**
```
✅ Endpoint added: https://api.example.com/data (Example API)
```

---

##### `sourcerykit endpoints list`

Display all trusted endpoints in a table.

```bash
sourcerykit endpoints list
```

**Example output:**
```
           Trusted Endpoints
┌──────────────────────────────┬─────────────┬──────────┬─────────────┐
│ URL                          │ Label       │ Policy   │ Created by  │
├──────────────────────────────┼─────────────┼──────────┼─────────────┤
│ https://api.example.com/data │ Example API │ v1       │ user@ex.com │
└──────────────────────────────┴─────────────┴──────────┴─────────────┘
```

---

##### `sourcerykit endpoints remove`

Remove a trusted endpoint from the allow-list.

```bash
sourcerykit endpoints remove <URL> [--yes]
```

**Arguments:**
| Argument | Required | Description |
|----------|----------|-------------|
| `URL` | Yes | Endpoint URL to remove |

**Options:**
| Option | Description |
|--------|-------------|
| `--yes` / `-y` | Skip confirmation prompt |

**Input:** Confirmation prompt (unless `--yes` is passed).

**Example:**
```bash
sourcerykit endpoints remove https://api.example.com/data -y
```

**Output:**
```
✅ Endpoint removed: https://api.example.com/data
```

---

### `sourcerykit config`

Manage SourceryKit configuration.

#### Subcommands

##### `sourcerykit config list`

Display the active configuration (global + local).

```bash
sourcerykit config list [--show-key]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--show-key` | Show secrets in clear text (default: masked) |

> [!WARNING]
> `--show-key` prints your API key and database password in clear text. Avoid using it in shared terminals or CI logs.

**Example output:**
```
📋 Global Config

PROVABLY_API_KEY       = ***********************************1234

📋 Local Config (.env)

SOURCERYKIT_POSTGRES_URL  = 'postgresql://user:***@host:5432/db'
SOURCERYKIT_PROJECT_NAME  = 'my-project'
```

---

##### `sourcerykit config set`

Interactively update configuration variables.

```bash
sourcerykit config set [--api-key KEY] [--postgres-url URL] [--project-name NAME]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--api-key` | Set `PROVABLY_API_KEY` |
| `--postgres-url` | Set `SOURCERYKIT_POSTGRES_URL` |
| `--project-name` | Set `SOURCERYKIT_PROJECT_NAME` |

**Input:** Interactive checkbox to select variables to update:
- `PROVABLY_API_KEY` (global)
- `SOURCERYKIT_POSTGRES_URL` (local)
- `SOURCERYKIT_PROJECT_NAME` (local)

**Non-interactive example:**
```bash
sourcerykit config set --project-name new-name
sourcerykit config set --postgres-url "postgresql://user:pass@newhost:5432/db"
```

**Output:** Saves changes and re-bootstraps if database or project name changed.

---

### `sourcerykit trace`

View and inspect traces (recorded agent actions and HTTP intercepts).

#### Subcommands

##### `sourcerykit trace list`

Show all traces with intercept outcome counts.

```bash
sourcerykit trace list [--limit N] [--page P]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--limit` / `-n` | Rows per page (default: 20) |
| `--page` / `-p` | Page number, 1-based (default: 1) |

**Example output:**
```
                              Traces
┌──────────────────────────────────────┬──────────────┬─────────────────────┬───────┬────────┬───────┐
│ ID                                   │ Task         │ Created             │  Pass │ Caught │ Error │
├──────────────────────────────────────┼──────────────┼─────────────────────┼───────┼────────┼───────┤
│ 123e4567-e89b-12d3-a456-426614174000 │ get_data     │ 2026-06-30 10:00:00 │     2 │      0 │     0 │
└──────────────────────────────────────┴──────────────┴─────────────────────┴───────┴────────┴───────┘
```

---

##### `sourcerykit trace show`

Show details of a single trace and its intercepts.

```bash
sourcerykit trace show <ID> [--save-proof]
```

**Arguments:**
| Argument | Required | Description |
|----------|----------|-------------|
| `ID` | Yes | Trace ID (UUID) |

**Options:**
| Option | Description |
|--------|-------------|
| `--save-proof` | Download and save proofs to `.provably` files |

**Example:**
```bash
sourcerykit trace show 123e4567-e89b-12d3-a456-426614174000
```

**Example output:**
```
Trace 123e4567-e89b-12d3-a456-426614174000
  Task:    get_data
  Created: 2026-06-30 10:00:00

        Intercepts
┌───┬────────────┬──────────────────────────┬─────────────────┬─────────┬────────┐
│ # │ Action     │ Source                   │ Mode            │ Claimed │ Outcome│
├───┼────────────┼──────────────────────────┼─────────────────┼─────────┼────────┤
│ 1 │ get_data   │ https://api.example.com  │ field_extraction│ value1  │ PASS   │
└───┴────────────┴──────────────────────────┴─────────────────┴─────────┴────────┘

  1. get_data → PASS
     SQL:    SELECT * FROM intercepts WHERE ...
     Proof:
             Status:     verified
             Verified:   true
             Exec time:  45ms
     Result: {
               "field": "value1"
             }
             Run with --save-proof to download the full proof.
```

**Error (trace not found):**
```
Trace abc123 not found.
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Session expired | Token expired or invalidated | Run `sourcerykit init` to re-login |
| Cannot reach Provably API | Network or firewall issue | Check connectivity; verify `SOURCERYKIT_PROVABLY_API_URL` if using a custom endpoint |
| Missing bootstrap IDs | Incomplete init or corrupted `.env` | Run `sourcerykit doctor --fix` |
| PostgreSQL connection failed | Wrong URL or DB not reachable | Check `SOURCERYKIT_POSTGRES_URL` in `.env`; ensure the database is publicly accessible |
| API key invalid | Wrong key or expired | Run `sourcerykit init` to re-authenticate and fetch a new key |
| Config not loading | Missing global or local config | Run `sourcerykit doctor` to identify which values are missing |
