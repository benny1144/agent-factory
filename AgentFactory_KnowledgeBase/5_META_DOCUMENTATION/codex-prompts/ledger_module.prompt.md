Implement append-only JSONL writer with per-entry SHA-256 and per-block Merkle root.
Emit {ts, actor_did, action, params_hash, prev_hash}.
Provide verify() to reconstruct chain and raise on tamper.
