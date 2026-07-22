# Engineering Pipeline Diagram

This state diagram represents the chronological progression through the engineering lifecycle stages, showing both the standard forward path and valid backward iteration loops.

Matches `WorkflowTransitionService.VALID_TRANSITIONS` exactly (`engine/workflow/services.py`)
-- Problem_Definition and Implementation have no AI `StageExecutor`, so
Research and Architecture also have direct shortcut edges to Planning and
Review respectively, letting a project skip them entirely as optional
manual detours rather than mandatory waypoints.

```mermaid
stateDiagram-v2
    [*] --> Idea
    Idea --> Research
    Research --> Problem_Definition
    Research --> Planning : Skip Problem Definition
    Research --> Idea : Refine Goals
    Problem_Definition --> Planning
    Problem_Definition --> Research : Refine Requirements
    Planning --> Architecture
    Planning --> Problem_Definition : Refine Scope
    Architecture --> Implementation
    Architecture --> Review : Skip Implementation
    Architecture --> Planning : Adjust Milestones
    Implementation --> Review
    Implementation --> Architecture : Adjust Designs
    Review --> Iteration : Defects Found
    Review --> Completion : Pass Audits
    Review --> Implementation : Code Mismatch
    Iteration --> Completion : Resolved
    Iteration --> Review : Re-Verify
    Iteration --> Implementation : Major Refactor
    Completion --> Iteration : Post-Release updates
    Completion --> [*]
```
