[JUNIE TASK]
Title: Commission Genesis to Create Archivist (Archy)
Preconditions:
- Genesis active in architect_mode
  Plan:
1. Send task payload to Genesis orchestrator:
   "Create and deploy Archivist Agent — Level-3 Knowledge Curator (Archy)"
2. Monitor /logs/genesis_session_*.log until completion message received.
3. When Genesis finishes, pull artifacts from /agents/archivist/ and verify build.
   Verification:
- Genesis log reports “Task complete.”
- Required files exist in /agents/archivist/.
  Rollback:
- Delete incomplete /agents/archivist/ directory if build aborted.
