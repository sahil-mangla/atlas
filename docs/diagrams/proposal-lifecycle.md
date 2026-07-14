# Proposal Lifecycle Diagram

This sequence diagram illustrates the complete proposal lifecycle: from generation and draft validation, through human review approval, to filesystem commit with rollback support.

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Developer
    participant WO as Workflow Orchestration
    participant ES as AI Engineering Service
    participant CA as Context Assembler
    participant Prov as AI Provider (Gemini)
    participant CS as Commit Service
    participant UOW as Unit of Work
    participant Repo as Filesystem Repository

    User->>WO: generate_proposal(project_id, instructions)
    WO->>ES: generate_proposal(project_id, instructions)
    ES->>CA: assemble_context(project_id)
    CA-->>ES: ContextPayload (Approved Snapshots)
    ES->>Prov: generate(request)
    Prov-->>ES: Raw JSON Content
    ES->>ES: model_validate() & wrap in AIProposal (DRAFT)
    ES-->>User: AIProposal[T]
    
    User->>WO: process_review_decision(APPROVE / REJECT)
    alt REJECT
        WO->>WO: Set proposal to REJECTED & save history
        WO-->>User: Return (Generation stopped)
    else APPROVE
        WO->>WO: Set proposal to APPROVED
        WO->>CS: commit_proposal(project_id, proposal)
        CS->>CS: Run Validator (Check semantic rules)
        CS->>UOW: begin() (Deep copy existing aggregates)
        critical Transform and Persist
            CS->>Repo: Save new entities / freeze snapshot
        option Commit Exception (Rollback)
            CS->>UOW: rollback() (Restore original files / delete new)
            CS-->>WO: Return Failure CommitResult
        end
        CS-->>WO: Return Success CommitResult
        WO->>WO: Evaluate Workflow Readiness & Transition Stage
        WO-->>User: Transition Success / Commit Success
    end
```
