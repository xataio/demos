WEDNESDAY DEMO GUIDE — Next.js + Xata + Claude Code Starter
============================================================

Tested end-to-end on 2026-06-01. Every command below is copy-paste verbatim.
No # comments (zsh chokes on them). One command per line.

IMPORTANT RULES (learned the hard way):
- Tab 1 = dev server ONLY. Never "export DATABASE_URL" in tab 1.
- Tab 2 = all xata/psql commands.
- After switching branches: edit .env.local AND restart dev server.
- After running a migration: restart dev server (Ctrl-C + npm run dev).
- The --branch flag is broken in CLI 1.2.1. Use "xata branch checkout <name>"
  then plain "xata branch url" instead.
- If you delete a branch, checkout main FIRST or the CLI gets stuck.


============================
PRE-SHOW SETUP (do backstage)
============================

Open two terminal tabs. Both cd to the project:

    cd /code/demos/nextjs-claude-code-starter

Confirm baseline is clean (tab 2):

    xata branch checkout main
    xata branch list

Should show only "main". If leftover branches exist, delete them:

    xata branch delete <name>

Verify baseline data (tab 2):

    export DATABASE_URL="$(xata branch url)"
    psql "$DATABASE_URL" -c "SELECT email, name FROM users;"

Should show Alice Chen and Bob Smith. If not, reseed:

    psql "$DATABASE_URL" -c "DELETE FROM users;"
    psql "$DATABASE_URL" -c "INSERT INTO users (email, name) VALUES ('alice@example.com','Alice Chen'),('bob@example.com','Bob Smith');"

Point the app at main (tab 2):

    printf 'DATABASE_URL=%s\n' "$(xata branch url)" > .env.local

Start the dev server (tab 1 — make sure DATABASE_URL is NOT set):

    echo $DATABASE_URL

If that prints anything:

    unset DATABASE_URL

Then start:

    npm run dev

Open localhost:3000. Confirm:
  [x] Users (2): Alice Chen, Bob Smith
  [x] Role column: blank dashes
  [x] Teams (0): "Run migration 003 to create the teams table."

PRE-WARM the demo branch (still backstage, tab 2):

    xata branch create --name add-roles
    xata branch wait-ready add-roles

This takes ~20s. Do it before you walk on stage so the endpoint is warm
and the branch-create wait doesn't eat live demo time.

Verify it's warm:

    psql "$(xata branch url)" -c "SELECT 1"

Should return instantly. You're ready.


============================
LIVE DEMO FLOW
============================

BEAT 1 — SHOW THE BASELINE
---------------------------
Browser: localhost:3000 already open.
"Here's our app — two users, basic schema. No roles, no teams yet."
Point at the blank Role column and the Teams placeholder.


BEAT 2 — INSTANT DATABASE BRANCHING
------------------------------------
"Before I touch anything, I'm going to create an isolated database branch.
This is a copy-on-write fork — no data duplication, ready in seconds."

If you pre-warmed (recommended), the branch already exists. Show it:

Console: open console.xata.io, navigate to claude-code-starter > Branches.
Show the branch tree: main -> add-roles.

If you want to create live instead (riskier, ~20s wait):

    xata branch create --name add-roles
    xata branch wait-ready add-roles


BEAT 3 — POINT THE APP AT THE BRANCH
--------------------------------------
Tab 2 (should already be checked out to add-roles from the create step):

    printf 'DATABASE_URL=%s\n' "$(xata branch url)" > .env.local

Tab 1: Ctrl-C, then:

    npm run dev

Refresh browser (Cmd+Shift+R).
"Same data — Alice and Bob — but now served from our branch. Main is untouched."


BEAT 4 — ZERO-DOWNTIME MIGRATION: ADD ROLES
---------------------------------------------
"Now I'll add a role column. pgroll uses expand-and-contract — old and new
schemas serve traffic simultaneously. Zero downtime."

Tab 2:

    xata roll start migrations/002_add_role.yaml
    xata roll complete

Tab 1: Ctrl-C, then:

    npm run dev

Refresh browser (Cmd+Shift+R).
Role column now shows "member" badges for Alice and Bob.

"The role column is live. Every existing user got backfilled to 'member'.
And main still has no role column — completely isolated."


BEAT 5 — ZERO-DOWNTIME MIGRATION: ADD TEAMS
---------------------------------------------
"Let's go further — add a teams table with a foreign key back to users."

Tab 2:

    xata roll start migrations/003_add_teams.yaml
    xata roll complete

Tab 1: Ctrl-C, then:

    npm run dev

Refresh browser (Cmd+Shift+R).
Teams section changes from "Run migration 003" to "No teams yet."

Optional — insert a team for a visual payoff:

    psql "$(xata branch url)" -c "INSERT INTO teams (name) VALUES ('Engineering');"

Refresh browser. Teams (1) with "Engineering" listed.


BEAT 6 — PROVE MAIN IS UNTOUCHED (optional but powerful)
---------------------------------------------------------
"Let me prove main is untouched."

Tab 2:

    xata branch checkout main
    printf 'DATABASE_URL=%s\n' "$(xata branch url)" > .env.local

Tab 1: Ctrl-C, then:

    npm run dev

Refresh browser (Cmd+Shift+R).
Back to baseline: blank roles, "Run migration 003" for teams.

"Main never changed. The branch had its own isolated schema evolution.
When we're happy, we merge. If something breaks, we delete the branch."


BEAT 7 — THE WHOA MOMENT: AGENTIC WORKFLOW
--------------------------------------------
"Everything I just did — branching, writing migrations, applying them,
verifying — what if Claude Code did it all from a single prompt?"

