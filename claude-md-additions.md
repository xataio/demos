## CLI gotchas (Xata CLI 1.2.x)

- The `--branch <name>` flag on `xata branch url` is BROKEN — it says "not found"
  even for branches that exist. Always use `xata branch checkout <name>` to switch,
  then plain `xata branch url` (no flags) to get the connection string.
- `xata branch create` automatically checks out the new branch.
- `xata branch wait-ready` uses the current branch if no argument given.
- Never delete the currently checked-out branch — it leaves the CLI in a broken state.
  Always `xata branch checkout main` before deleting.

## App connection

- The Next.js app reads DATABASE_URL from `.env.local` at boot time.
- To switch branches: update `.env.local`, then restart the dev server.
- NEVER use `export DATABASE_URL=...` in the dev server terminal — shell env vars
  override `.env.local` and silently point the app at the wrong branch.
- After any migration or branch switch, the dev server must be restarted
  (Ctrl-C + `npm run dev`) for the app to see schema changes.
