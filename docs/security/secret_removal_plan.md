# Secret Remediation & History Purge Plan

This document describes how to remove committed secrets from the repository history and rotate affected keys. Follow these steps carefully.

Scope
- Files with secrets (currently committed):
  - .env (repo root)
  - junie-bridge/.env (if previously committed)
- Providers: Google, OpenAI, Groq, Serper (per .env contents)

Immediate actions (already applied)
- Added .gitignore to prevent committing secrets and build artifacts (.env, frontend/node_modules, dist, artifacts, etc.).
- Will untrack .env files in the next commit while keeping local copies.

1) Rotate keys (do this first)
- Generate new API keys in each provider’s console.
- Immediately revoke/disable the exposed keys.
- Update your local .env and junie-bridge/.env with the new keys (DO NOT COMMIT). Use .env.example for placeholders.

2) Remove secrets from the current tree
- Untrack local secret files (keep working copies):
  - git rm --cached .env
  - git rm --cached junie-bridge/.env  # if it exists/tracked
- Commit: "security: remove committed .env files and prevent future commits"

3) Purge secrets from Git history (pick one)
A) Using git filter-repo (recommended)
- Install: https://github.com/newren/git-filter-repo
- Backup your repo first.
- Then run from repo root:
  - git filter-repo --path .env --path junie-bridge/.env --invert-paths --force
- This rewrites history to remove the files entirely.
- Push with force (coordinate with your team):
  - git push --force origin main

B) Using BFG Repo-Cleaner
- Download BFG: https://rtyley.github.io/bfg-repo-cleaner/
- Backup your repo first.
- Create a text file listing the secret paths:
  - echo ".env" > bfg-files.txt
  - echo "junie-bridge/.env" >> bfg-files.txt
- Run:
  - java -jar bfg.jar --delete-files bfg-files.txt
- Follow BFG instructions to complete cleanup and force-push.

4) Validate
- Clone the repository fresh in a new directory.
- Search for any remnants:
  - git log -p | Select-String -Pattern "OPENAI_API_KEY|GOOGLE_API_KEY|GROQ_API_KEY|SERPER_API_KEY"
- Ensure .env files are not present in history.

5) Governance & documentation
- Update docs/governance_ledger.md with a new entry documenting this remediation.
- Record key rotation details (dates, owners) in your internal security ledger.

Notes
- History rewrites require coordination and can disrupt other clones. Notify all collaborators.
- After force-push, all consumers must rebase or re-clone.
- Keep only .env.example in VCS. Never commit active keys.
