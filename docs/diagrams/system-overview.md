# Subsystem Interactions Diagram

This diagram illustrates how the core subsystems of ATLAS collaborate. The solid lines represent direct ownership or orchestration links, while the dotted lines show the Memory subsystem logging events as a cross-cutting concern.

```mermaid
graph TD
    Project[Project Subsystem]
    Workspace[Workspace Subsystem]
    Research[Research Subsystem]
    Planning[Planning Subsystem]
    Workflow[Workflow Subsystem]
    Architecture[Architecture Subsystem]
    Evaluation[Evaluation Subsystem]
    AI_Integration[AI Integration Subsystem]
    AI_Eng_Services[AI Engineering Services]
    Workflow_Orch[Workflow Orchestration]
    Memory[Memory Subsystem]

    Project --> Workspace
    Project --> Research
    Project --> Planning
    Project --> Architecture
    Project --> Workflow
    Project --> Evaluation
    Project --> Memory

    Workflow_Orch --> Workflow
    Workflow_Orch --> AI_Eng_Services
    Workflow_Orch --> Evaluation

    AI_Eng_Services --> AI_Integration
    AI_Eng_Services --> Architecture
    AI_Eng_Services --> Planning
    AI_Eng_Services --> Research
    AI_Eng_Services --> Evaluation

    Memory -.->|Logs events from| Project
    Memory -.->|Logs events from| Research
    Memory -.->|Logs events from| Planning
    Memory -.->|Logs events from| Architecture
    Memory -.->|Logs events from| Workflow
    Memory -.->|Logs events from| Evaluation
```
