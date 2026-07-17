# Migrating to Unreleased

Changes currently on `main` that have not been tagged as a release yet.

## Schema change

Migration `005` adds a `answer TEXT` column to the `traces` table.

## Upgrade

```bash
pip install --upgrade sourcerykit
sourcerykit upgrade
```
