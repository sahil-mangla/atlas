# Workflow Stage Execution

ATLAS separates stages that can produce AI proposals from stages that require
direct human workflow activity.

| Stage | Execution mode |
|---|---|
| IDEA | Human-driven setup and objective definition |
| RESEARCH | AI-assisted proposal generation with human approval |
| PROBLEM_DEFINITION | Human-driven refinement |
| PLANNING | AI-assisted proposal generation with human approval |
| ARCHITECTURE | AI-assisted proposal generation with human approval |
| IMPLEMENTATION | Human-driven implementation |
| REVIEW | AI-assisted evaluation proposal generation with human approval |
| ITERATION | Human-driven iteration selection |
| COMPLETION | Human-driven completion decision |

The public `execute_stage` operation is valid only for the active AI-assisted
stage. Human-driven stages progress through workflow commands and do not have an
AI stage executor.

## Progressing through a human-driven stage

Every stage transition -- AI-assisted or human-driven -- sets a list of
default active objectives for the newly entered stage
(`DEFAULT_STAGE_OBJECTIVES` in `engine/workflow/services.py`), and
`workflow transition` is blocked until those objectives are cleared.

For AI-assisted stages, objectives clear automatically the moment the
stage's proposal is committed (`ApproveProposalCommand`).

For human-driven stages -- PROBLEM_DEFINITION, IMPLEMENTATION, ITERATION,
COMPLETION -- there is no proposal to commit, so objectives must be cleared
explicitly with `CompleteObjectiveCommand` (`atlas workflow
complete-objective`), one objective string at a time. `workflow status`
lists the current stage's active objectives. Once all of them are cleared,
`workflow transition` becomes unblocked.

This is what makes it possible for a project to reach COMPLETION using only
public interfaces:

```
atlas workflow status --project-id <uuid>
# Objectives: Address review feedback, Resolve blocking bugs

atlas workflow complete-objective --project-id <uuid> --objective "Address review feedback"
atlas workflow complete-objective --project-id <uuid> --objective "Resolve blocking bugs"

atlas workflow transition --project-id <uuid>
# current_stage: completion
```
