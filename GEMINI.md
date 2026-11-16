# Pragmatic Engineering Guidelines

Guidelines for high-reliability, production-grade software development.

## 1. Data Supremacy: The Data Model is the Architecture
- Define state layout, schemas, and data structures before writing business logic.
- Resolve edge cases and conditional branching by correcting the shape of the data, not by multiplying if/else statements.
- Prefer straightforward, flat data structures and pure functions over deep inheritance hierarchies.

## 2. Simplicity First: Minimal & Obvious Code
- Write the simplest code that solves the problem robustly.
- Avoid speculative abstractions, premature generalization, and enterprise design patterns (factories, managers) for simple tasks.
- Prioritize maintainability and readability over cleverness or terse syntax.

## 3. Surgical Changes: Diff Discipline
- Keep code changes strictly scoped to the user request or bug fix.
- Do not perform drive-by refactorings, reformat untouched code, or rename unrelated variables.
- Maintain existing codebase style and architectural conventions.
- Remove only the unused imports and dead code introduced by your own modifications.

## 4. Hardware & Runtime Awareness
- Optimize for real-world constraints: eliminate redundant database queries (N+1), heavy memory allocations, and unneeded network hops.
- Avoid speculative concurrency, thread synchronization, or complex async wrappers unless demonstrably necessary.

## 5. Backward Compatibility & Stability
- Do not break existing API contracts, database schemas, or public function signatures without explicit stakeholder approval and migration plans.
- Regressions are critical bugs; preserve expected consumer behavior.

## 6. Verifiable Proof: Proof Beats Confidence
- Define measurable acceptance criteria before completing tasks.
- Verify modifications with unit tests, integration tests, or verifiable reproduction steps.
- Formulate execution plans with verification checkpoints:
  ```text
  1. [Step] -> Verify: [Test or observable check]
  2. [Step] -> Verify: [Test or observable check]
  ```

## 7. Anti-Pattern Detection & Remediation
Reject and address:
- **Premature Abstraction:** Indirection without immediate concrete reuse.
- **Collateral Churn:** Modifying lines or files outside the core task.
- **Unsubstantiated Optimization:** Making code complex for performance without benchmark data.
- **Defensive / Voodoo Coding:** Adding arbitrary retries or fallbacks without understanding the root cause.
- **Special-Case Sprawl:** Conditional cascades that stem from an inadequate data model.
