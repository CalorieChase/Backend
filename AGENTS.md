# AGENT.md

## Project Overview

This is a Python-based software project.

The codebase may include:

* Backend APIs
* Agentic workflows
* Database integrations
* External APIs and SDKs

---

## Core Rule

Before writing or modifying code, inspect the relevant parts of the repository.

Do not treat each task as an isolated coding problem.

Understand the existing architecture first, then make the smallest clean change that fits the current codebase.

---

## Before Writing Code

Before implementing any change:

1. Inspect the project structure.
2. Read the relevant existing files.
3. Identify how similar functionality is already implemented.
4. Search for reusable functions, classes, models, services, utilities, and constants.
5. Follow existing architecture and naming conventions.
6. Decide the smallest reasonable change required.
7. Write necessary comments but not too much! 

Do not immediately create new files, classes, utilities, or abstractions.

Prefer extending existing code when appropriate.

---

## Repository Structure

Follow the existing repository structure.

Preferable  file structure:

```text
app/
├── api/          # API routes and API-specific dependencies
├── agents/       # Agents, LangGraph nodes, graphs, and workflows
├── models/       # Pydantic models and domain models
├── schemas/      # Request/response schemas if separated
├── services/     # Business logic and external integrations
├── repositories/ # Database access logic
├── db/           # Database configuration and sessions
├── core/         # Configuration and shared application setup
├── utils/        # Small reusable utilities
└── main.py       # Application entry point

tests/            # Tests
```


## Code Reuse

Reuse existing code whenever reasonable.

Before adding new logic, search for an existing implementation.

Prefer:

* Existing services
* Existing utilities
* Existing models
* Existing schemas
* Existing constants
* Existing database helpers
* Existing agent nodes
* Existing abstractions

Avoid duplicating logic across multiple files.

If similar logic already exists, reuse or refactor it instead of creating another version.

Do not create a generic helper function unless it is actually reused or clearly improves the code.

---

## Keep Changes Focused

Only modify files needed for the requested task.

Do not:

* Refactor unrelated code
* Rename unrelated files
* Reformat the entire repository
* Replace working implementations without a reason
* Introduce new architectural patterns unnecessarily
* Change public APIs unless the task requires it

Prefer small, reviewable changes.

---

## Python Style

Write clean and idiomatic Python.

Follow these rules:

* Use type hints.
* Use descriptive variable and function names.
* Prefer simple code over clever code.
* Use simple human readable syntax over some complex ones.
* Prefer early returns when they reduce nesting.
* Avoid deeply nested conditionals.
* Avoid wildcard imports.
* Prefer `pathlib` over manual path string manipulation.
* Prefer f-strings for string formatting.
* Use constants instead of repeated magic values.
* Keep functions focused on one responsibility.
* Keep modules reasonably small.
* Avoid unnecessary inheritance.
* Avoid unnecessary global state.
* Avoid mutable default arguments.
* Handle `None` and optional values explicitly.
* Follow existing formatting conventions.

If the project has Ruff, Black, Flake8, MyPy, Pyright, or another configured tool, follow its configuration.

---

## Functions

Functions should be small enough to understand without excessive mental overhead.

A function should generally perform one clear task.

Prefer:

```python
def calculate_total(items: list[Item]) -> Decimal:
    ...
```

over vague naming such as:

```python
def process(data):
    ...
```

Avoid creating many tiny wrapper functions that add no useful abstraction.

---

## Classes

Create classes only when they provide meaningful structure.

Good reasons include:

* Managing state
* Representing a domain concept
* Encapsulating related behavior
* Implementing an established project pattern

Do not turn every function into a class.

Do not introduce inheritance when composition or simple functions are enough.

---

## FastAPI

FastAPI is used in the following way:

Keep route handlers thin.

Routes should generally handle:

* Request parsing
* Dependency injection
* Authentication/authorization
* Calling the appropriate service
* Returning the response

Business logic should not live directly inside route handlers.

Prefer:

```text
Route
  ↓
Service
  ↓
Repository / External API
```

Use Pydantic models for request and response validation.

Use FastAPI dependency injection when it improves testability or removes duplicated setup logic.

Do not create dependencies for trivial values.

---

## Business Logic

Business logic should usually live in service-layer code or the equivalent existing abstraction.

Avoid mixing:

* HTTP concerns
* Database queries
* Business rules
* External API calls

