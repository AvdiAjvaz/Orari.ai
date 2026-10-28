# Orari.ai — Architecture

The initial vertical slice serves an Albanian browser interface and JSON API from one FastAPI process. A small static frontend keeps installation and deployment simple; the solver is isolated from presentation so a richer client can replace it later.

## Data and execution
School → weekly days/periods, teachers with unavailable slots and optional hard weekly-hour ceilings, teaching assignments (class, subject, teacher, weekly hours, optional exclusive room). Slots are zero-based `day * periods + period` in the API; the UI uses one-based day:period.

POST /api/generate validates references and resource limits, performs capacity checks, then builds a CP-SAT model. Boolean assignment-slot variables enforce exact weekly demand, teacher availability, weekly-hour ceilings, and exclusive class/teacher/room occupancy. The objective minimizes additional occurrences of a class/subject within the same day. It is a preference, not a hard daily limit. Solver workers are capped at two; each request is capped at thirty seconds (UI: ten).

A separate verifier checks the returned entries against the input before any solution is exposed. Results distinguish feasible, proven optimal for this objective, proven infeasible, and unknown after timeout. No strict rule is silently relaxed.

The browser retains input in localStorage; the server has no database or accounts. Input changes invalidate visible output. CSV exports use the exact solved input snapshot.

## Scope and next milestones
This version supports one school/week, shared rooms, availability and class views. It does not yet support double periods, shifts, split groups, fixed placements, teacher-gap optimization, configurable priority tiers, manual dragging, or minimum-change rescheduling. Those require explicit schema, constraints and verifier updates together.

Next: persist versioned school plans in PostgreSQL; add typed rule definitions and lexicographic priorities; add fixed assignments and contradiction explanations; move solve jobs to a bounded background queue with polling/cancellation; add accounts and authorization before public multi-user deployment. Current synchronous requests should run only in trusted local development. Limits bound individual models, not aggregate concurrent demand.

Teacher availability presets in the UI are expanded to explicit unavailable slots before solving. Selected workdays and inclusive period intervals define the free slots; manual calendar changes can refine them. An optional `max_hours` is a ceiling across all classes and subjects, not a target. Prechecks report excess assigned demand; CP-SAT and the independent verifier also enforce the ceiling. Existing teachers default to no additional ceiling.
