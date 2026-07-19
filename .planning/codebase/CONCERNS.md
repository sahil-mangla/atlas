# Codebase Concerns

**Analysis Date:** 2026-07-19

## Tech Debt

### Logging Infrastructure Not Implemented

**Issue:** Configuration for logging exists (`engine/config.py` defines `log_level` and `debug` settings) but no actual logging is used anywhere in the engine code.

**Files:** 
- `engine/config.py` (lines 43-46)
- All files in `engine/` subdirectories (no logger imports found)

**Impact:** 
- Impossible to debug production issues
- Cannot trace code execution flow
- Error diagnosis relies solely on exception propagation
- Performance profiling is blind

**Fix approach:** 
1. Add Python `logging` module setup in a centralized location (e.g., `engine/logging.py`)
2. Initialize logger in `atlas/_bootstrap.py` using `engine/config.py` settings
3. Add debug logs at service entry points and in critical paths
4. Add error context logs in exception handlers

---

### Repository Rollback Assumes `delete()` Method Exists

**Issue:** The `ProposalCommitUnitOfWork.rollback()` method in `engine/ai/unit_of_work.py` (line 36-41) assumes repositories have a `delete()` method via `getattr()`. If a repository doesn't implement it, a `RuntimeError` is raised during rollback—which is itself a failure condition.

**Files:** `engine/ai/unit_of_work.py` (lines 28-41)

**Impact:** 
- Rollback can fail and leave corrupted state
- New repository implementations can break existing commit logic if they don't provide `delete()`
- No graceful fallback mechanism

**Fix approach:**
1. Add abstract `delete()` method to repository base class/protocol
2. Enforce implementation in all repository types
3. Add tests for rollback failure scenarios
4. Consider compensating transactions instead of delete-based rollback

---

### Knowledge Service Inefficient Deduplication Check

**Issue:** In `engine/knowledge/services.py` line 106, the `create()` method calls `get_pending()` which fetches the entire pending list from the repository. The deduplication logic then iterates through both published and pending lists sequentially (lines 43-51) without any indexing.

**Files:** `engine/knowledge/services.py` (lines 105-112, 33-51)

**Impact:** 
- O(n) scan for every candidate creation
- Scales poorly as knowledge base grows
- Multiple repository calls for single operation
- No caching of published knowledge index

**Fix approach:**
1. Build in-memory index of published knowledge fingerprints
2. Cache published knowledge list at orchestration level
3. Use set operations for fingerprint checking instead of list iteration
4. Add repository method for fingerprint-based lookup

---

## Known Bugs

### Silent Exception Swallowing in Conversation Scan

**Issue:** In `engine/ai/fs_repository.py` lines 87-88, a bare `except Exception: continue` silently skips corrupted conversation files when scanning workspaces. This masks data corruption but is by design for robustness.

**Files:** `engine/ai/fs_repository.py` (line 87)

**Trigger:** Call `get_by_id()` with no project_id when a conversation file is corrupted

**Impact:** 
- Corrupted files are silently ignored instead of reported
- User cannot know data is lost
- Better than failing completely but hides problems

**Workaround:** Implement a separate validation/repair tool to audit conversation files

---

### Unused Parameters in Deprecation Function

**Issue:** In `engine/knowledge/services.py` line 152, the `deprecate()` method has parameters `_reason` and `_actor` prefixed with underscore but never uses them. This looks like incomplete implementation.

**Files:** `engine/knowledge/services.py` (lines 152-158)

**Trigger:** Call `deprecate()` and pass reason/actor parameters

**Impact:** 
- Deprecation reasons are not recorded
- No audit trail of who deprecated knowledge
- Metadata is lost

**Workaround:** Manually track deprecation reasons in separate documentation

---

### Architecture Service Problem Statement Bug

**Issue:** In `engine/ai/engineering_services.py` line 459, when creating an ADR (Architecture Decision Record), the problem statement is set to `decision.context` instead of using a dedicated problem statement field.

**Files:** `engine/ai/engineering_services.py` (lines 454-463)

**Trigger:** Create architecture proposal with architectural decisions

**Impact:** 
- ADR problem statement is duplicated from context
- Correct problem statement from draft is ignored
- Historical records will have incorrect problem statements

**Fix approach:** Use `decision.problem_statement` if available, or extract from context properly

---

## Security Considerations

### API Keys Properly Protected

**Status:** No issues found.

**Details:** 
- API keys (`gemini_api_key`, `ai_api_key`, etc.) are read from environment variables
- `.env` files are in `.gitignore`
- No hardcoded credentials in code
- Anthropic adapter uses proper header-based auth

---

## Performance Bottlenecks

### Filesystem-Based Repository Scalability Limits

**Problem:** All repositories use filesystem storage (JSON files) instead of a database.

**Files:** 
- `engine/ai/fs_repository.py`
- `engine/architecture/fs_repository.py`
- `engine/knowledge/fs_repository.py`
- All other `fs_repository.py` files in subsystems

