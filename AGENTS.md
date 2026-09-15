# AGENTS.md — Rules for Antigravity

1. **One task at a time.** Work only the task ID(s) listed as active in
   `planning/CURRENT_PHASE.md`. Do not jump ahead to later phases.
2. **Inspect before writing.** Read existing code/files touching the task
   before making changes. Do not assume — verify current state.
3. **Scope discipline.** Implement only what the task requires. No
   speculative features, no unrelated refactors, no new dependencies unless
   the task calls for them.
4. **Run tests.** Every task ends with running the relevant test suite
   (`pytest`, plus any integration/docker profile the task needs).
5. **No unverified DONE.** Never mark a task `DONE` in `TASK_TRACKER.md`
   without tests passing and acceptance criteria met. Use `NEEDS_REVIEW` if
   unsure.
6. **Keep trackers current.** After each task: update `TASK_TRACKER.md`
   status, `TEST_STATUS.md` results, and append to `SESSION_LOG.md`.
7. **Record bugs, don't hide them.** Any failing test not fixed in-session
   goes into `BUG_TRACKER.md` with status `OPEN`. Never delete or weaken a
   test to make it pass.
8. **Record architecture decisions.** Any deviation from
   `docs/ARCHITECTURE.md` or `docs/PHASES.md`, or any non-trivial technical
   choice, gets logged in `planning/DECISION_LOG.md` before implementation.
9. **Never silently change architecture.** If a task seems to require
   deviating from the documented design, stop, log the proposed change in
   `DECISION_LOG.md`, and flag it rather than implementing an undocumented
   alternative.
10. **Keep the project runnable.** `docker compose up` and `pytest` must
    succeed at the end of every session, even if a phase is incomplete.
11. **Advance phases only on acceptance criteria.** Do not move
    `CURRENT_PHASE.md` forward until the current phase's acceptance criteria
    (per `docs/PHASES.md`) are met and reflected in `TEST_STATUS.md`.
