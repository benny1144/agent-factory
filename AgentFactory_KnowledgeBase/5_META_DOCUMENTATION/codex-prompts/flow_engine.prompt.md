State machine with steps, transitions, wait_for_approval(token).
Decorators: @start, @listen(event), @require_approval.
Redis-backed queue; resumable; persistence of state; audit all transitions.
