# Orari.ai — Architecture

The initial vertical slice serves an Albanian browser interface and JSON API from one FastAPI process. A small static frontend keeps installation and deployment simple; the solver is isolated from presentation so a richer client can replace it later.

## Data and execution
School → weekly days/periods, teachers with unavailable slots and optional hard weekly-hour ceilings, teaching assignments (class, subject, teacher, weekly hours, optional exclusive room). Slots are zero-based `day * periods + period` in the API; the UI uses one-based day:period.

POST /api/generate validates references and resource limits, performs capacity checks, then builds a CP-SAT model. Boolean assignment-slot variables enforce exact weekly demand, teacher availability, weekly-hour ceilings, and exclusive class/teacher/room occupancy. The objective minimizes additional occurrences of a class/subject within the same day. It is a preference, not a hard daily limit. Solver workers are capped at two; each request is capped at thirty seconds (UI: ten).

A separate verifier checks the returned entries against the input before any solution is exposed. Results distinguish feasible, proven optimal for this objective, proven infeasible, and unknown after timeout. No strict rule is silently relaxed.

The browser retains input in localStorage; the server has no database or accounts. Input changes invalidate visible output. CSV exports use the exact solved input snapshot.

## Scope and next milestones
This version supports one school/week, shared rooms, availability, class/teacher/room/whole-school views, configurable daily loads, hard subject caps, and required double periods. It does not yet support shifts, split groups, fixed placements, teacher-gap optimization, configurable priority tiers, manual dragging, or minimum-change rescheduling. Those require explicit schema, constraints and verifier updates together.

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
