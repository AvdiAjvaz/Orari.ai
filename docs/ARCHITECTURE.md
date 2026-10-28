# Orari.ai — Architecture

The initial vertical slice serves an Albanian browser interface and JSON API from one FastAPI process. A small static frontend keeps installation and deployment simple; the solver is isolated from presentation so a richer client can replace it later.

## Data and execution
School → weekly days/periods, teachers with unavailable slots and optional hard weekly-hour ceilings, teaching assignments (class, subject, teacher, weekly hours, optional exclusive room). Slots are zero-based `day * periods + period` in the API; the UI uses one-based day:period.

POST /api/generate validates references and resource limits, performs capacity checks, then builds a CP-SAT model. Boolean assignment-slot variables enforce exact weekly demand, teacher availability, weekly-hour ceilings, and exclusive class/teacher/room occupancy. The objective minimizes additional occurrences of a class/subject within the same day. It is a preference, not a hard daily limit. Solver workers are capped at two; each request is capped at thirty seconds (UI: ten).

A separate verifier checks the returned entries against the input before any solution is exposed. Results distinguish feasible, proven optimal for this objective, proven infeasible, and unknown after timeout. No strict rule is silently relaxed.

The browser retains input in localStorage; the server has no database or accounts. Input changes invalidate visible output. CSV exports use the exact solved input snapshot.

## Scope and next milestones
This version supports one school/week, shared rooms, availability, class/teacher/room/whole-school views, configurable daily loads, hard subject caps, and required double periods. It does not yet support shifts, split groups, teacher-gap optimization, configurable priority tiers, or minimum-change rescheduling. Fixed placements and verified manual dragging/swaps are supported. Those require explicit schema, constraints and verifier updates together.

Next: persist versioned school plans in PostgreSQL; add typed rule definitions and lexicographic priorities; add fixed assignments and contradiction explanations; move solve jobs to a bounded background queue with polling/cancellation; add accounts and authorization before public multi-user deployment. Current synchronous requests should run only in trusted local development. Limits bound individual models, not aggregate concurrent demand.

Teacher availability presets in the UI are expanded to explicit unavailable slots before solving. Selected workdays and inclusive period intervals define the free slots; manual calendar changes can refine them. An optional `max_hours` is a ceiling across all classes and subjects, not a target. Prechecks report excess assigned demand; CP-SAT and the independent verifier also enforce the ceiling. Existing teachers default to no additional ceiling.

## Photo example and document exports

`app/data/photo.json` preserves the transcribed source matrix, including blank cells. `GET /api/examples/photo` derives weekly demand from occurrences, retains original placements, and runs the independent verifier. Unknown subjects remain explicitly unknown. Sociology uses distinct per-class placeholder teachers, not invented real identities. These placeholders must be resolved for a real staffing plan. No availability or hour caps are inferred. The source view is labeled a transcription, not a solver optimum. Regeneration uses derived demand and current constraints and may move all entries.

`POST /api/export/{xlsx|docx|pdf}` accepts the solved School snapshot and entries, validates references and runs the verifier before document generation. Shared projection logic supports the selected individual or whole-school view. Openpyxl, python-docx and ReportLab produce native files; PDF uses bundled DejaVu fonts with their license, avoiding runtime network downloads and preserving Albanian characters. Spreadsheet cells are explicitly strings to prevent formula evaluation. PDF splits large class lists into groups of eight columns. Files are generated in memory, with no retained server documents.


Class-day occupancy is a mandatory prefix from period zero: occupancy[p] >= occupancy[p+1]. Each occupied class day therefore begins in the first period and contains no internal gaps. Free trailing periods are permitted. The default minimum daily load is zero, so entirely empty days remain permitted unless a positive minimum is configured. The independent verifier checks the same invariant from actual entries, including document-export requests. Teacher availability may begin later, provided other assignments cover the class prefix.


## Configurable daily limits and double periods

School defaults `min_daily_hours` (0), `max_daily_hours` (null = periods/day), and `max_subject_per_day` (null = no hard subject cap) preserve older saved plans. `class_rules` overrides minimum/maximum by class; null inherits the school value, while explicit zero overrides a positive minimum. Bounds apply on every selected school day, including registered classes with no assignments. Positive minimums therefore require enough weekly demand to cover all days. The class occupancy prefix rule remains mandatory.

A lesson's `max_per_day` overrides the school subject cap for its class/subject pair. Counts aggregate across all teachers and teaching assignments for that pair. Multiple explicit limits resolve to their minimum. Unknown photo subjects are excluded from the school-wide subject cap because their identity is unavailable; explicit limits still apply.

`double_periods` requires at least that many disjoint adjacent pairs within the same teaching assignment, teacher, class and room, in a single day. Each pair consumes two of the existing weekly hours; odd weekly demand is supported. Pair-start Booleans require both adjacent occupancy variables and cannot overlap. The independent verifier counts disjoint pairs in same-day contiguous runs; boundary-adjacent periods on different days never form a pair. Incidental additional adjacent singles are permitted. Subject caps are never silently raised for doubles: conflicting rules return infeasible with a useful precheck explanation.

Capacity prechecks report incompatible weekly/daily bounds and subject caps. CP-SAT enforces all configured limits alongside existing resource constraints. The verifier and exports validate them independently. The existing soft preference for subject distribution remains subordinate to these hard rules.


The photo example sets `preferred_friday_hours=6` (browser state: `preferredFriday`). This is a soft per-class target on day index 4, editable in weekly settings. CP-SAT minimizes total absolute Friday deviation before subject repetition: the coefficient is total weekly demand + 1, exceeding the maximum possible repetition penalty. Hard constraints are never relaxed. Responses retain `penalty` as the repetition count and separately return `friday_deviation` and `friday_loads`; UI reports unmet targets without claiming infeasibility or optimality.


## Fixed placements and manual editing

`Lesson.fixed_slots` is a unique list of zero-based weekly slots, bounded by assignment hours and the School's week. These are part of existing weekly demand. CP-SAT forces their occupancy; prechecks explain resource collisions and unavailable teachers; the independent verifier requires every pin in the submitted entries, including manual validations and document exports. Pinning a late lesson does not relax the class prefix rule: earlier periods still require coverage. Week resizing preserves each pin's day/period coordinates and refuses changes that would discard pins. Editing assignment hours cannot reduce demand below the number of pins.

The browser offers native drag/drop and keyboard/two-click movement. Moves and temporal swaps remain within the original classroom. Dropping into an occupied class slot swaps the two entries; assignments, teachers, subjects, rooms and weekly totals retain their identity. The candidate is posted to `POST /api/validate`; all hard rules are checked before replacing the visible result. Invalid candidates leave the existing result untouched and return concrete issues. Fixed source/target entries are protected in the UI and again by the API. A one-step undo uses the same validation path. Manual results never retain an optimality claim; soft Friday target metrics are recomputed.

Validated result snapshots are stored in browser localStorage with their full input fingerprint. On reload, a result is restored only if the current inputs match and `/api/validate` approves it under current server rules. Concurrent edits invalidate pending movement responses using input revision and result identity checks. This remains per-browser storage, not multi-user/server persistence. Moving one period of a double block is allowed only when the resulting schedule still satisfies all required disjoint pairs.
