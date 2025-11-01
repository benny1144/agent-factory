1) Generate DID for test agent; write did.json
2) Sign a sample action payload; append to ledger
3) Run ledger.verify() — expect pass
4) Tamper with entry N; run verify() — expect fail
5) Save Merkle root to /anchors/<date>.txt
6) LVPF: compute file hashes for /agents/test/, sign manifest.json, verify
7) Rollback: modify a file, detect hash mismatch, restore previous version
