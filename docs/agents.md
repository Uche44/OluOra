# AGENTS.md

# OluOra AI Development Rules

Version: 1.0

---

# Purpose

This document defines the rules every AI coding agent must follow while contributing to the OluOra codebase.

The objective is to produce production-quality, maintainable, consistent, and fully tested code throughout development.

---

# General Principles

* Build production-ready code only.
* Prefer simplicity over cleverness.
* Never over-engineer the MVP.
* Follow the project documentation before making implementation decisions.
* Keep the codebase clean, modular, and scalable.
* Favor readability and maintainability over writing fewer lines of code.

---

# Milestone-Based Development

The entire project **must be broken into 25 independent milestones**.

Each milestone must:

* Deliver one complete feature or subsystem.
* Be fully functional on its own.
* Be independently testable.
* Not leave partially implemented functionality.
* Integrate cleanly with previous milestones.

**Do not begin the next milestone automatically.**

At the end of every milestone:

1. Verify all acceptance criteria are met.
2. Ensure tests pass.
3. Summarize what was completed.
4. Explain any architectural decisions.
5. Ask for explicit permission before proceeding to the next milestone.

---

# Implementation Order

Always build from the foundation upward.

Recommended order:

1. Project setup
2. Database
3. Authentication
4. API foundation
5. Core business features
6. AI features
7. Dashboard
8. Polish and optimization

Never implement advanced features before foundational systems exist.

---

# Frontend & Backend Contract

Backend responses **must always match frontend expectations**.

This includes:

* Response shape
* Property names
* Data types
* Nullable fields
* Pagination format
* Error format

The backend is not allowed to arbitrarily change API contracts.

If a contract change is necessary:

* Update the API specification.
* Update the frontend.
* Update backend implementation.
* Keep everything synchronized.

---

# API Rules

Every endpoint must:

* Follow REST conventions.
* Return standardized responses.
* Validate input.
* Verify authentication.
* Verify resource ownership.
* Return proper HTTP status codes.

Never expose:

* Internal exceptions
* Stack traces
* Database errors
* Secrets

---

# Type Safety

Never use ambiguous types.

Always use:

* TypeScript interfaces/types on the frontend.
* Pydantic schemas on the backend.
* Strong typing in Python.

Avoid:

* `any`
* untyped dictionaries
* implicit data structures

---

# Single Source of Truth

Avoid duplicated logic.

Business logic belongs only in the backend.

Frontend should never duplicate backend rules.

Configuration should exist in one location.

Constants should not be duplicated across files.

---

# Separation of Concerns

Each layer has one responsibility.

Frontend

* UI
* State
* User interactions

Backend

* Business logic
* Authentication
* AI orchestration
* Data persistence

Database

* Data storage

Never mix responsibilities.

---

# Testing Requirements

Every milestone must include appropriate testing.

Before completion, verify:

* Feature works as expected.
* Existing functionality is unaffected.
* No runtime errors.
* No TypeScript errors.
* No Python linting or syntax errors.

A milestone is not complete until it has been tested.

---

# Code Quality

Every implementation should:

* Follow existing project conventions.
* Be modular.
* Avoid unnecessary abstraction.
* Avoid duplicated code.
* Use meaningful names.
* Include comments only where necessary.

Write code that another engineer can easily understand.

---

# File Organization

Keep files focused.

Avoid excessively large files.

If a file grows too large, refactor into smaller modules with clear responsibilities.

Follow the project's folder structure at all times.

---

# Database Rules

Use migrations for every schema change.

Never modify production schema manually.

Always:

* Use foreign keys.
* Use indexes where appropriate.
* Preserve referential integrity.

Avoid duplicate data whenever possible.

---

# AI Features

AI should only perform tasks requiring intelligence.

Do not use LLMs for deterministic operations.

Cache expensive AI outputs whenever possible.

Never regenerate existing analyses unless explicitly requested.

Design AI services so providers can be swapped with minimal changes.

---

# Performance

Prefer lazy loading.

Load only the data required for the current page.

Never fetch comments unless analysis is requested.

Avoid unnecessary database queries.

Paginate large datasets.

Optimize expensive operations only after measuring performance.

---

# Security

Never trust client input.

Always:

* Validate requests.
* Authenticate users.
* Verify ownership.
* Sanitize user-generated content.
* Protect secrets.

Never hardcode credentials or API keys.

---

# Error Handling

Handle expected failures gracefully.

Return user-friendly error messages.

Log unexpected exceptions.

Never expose internal implementation details.

---

# Git Practices

Each milestone should produce a clean, reviewable commit.

Commit messages should clearly describe the completed work.

Avoid unrelated changes in the same commit.

---

# Documentation

When introducing a new feature:

* Update relevant documentation if needed.
* Keep API specifications synchronized.
* Keep architectural documentation accurate.

Documentation should evolve alongside the codebase.

---

# Completion Checklist

Before requesting approval to proceed, confirm that:

* All acceptance criteria are complete.
* Feature is fully functional.
* Tests pass.
* No linting errors exist.
* No type errors exist.
* API contract is respected.
* Documentation is updated if required.
* Code follows project conventions.

Only after all checks pass should permission be requested for the next milestone.

---

# Non-Negotiable Rules

* Never break existing functionality.
* Never leave incomplete implementations.
* Never skip testing.
* Never ignore errors or warnings.
* Never change API contracts without updating both frontend and backend.
* Never introduce unnecessary dependencies.
* Never implement features outside the current milestone.
* Never proceed to the next milestone without explicit user approval.

---

# Guiding Philosophy

Every decision should move OluOra toward becoming a robust, scalable audience intelligence platform while keeping the MVP lean, maintainable, and cost-effective.

When faced with multiple implementation options:

* Choose the simplest solution that satisfies the requirements.
* Prioritize maintainability over cleverness.
* Optimize for developer experience and long-term scalability.
* Deliver complete, production-ready milestones rather than partially finished features.
