# Migrations

Upgrade guides for SourceryKit releases. Each guide covers breaking changes, new schema requirements, and the recommended upgrade path.

| Version | Action | Guide |
|---|---|---|
| [Unreleased](unreleased/unreleased.md) | `sourcerykit upgrade` | Breaking: `reasoning` → `answer`; schema change (traces.answer) |
| [v1.0.1](https://github.com/ProvablyAI/sourcerykit/blob/main/CHANGELOG.md#101) | `pip install --upgrade sourcerykit` | No schema change |
| [v1.0](v1_0/v1_0.md) | `sourcerykit upgrade` | Full migration from previous versions |

## Quick upgrade

```bash
pip install --upgrade sourcerykit
sourcerykit upgrade
```

The `sourcerykit upgrade` command checks for a newer package version on PyPI, offers to install it, and runs all pending database migrations.