**Cause:** 
- O(n) filesystem scans for queries
- No indexing capability
- No transaction support
- Concurrent access conflicts

**Current capacity:** 
- Works for single projects with <1000 entities
- Performance degrades with multiple concurrent projects

**Scaling path:** 
1. Migrate to SQLite for single-machine deployments
2. Support PostgreSQL for production
3. Add in-memory caching layer
4. Implement query indexing

---

### Knowledge Retrieval Sorting on Every Query

**Problem:** In `engine/knowledge/services.py` line 199, knowledge entries are sorted every time they're retrieved, even if they haven't changed.

**Files:** `engine/knowledge/services.py` (lines 190-202)

**Cause:** No sorting at storage time; all work deferred to query time

**Improvement path:** 
1. Store entries in sorted order or maintain sort index
2. Cache sorted results per stage
3. Invalidate cache only on publish/deprecate/supersede

---

### Deduplication Fingerprint Computation Not Cached

**Problem:** In `engine/knowledge/services.py` lines 35-39, fingerprints are recomputed on every deduplication check.

**Files:** `engine/knowledge/services.py` (lines 33-51)

**Cause:** Fingerprints computed at validation time but not stored until after deduplication

**Improvement path:**
1. Compute and cache fingerprint at draft creation
2. Lookup cached fingerprint instead of recomputing
3. Lazy-compute only for legacy data

---

## Fragile Areas

### Proposal Commit Unit of Work

**Files:** `engine/ai/unit_of_work.py`

**Why fragile:** 
- Depends on repositories having `delete()` method, but interface doesn't enforce it
- Uses `model_copy(deep=True)` to backup state—expensive for large aggregates
- Rollback can fail and leave partial state

**Safe modification:** 
1. Always test rollback scenarios when modifying repositories
2. Add repository compatibility checks in factory
3. Use immutable data structures where possible

**Test coverage:** Unknown (no visible tests for rollback scenarios)

---

### Knowledge Candidate Deduplication Logic

**Files:** `engine/knowledge/services.py` (lines 33-51)

**Why fragile:**
- Multiple list scans without error handling
- Relies on exact data matching for deduplication
- No handling for null/empty categories
- String normalization assumes ASCII text

**Safe modification:**
1. Add comprehensive test cases for edge cases (empty strings, unicode, duplicates)
2. Document normalization rules in comments
3. Add fuzzy matching tests

**Test coverage:** Partially tested (test_knowledge/test_services.py exists)

---

### CLI Parser and Renderer

**Files:** 
- `clients/cli/parser.py` (354 lines, 0% coverage)
- `clients/cli/renderer.py` (364 lines, 0% coverage)

**Why fragile:**
- Completely untested
- Human-facing output formatting is complex
- Parse error messages not verified
- No coverage for edge cases (empty input, very long strings, special characters)

**Safe modification:**
- Add at least 80% test coverage before making changes
- Test CLI parsing with invalid/boundary inputs
- Snapshot test rendering output

**Test coverage:** 0% (critical gap)

---

## Scaling Limits

### Filesystem I/O Scaling

**Resource:** Filesystem operations

**Current capacity:** 
- ~1000 entities per project before noticeable slowdown
- Single project isolation prevents inter-project contention
- No parallel access support

**Limit:** 
- Hits I/O throughput limits around 10K+ entities
- Concurrent CLI commands on same project will conflict
- No way to query across projects efficiently

**Scaling path:**
1. Add database abstraction layer
2. Support SQLite for local dev
3. Support PostgreSQL for multi-user deployments
4. Implement connection pooling and transaction management

---

### Memory Usage During Large Proposal Commits

**Issue:** In `engine/ai/engineering_services.py`, the transformers load and manipulate entire aggregate copies in memory.

**Files:** `engine/ai/engineering_services.py` (lines 388-483)

**Current capacity:** Works for typical projects with <100 components

**Limit:** Will use excessive memory for projects with thousands of components or deep hierarchies

**Scaling path:**
1. Stream processing instead of bulk loading
2. Implement pagination in transformer loops
3. Add memory profiling to tests

---

## Dependencies at Risk

### Google GenAI SDK Tightly Coupled

**Risk:** `engine/ai/adapters/gemini.py` directly imports `google.genai` and `google.genai.types`.

**Impact:** 
- Breaking changes in Google SDK require code updates
- Gemini provider unavailable if SDK updates are incompatible
- No version pinning constraints visible

**Migration plan:**
1. Update `pyproject.toml` to pin genai version
2. Add feature detection for SDK capabilities
3. Create adapter version compatibility matrix
4. Add fallback to HTTP-based adapter if SDK breaks

---

### Pydantic Dependency for Serialization

**Risk:** All domain models use Pydantic `model_copy()` and `model_dump()`.

**Impact:** 
- Heavy memory usage for deep copies
- No control over serialization format
- Breaking changes if Pydantic v3 changes API