inside one large function.

Keep responsibilities separated when the existing project architecture supports it.

---

## Database Code

Follow the project's existing database patterns.

Do not mix multiple database access styles without a reason.

If repositories are used, keep database-specific queries there.

Be careful with:

* Transactions
* Session lifecycle
* Connection management
* N+1 queries
* Duplicate queries
* Missing indexes
* Race conditions
* Partial writes

Use transactions when multiple database operations must succeed or fail together.

Never silently swallow database errors.

---

## Dependencies

Do not install a new package unless it provides clear value.

Before adding a dependency:

1. Check whether the project already has a library that solves the problem.
2. Check whether the Python standard library is sufficient.
3. Consider whether implementing the small required behavior directly is simpler.
4. If adding a dependency, update the project's requirements.txt file and run 
```bash
pip install -r requirements.txt
```
---

## Configuration

Do not hardcode environment-specific values.

Use the project's configuration system.

Examples include:

* Environment variables
* `.env`
* Pydantic Settings
* Configuration classes

Never commit secrets such as:

* API keys
* Database passwords
* Authentication tokens
* Private credentials

Use `.env.example` or an equivalent template when appropriate.

---

## Error Handling

Handle errors where meaningful action can be taken.

Do not use:

```python
try:
    ...
except Exception:
    pass
```

Do not silently hide failures.

Catch specific exceptions when possible.

Errors should either:

* Be handled appropriately
* Be transformed into a meaningful application error
* Be logged and re-raised

Avoid wrapping every function in unnecessary `try/except` blocks.

---

## Logging

Use the project's logging system.

Do not use `print()` for production debugging unless the existing project explicitly does so.

Log useful information such as:

* Important state transitions
* External service failures
* Unexpected exceptions
* Background job failures

Avoid noisy logs inside tight loops.

---

## Comments

Do not over-comment code.

Bad:

```python
# Loop through users
for user in users:
    # Get the user ID
    user_id = user.id
```

The code already explains itself.

Comments should explain:

* Why something unusual is being done
* Non-obvious constraints
* Important tradeoffs
* Workarounds
* Edge cases

Comments should explain **why**, not repeat **what** the code does.

---

## Docstrings

Use docstrings for important public functions, classes, modules, or interfaces when useful.

Do not add large docstrings to obvious internal helper functions.

Keep docstrings concise.

---

## Naming

Follow existing naming conventions.

Python defaults:

```text
Variables: snake_case
Functions: snake_case
Classes: PascalCase
Constants: UPPER_SNAKE_CASE
Modules: snake_case.py
```

Use names based on responsibility.

Avoid vague names such as:

```text
data
temp
thing
stuff
handler2
manager_new
helper_function
```

unless the context makes the meaning obvious.

---

## API Models

Keep request, response, and database models separate when the architecture requires different responsibilities.

Do not expose database models directly through APIs unless that is an intentional existing pattern.

Validate user-controlled input.

Prefer explicit schemas over unstructured dictionaries for important application data.

---



## Tests

New behavior should be tested when appropriate.

Prioritize tests for:

* Business logic
* Important service behavior
* API endpoints
* Agent state transitions
* Database logic
* Bug fixes
* Important edge cases

Test:

* Expected behavior
* Failure behavior
* Important edge cases

Do not rewrite unrelated tests.

Do not make tests depend unnecessarily on real external APIs.

Mock external services when appropriate.

Prefer deterministic tests.

---


## Existing Code Has Priority

When this document conflicts with an established pattern in the repository, prefer the repository's existing conventions unless they are clearly broken or the task specifically requires changing them.

Consistency across the project is more important than blindly applying generic best practices.

---

## After Writing Code

Before considering a task finished:

1. Review the files that were changed.
2. Check imports.
3. Check type hints.
4. Check naming.
5. Check for duplicated logic.
6. Check for unnecessary complexity.
7. Check error handling.
8. Check obvious security issues.
9. Run relevant tests if available.
10. Run configured linting or formatting tools if available.
11. Make sure unrelated behavior was not changed.

Do not leave temporary debugging code.

Remove:

```text
print statements
unused imports
commented-out old code
temporary files
unused variables
debug flags
```

---

## Git
I am trying to increase my github contribution so after every small changes you can make a commit. For an example: You have 5 functions to implement and you have to do it one by one and make a commit after each function: 5 commit from that.