NOTE: After Beat 6 you're on main, and the add-roles branch still exists.
That's fine — Claude Code will create a NEW branch with a different name.
The add-roles branch is just leftover evidence the audience can see in the
console tree. If you skipped Beat 6, checkout main first:

    xata branch checkout main

Make sure .env.local points to main and dev server is running on main.

Open Claude Code in the project directory (tab 3, or use tab 2):

    cd /code/demos/nextjs-claude-code-starter
    claude

Type this prompt (or something similar — improvise to match the moment):

    Add a created_by column to the users table to track who created each user

Then sit back and let the audience watch Claude Code:
  1. Create a branch (e.g., add-created-by)
  2. Wait for the branch endpoint
  3. Write a new migration file (004_add_created_by.yaml)
  4. Apply it with xata roll start / xata roll complete
  5. Verify with psql
  6. Update .env.local

When Claude Code finishes, it will tell you to restart the dev server.

Tab 1: Ctrl-C, then:

    npm run dev

Refresh browser (Cmd+Shift+R).
The users table should show a new "created_by" column (or whatever
Claude Code added). The audience just watched an AI agent do the full
DevOps workflow autonomously.

Talking points while Claude Code works:
- "It's reading the project's CLAUDE.md to understand the CLI commands."
- "It created a branch first — so main is still safe."
- "It wrote a pgroll migration, not raw DDL — so this is zero-downtime."
- "It verified the result before telling me it's done."

IMPORTANT: This beat depends on the feature-flow skill being installed.
See the SKILL SETUP section at the bottom of this guide.

If Claude Code gets stuck or does something unexpected, you can recover:
- Ctrl-C to stop Claude Code
- xata branch checkout main (in tab 2)
- Delete any branch it created: xata branch delete <name>
- Repoint app: printf 'DATABASE_URL=%s\n' "$(xata branch url)" > .env.local
- Restart dev server

Alternative safe prompts (tested patterns that match existing migrations):

    Add a role column to the users table with a default of 'member'

    Create a teams table and add a team_id foreign key to users


============================
RESET (after rehearsal, before live)
============================

Tab 2 — clean up ALL branches from the rehearsal:

    xata branch checkout main
    xata branch list

Delete every branch that isn't main:

    xata branch delete add-roles
    xata branch delete <any-branch-claude-code-created>

Also delete any migration files Claude Code wrote during Beat 7:

    ls migrations/

If there's anything beyond 001, 002, 003 (e.g., 004_add_created_by.yaml),
delete it so the next run starts clean:

    rm migrations/004_*.yaml

Reseed if needed:

    export DATABASE_URL="$(xata branch url)"
    psql "$DATABASE_URL" -c "DELETE FROM users;"
    psql "$DATABASE_URL" -c "INSERT INTO users (email, name) VALUES ('alice@example.com','Alice Chen'),('bob@example.com','Bob Smith');"

Repoint app at main:

    printf 'DATABASE_URL=%s\n' "$(xata branch url)" > .env.local

Tab 1: Ctrl-C, then:

    npm run dev

Refresh browser. Baseline confirmed. Then pre-warm a fresh branch:

    xata branch create --name add-roles
    xata branch wait-ready add-roles


============================
KNOWN GOTCHAS (quick reference)
============================

1. NEVER export DATABASE_URL in tab 1. Shell env overrides .env.local.
2. ALWAYS restart dev server after migration or branch switch.
3. --branch flag is broken in CLI 1.2.1. Use checkout + plain url.
4. Branch creation takes ~20s for the endpoint to warm. Pre-warm backstage.
5. If you delete a branch, checkout main FIRST or CLI gets stuck on a ghost.
6. New terminal tabs don't have xata in PATH unless ~/.zshrc has the export.
7. zsh doesn't treat # as comments in interactive mode. Don't paste comment lines.
8. npm audit warnings are a postcss XSS on localhost — ignore, never --force.


============================
SKILL SETUP (one-time, before first rehearsal)
============================

The "WHOA moment" (Beat 7) requires the feature-flow skill to be installed
in the project's .claude/skills/ directory, and the CLAUDE.md to include
the CLI gotchas so Claude Code doesn't hit the same traps you did.

1. Copy the skill into the project:

    mkdir -p /code/demos/nextjs-claude-code-starter/.claude/skills/feature-flow
    cp ~/demos/claude-skills/feature-flow/SKILL.md /code/demos/nextjs-claude-code-starter/.claude/skills/feature-flow/SKILL.md

2. Add CLI gotchas to CLAUDE.md (append to the end of the file):

    Open /code/demos/nextjs-claude-code-starter/CLAUDE.md and add:

    ## CLI gotchas (Xata CLI 1.2.x)

    - The `--branch <name>` flag on `xata branch url` is BROKEN — it says
      "not found" even for branches that exist. Always use
      `xata branch checkout <name>` to switch, then plain `xata branch url`
      (no flags) to get the connection string.
    - `xata branch create` automatically checks out the new branch.
    - `xata branch wait-ready` uses the current branch if no argument given.
    - Never delete the currently checked-out branch — it leaves the CLI in a
      broken state. Always `xata branch checkout main` before deleting.

    ## App connection

    - The Next.js app reads DATABASE_URL from `.env.local` at boot time.
    - To switch branches: update `.env.local`, then restart the dev server.
    - NEVER use `export DATABASE_URL=...` in the dev server terminal — shell
      env vars override `.env.local` and silently point the app at the wrong
      branch.
    - After any migration or branch switch, the dev server must be restarted
      (Ctrl-C + `npm run dev`) for the app to see schema changes.

3. Test the skill by opening Claude Code in the project and running:

    /project:feature-flow

   Or just type a natural prompt like:

    Add a status column to the users table

   Claude Code should autonomously branch, migrate, verify, and report back.
