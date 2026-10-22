# BACKEND_GUIDE.md

# OluOra Backend Development Guide

Version: 1.0 (MVP)

---

# Purpose

This document defines the backend architecture, coding conventions, and engineering standards for OluOra.

Every backend feature should follow these guidelines to ensure consistency, maintainability, scalability, and security.

The backend should prioritize:

* Simplicity
* Clean architecture
* Testability
* Separation of concerns
* Scalability
* Cost efficiency

---

# Technology Stack

## Framework

* FastAPI

## Language

* Python 3.13+

## Database

* PostgreSQL

## ORM

* SQLAlchemy 2.0

## Migrations

* Alembic

## Validation

* Pydantic v2

## Authentication

* Google OAuth (YouTube)
* JWT Access Tokens

## AI Integration

* Provider-agnostic (OpenAI initially)

## Testing

* Pytest

---

# Project Architecture

The backend follows a layered architecture.

```text
Client
    │
    ▼
API Router
    │
    ▼
Service Layer
    │
    ▼
Repository Layer
    │
    ▼
Database
```

Each layer has a single responsibility.

---

# Folder Structure

```text
backend/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── dependencies/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   ├── ai/
│   ├── integrations/
│   └── main.py
│
├── tests/
├── migrations/
├── scripts/
└── requirements.txt
```

---

# Layer Responsibilities

## API Layer

Responsible for:

* Routing
* Request validation
* Authentication
* Returning HTTP responses

Routers should remain thin.

Never place business logic inside route handlers.

---

## Service Layer

Responsible for:

* Business logic
* AI orchestration
* Validation beyond schema rules
* External API communication

All application logic belongs here.

---

## Repository Layer

Responsible for:

* Database queries
* CRUD operations
* Transactions

Repositories should never contain business logic.

---

## Models

Represent database tables.

Models should only define:

* Fields
* Relationships
* Constraints

---

## Schemas

Responsible for:

* Request validation
* Response serialization

Never expose SQLAlchemy models directly.

---

# Request Lifecycle

Every request follows this order:

1. Authentication
2. Authorization
3. Validation
4. Business Logic
5. Database Access
6. Response Serialization

Never bypass this flow.

---

# Dependency Injection

Use FastAPI dependency injection for:

* Database sessions
* Current user
* Authentication
* Shared services

Avoid global state.

---

# Authentication

MVP uses Google OAuth for YouTube.

Flow:

1. User authenticates with Google.
2. Backend exchanges authorization code.
3. Backend retrieves user information.
4. Create or find user.
5. Generate JWT.
6. Return token.

All protected endpoints require JWT authentication.

---

# Authorization

Every resource must verify ownership.

Never trust IDs provided by the frontend.

Always verify:

```text
JWT User
      │
      ▼
Requested Resource
      │
      ▼
Ownership
```

Return:

* 401 if unauthenticated
* 403 if unauthorized

---

# Database Guidelines

* PostgreSQL is the source of truth.
* Use UUIDs for primary keys.
* Use foreign keys for relationships.
* Index frequently queried columns.
* Normalize data.
* Avoid duplicate records.

Never write raw SQL unless necessary.

---

# Models

Core models include:

* User
* SocialAccount
* Video
* Comment
* Analysis
* Insight
* Question
* Recommendation

Each model should have:

* UUID primary key
* Created timestamp
* Updated timestamp

---

# Repository Rules

Repositories should:

* Read from the database
* Write to the database
* Handle transactions

Repositories should not:

* Call AI providers
* Perform business logic
* Validate permissions

---

# Service Rules

Services should:

* Coordinate repositories
* Communicate with AI
* Communicate with external APIs
* Apply business rules

Services should not:

* Return HTTP responses
* Know about frontend implementation
* Execute raw SQL

---

# AI Integration

AI should be abstracted behind a dedicated service.

Example responsibilities:

* Comment preprocessing
* Embedding generation
* Topic clustering
* Insight generation
* Recommendation generation

The application should be able to switch AI providers with minimal code changes.

---

