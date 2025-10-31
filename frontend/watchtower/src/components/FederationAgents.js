// Watchtower — Federation Agents Roster
// This roster feeds the UI and can be extended by operators.

const roster = [
  { name: "Orion", role: "Meta-Orchestrator", status: "Active", model: "n/a", readiness: "1.00" },
  { name: "Artisan", role: "Implementation Engine", status: "Active", model: "policy/allowlist", readiness: "0.98" },
  { name: "Genesis", role: "Evolver", status: "Active", model: "mixed", readiness: "0.97" },
  { name: "Archy", role: "Reflective Intelligence", status: "Active", model: "gpt-4o-mini", readiness: "0.97" },
  // Appended per Phase 38.6–38.7
  {
    name: "Forgewright",
    role: "Toolmaker",
    model: "gpt-5-mini",
    readiness: "0.90",
    status: "Active"
  },
  {
    name: "Librarius",
    role: "Knowledge Curator",
    model: "gpt-5-mini",
    readiness: "0.88",
    status: "Active"
  }
];

export default roster;
