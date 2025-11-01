Add decorators:
 - @require_risk("LOW|MODERATE|HIGH|CRITICAL")
 - @require_roles([...])
Tie to governance-kernel.config.yaml.
Reject calls lacking manifest permission; log policy_violation.
