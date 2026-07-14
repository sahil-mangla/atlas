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