# External Integrations

External services belong inside the `integrations/` directory.

Examples:

* Google OAuth
* YouTube Data API
* OpenAI
* Email providers

Business logic should not be tightly coupled to third-party SDKs.

---

# Error Handling

Use consistent error responses.

Example:

```json
{
  "success": false,
  "error": {
    "code": "VIDEO_NOT_FOUND",
    "message": "Requested video does not exist."
  }
}
```

Never expose stack traces or internal exceptions to clients.

---

# API Standards

Follow REST principles.

Use:

* GET
* POST
* PATCH
* DELETE

Version APIs:

```text
/api/v1/
```

Use pagination for large collections.

Return consistent response structures.

---

# Logging

Log:

* Authentication
* Analysis requests
* AI calls
* External API failures
* Unexpected exceptions

Never log:

* Passwords
* Tokens
* API keys
* Secrets

---

# Testing

Every new feature should include:

* Unit tests
* Integration tests (where applicable)

Test:

* Services
* Repositories
* Authentication
* Authorization
* API endpoints

Avoid testing framework internals.

---

# Performance Guidelines

* Minimize external API requests.
* Cache expensive operations.
* Batch database writes where possible.
* Avoid N+1 queries.
* Paginate large datasets.
* Reuse stored AI analyses.

Optimize only after measuring bottlenecks.

---

# Security

Always:

* Validate input
* Authenticate users
* Verify ownership
* Sanitize user-generated content
* Use HTTPS
* Store secrets in environment variables

Never:

* Trust frontend validation
* Expose internal IDs unnecessarily
* Commit secrets to Git

---

# Background Processing (Future)

Long-running operations should eventually move to background workers.

Examples:

* Comment imports
* AI analysis
* Report generation

Email sending is already handled this way: sends are enqueued with FastAPI
`BackgroundTasks` and executed by `app/modules/email/tasks.py`, which opens its own
session, so a slow provider never blocks a request. The provider itself is
vendor-agnostic (`app/integrations/email/`, selected by `EMAIL_PROVIDER`).

API endpoints should remain responsive.

---

# Configuration

Store configuration in environment variables.

Examples:

```env
DATABASE_URL=

JWT_SECRET=

GOOGLE_CLIENT_ID=

GOOGLE_CLIENT_SECRET=

OPENAI_API_KEY=

FRONTEND_URL=

BACKEND_URL=

ENVIRONMENT=
```

Never hardcode configuration.

---

# Code Style

* Follow PEP 8.
* Use type hints everywhere.
* Prefer explicit code over clever code.
* Keep functions focused on one task.
* Keep files reasonably small.
* Use descriptive names.
* Write meaningful docstrings where necessary.

---

# Naming Conventions

Classes

* PascalCase

Functions

* snake_case

Variables

* snake_case

Constants

* UPPER_SNAKE_CASE

Files

* snake_case.py

Routes

* kebab-case or resource-based REST paths

---

# Git Workflow

* One feature per branch.
* Small, focused pull requests.
* Clear commit messages.
* Never commit generated files or secrets.
* Ensure tests pass before merging.

---

# Backend Principles

Every backend feature should satisfy these principles:

* Single Responsibility Principle
* Separation of Concerns
* DRY (Don't Repeat Yourself)
* Explicit over implicit
* Fail fast with meaningful errors
* Prefer composition over inheritance
* Build reusable services
* Design for future scalability without overengineering

---

# Definition of Done

A backend feature is considered complete only if:

* Business logic is implemented.
* Input validation is present.
* Authorization is enforced.
* Tests pass.
* Errors are handled gracefully.
* Logging is included where appropriate.
* API responses follow the project standard.
* Documentation is updated if required.

---

# Final Engineering Philosophy

The OluOra backend should remain predictable, modular, and easy to extend.

Every layer should have a clear responsibility, every request should follow a consistent lifecycle, and every feature should prioritize maintainability over cleverness.

Build for today's MVP while making decisions that allow the platform to evolve into a scalable audience intelligence system without major architectural rewrites.
