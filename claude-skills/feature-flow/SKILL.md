---
name: feature-flow
description: End-to-end feature workflow — create a branch, write and apply a migration, verify the result, update the app
---

# Feature Flow

When the user describes a schema change (e.g., "add a role column to users"),
execute the full workflow autonomously. Follow every step in order. Do not skip
verification. Report results at the end.

## Step 1 — Name and create a branch

Derive a short kebab-case branch name from the request (e.g., add-user-roles,
add-teams-table, add-status-field). Create and wait for it:

```bash
xata branch create --name <branch-name>
xata branch wait-ready <branch-name>
```

`wait-ready` takes ~20 seconds while the database endpoint warms up. This is
normal. Do not retry or abort.

After creation, check out the branch:

```bash
xata branch checkout <branch-name>
```

IMPORTANT: The `--branch` flag on `xata branch url` is broken in CLI 1.2.x.
Always use `xata branch checkout` to switch branches, then plain
`xata branch url` (no flags) to get the connection string.

## Step 2 — Write or select the migration file

Check `migrations/` for an existing file that matches the requested change.
If a match exists, use it. If not, write a new pgroll YAML migration file.

Naming: find the highest-numbered file in `migrations/` and increment.
Example: if `003_add_teams.yaml` exists, the next file is `004_<name>.yaml`.

pgroll migration format:

```yaml
operations:
  - add_column:
      table: users
      column:
        name: status
        type: text
        nullable: false
        default: "'active'"
```

Common operations:
- `create_table` with `columns` array (each column has name, type, and optional pk, default, nullable, unique, references)
- `add_column` with `table` and `column`
- `drop_column` with `table` and `column` name
- `rename_column` with `table`, `from`, `to`
- `alter_column` with `table`, `column`, and changes
- `create_index` with `table`, `columns` array

For columns with text defaults, wrap the value in single quotes inside double quotes:
`default: "'member'"` (the outer quotes are YAML, the inner quotes are SQL).

For uuid primary keys, use: `type: uuid`, `pk: true`, `default: gen_random_uuid()`
For timestamps, use: `type: timestamptz`, `default: now()`

## Step 3 — Apply the migration

```bash
xata roll start migrations/<file>.yaml
xata roll complete
```

If `roll start` fails, read the error carefully. Common causes:
- Table already exists (migration already applied — check with `\dt`)
- Column already exists (check with `\d <table>`)
- Syntax error in YAML (fix and retry)

If it fails and you cannot fix it, run `xata roll rollback` to clean up,
then diagnose.

## Step 4 — Verify

Confirm the migration landed correctly:

```bash
psql "$(xata branch url)" -c "\d <table>"
psql "$(xata branch url)" -c "SELECT * FROM <table> LIMIT 5;"
```

Check that:
- New columns appear with correct types and defaults
- New tables exist with the right structure
- Existing data is preserved (backfilled where applicable)

## Step 5 — Update the app connection

Point the Next.js app at the branch so the user can see the change in the browser:

```bash
printf 'DATABASE_URL=%s\n' "$(xata branch url)" > .env.local
```

CRITICAL: Do NOT run `export DATABASE_URL=...` in any terminal. Shell
environment variables override .env.local and cause the app to connect
to the wrong branch. Only write to .env.local.

## Step 6 — Report

Tell the user:
1. Branch name created
2. Migration file used or written (show the filename and contents if new)
3. Verification results (schema and sample data)
4. That .env.local has been updated
5. **They need to restart the dev server** (Ctrl-C + `npm run dev` in the
   dev server terminal) and refresh the browser to see the change

## Error recovery

If something goes wrong mid-flow:

- Migration in expand phase (started but not completed):
  `xata roll rollback` to undo, then fix and retry.

- Branch created but migration failed beyond repair:
  ```bash
  xata branch checkout main
  xata branch delete <branch-name>
  ```
  Then start over.

- Never delete a branch you're currently checked out to. Always
  `xata branch checkout main` first.

## Cleanup (only when user asks)

```bash
xata branch checkout main
xata branch delete <branch-name>
printf 'DATABASE_URL=%s\n' "$(xata branch url)" > .env.local
```

Remind the user to restart the dev server after switching back to main.