**Migration plan:**
1. Consider dataclass alternative for read-only models
2. Use lightweight copying strategies (only copy mutable fields)
3. Pin Pydantic version in `pyproject.toml`

---

## Missing Critical Features

### No Audit Trail for Knowledge Operations

**Problem:** Knowledge candidate review (approve/reject/withdraw) lacks audit trails.

**Blocks:** 
- Cannot answer "who deprecated this knowledge?"
- Cannot trace decision history
- Compliance/governance requirements

**Files:** `engine/knowledge/services.py` (lines 117-183)

---

### No Validation Error Messages in User Feedback

**Problem:** Proposal validation errors are thrown but don't include context about which field failed or expected format.

**Blocks:** 
- Users cannot fix their proposals without guessing
- Validation exceptions lack actionable information

**Files:** `engine/ai/engineering_services.py` (lines 72-183)

---

### No Conflict Detection for Concurrent Edits

**Problem:** No mechanism to detect or handle concurrent edits to same proposal/project.

**Blocks:** 
- Multi-user scenarios can silently overwrite changes
- No optimistic locking
- No last-write-wins tracking

**Files:** All repository implementations

---

## Test Coverage Gaps

### AI Subsystem Completely Untested

**Untested area:** Entire AI generation, validation, and proposal pipeline

**Files:**
- `engine/ai/engineering_services.py` (0% coverage)
- `engine/ai/services.py` (0% coverage)
- `engine/ai/executor.py` (0% coverage)
- `engine/ai/factory.py` (0% coverage)
- `engine/ai/adapters/*` (0% coverage)
- `engine/ai/context.py` (0% coverage)

**Risk:** 
- Most critical path untested
- Bugs in proposal generation can't be caught before deployment
- No regression test suite for LLM prompt changes

**Priority:** **CRITICAL** - These are the core features of the platform

---

### CLI Layer Completely Untested

**Untested area:** All command parsing, application dispatch, and output rendering

**Files:**
- `clients/cli/application.py` (0% coverage)
- `clients/cli/parser.py` (0% coverage)
- `clients/cli/renderer.py` (0% coverage)
- `clients/cli/commands.py` (0% coverage)

**Risk:** 
- User-facing bugs can't be caught
- No validation of help text accuracy
- Error message rendering never tested
- Exit codes may be wrong

**Priority:** **CRITICAL** - Users interact through CLI

---

### Presentation Layer Untested

**Untested area:** Output formatting and component rendering

**Files:**
- `presentation/renderers/` (0% coverage)
- `presentation/views/` (0% coverage)
- `presentation/collectors/` (0% coverage)

**Risk:** 
- Output formatting bugs affect all commands
- Read models never validated
- Data transformation logic untested

**Priority:** **HIGH**

---

### Knowledge Extractor Edge Cases

**Untested area:** Knowledge extraction from different artifact types

**Files:**
- `engine/knowledge/extractors/architecture.py` (likely 0% coverage)
- `engine/knowledge/extractors/planning.py` (likely 0% coverage)
- `engine/knowledge/extractors/research.py` (likely 0% coverage)
- `engine/knowledge/extractors/evaluation.py` (likely 0% coverage)

**Specific gaps:**
- What happens with empty/malformed artifacts?
- Are circular references handled?
- Does extraction skip invalid entries?

**Priority:** **HIGH** - New subsystem with unknown coverage

---

## Architectural Concerns

### No Centralized Error Context

**Issue:** Exception messages are terse and don't include contextual information.

**Example:** `InvalidProposalException("Problem statement cannot be empty.")` doesn't indicate which proposal or project failed.

**Impact:** Difficult to debug in production

---

### Repository Interface Implicit, Not Explicit

**Issue:** Repositories inherit from abstract bases but don't enforce consistent interfaces.

**Example:** `delete()` method is optional but required for rollback

**Impact:** New implementations can break existing code

---

### Knowledge Layer Just Shipped

**Issue:** Knowledge subsystem added in commit `efc4170` (2 days ago).

**Impact:** 
- Likely untested in production scenarios
- May have undiscovered edge cases
- Database consistency not verified
- Deduplication algorithm not battle-tested

**Recommendation:** Extra vigilance for bug reports related to knowledge operations

---

## Overall Risk Assessment

| Category | Severity | Impact |
|----------|----------|--------|
| Test Coverage (AI/CLI) | **CRITICAL** | 30% overall coverage; entire platform untested |
| Missing Logging | **HIGH** | Production debugging impossible |
| Knowledge Layer Maturity | **HIGH** | Recently added, likely untested edge cases |
| Filesystem Scalability | **MEDIUM** | Works now; will fail at scale |
| Error Context | **MEDIUM** | Debugging harder than necessary |
| Rollback Fragility | **MEDIUM** | Data corruption possible if rollback fails |

---

*Concerns audit: 2026-07-19*
