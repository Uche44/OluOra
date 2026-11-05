# OluOra Content Strategy --- Agent Implementation Brief

## 1. Overview

OluOra is an AI-powered audience intelligence platform for content
creators. Its current core capability analyses comments on a creator's
YouTube videos and surfaces audience questions, pain points, content
requests, sentiment, and emerging interests.

The Content Strategy feature should extend that capability. It should
help creators move from **understanding what their audience is saying**
to **deciding what to create and planning how to create it**.

This must not become a generic AI content generator. Recommendations
should be grounded in evidence from the creator's audience wherever
possible.

## 2. Product objective

Build a workflow that allows a creator to:

1.  Review insights extracted from audience comments.
2.  Turn those insights into relevant content opportunities.
3.  Organise selected opportunities into a weekly content calendar.
4.  Generate useful, editable scripts and content briefs for planned
    posts.

The connection between audience feedback and each recommendation must be
clear.

## 3. Intended user journey

### Step 1 --- Analyse audience comments

Reuse the existing OluOra workflow:

1.  Creator signs in and connects their YouTube account.
2.  Creator selects one of their videos.
3.  OluOra retrieves the video's comments.
4.  The analysis process identifies patterns and produces structured
    insights.

Relevant insight types include: - Frequently asked questions. - Audience
pain points and problems. - Content or topic requests. - Sentiment and
audience reactions. - Emerging interests and recurring themes.

**Implementation note:** Reuse the existing comment retrieval and
analysis pipeline, data structures, and UI wherever practical. Do not
create a second analysis pipeline for Content Strategy.

### Step 2 --- Generate content opportunities

Use available audience insights to suggest specific content
opportunities.

Each opportunity should include: - **Suggested topic:** What the creator
could make content about. - **Why it matters:** The audience need,
question, or interest behind the suggestion. - **Supporting evidence:**
The insight or comment patterns that led to the suggestion. -
**Suggested format:** For example, tutorial, explainer, comparison, FAQ,
demonstration, or opinion piece. - **Suggested angle:** A useful way to
approach the topic. - **Priority/relevance:** Why the creator may want
to consider it.

Recommendations must be traceable to underlying audience evidence. Do
not present unsupported AI-generated ideas as if they came from audience
feedback.

Where possible, include references to the source video, insight record,
or representative comments. Respect existing privacy and data-access
rules when displaying comments.

Creators should be able to review opportunities and choose which ones to
develop.

### Step 3 --- Build a weekly content calendar

Allow creators to turn selected opportunities into a weekly content
plan.

The calendar should support: - Selecting a planning week. - Adding
opportunities to dates. - Choosing or editing content format. - Setting
a platform, where supported. - Setting a posting date and optional
time. - Editing the topic, angle, and notes. - Changing status
(e.g. Idea, Planned, In Progress, Ready, Published). - Moving, removing,
or rescheduling calendar items.

The calendar must be editable. AI-generated plans are starting points,
not fixed decisions.

Generated plans should account for the creator's stated posting cadence,
goals, preferred formats, and platform when those preferences are
available. Do not assume preferences that have not been provided.

For the first version, prioritise a clear weekly calendar over advanced
scheduling or automatic publishing.

### Step 4 --- Generate scripts and content briefs

A creator should be able to open a calendar item and generate a script
or content brief.

Generation should use: - The selected content opportunity. - The
audience insight and supporting evidence. - The creator's chosen topic
and angle. - The selected platform and content format. - Available
creator style and tone preferences.

A useful script/brief may contain: 1. Working title. 2. Hook --- an
opening designed to capture the intended audience's attention. 3. Main
script --- a coherent, usable draft. 4. Key talking points. 5. Examples
or demonstrations, where appropriate. 6. Call to action. 7. Optional
caption, description, or alternative title.

Creators must be able to edit generated content. The first AI output is
not necessarily final.

## 4. Creator voice and style

Generated scripts should suit the individual creator rather than sound
generic.

Support two ways of providing style context:

-   **Learn from existing content:** Where technically and legally
    feasible, use creator-provided or connected content (such as scripts
    or video transcripts) to infer tone, structure, vocabulary, and
    presentation style.
-   **Manual configuration:** Let creators specify preferences such as
    tone, language, audience, level of technical depth, preferred
    structure, and approaches to avoid.

These approaches should be compatible. A creator should be able to
configure preferences even if style learning is unavailable.

**Open product decision:** Confirm the initial source and scope for
style learning. Do not assume the current YouTube integration already
provides transcripts or that video content can be processed without
additional permissions or implementation.

## 5. Core product principles

1.  **Evidence-backed recommendations:** Make clear which audience
    insights support a suggestion.
2.  **Creator control:** Creators can edit, reject, rearrange, and
    personalise recommendations, calendar items, and scripts.
3.  **Useful specificity:** Prefer a small number of actionable
    suggestions over many vague ideas.
4.  **Context awareness:** Use creator audience, topic, platform,
    format, and preferences when available.
5.  **Separate evidence from generation:** Label audience-derived
    findings separately from AI-generated interpretations or
    suggestions.
6.  **Reuse existing systems:** Extend OluOra rather than rebuilding
    existing capabilities unnecessarily.

## 6. Suggested interface structure

Follow the existing application design system and information
architecture. These are functional areas, not necessarily separate
top-level navigation items.

### Content Opportunities

-   List/cards of suggested topics.
-   Explanation of the audience need behind each suggestion.
-   Supporting insight or comment evidence.
-   Suggested format and angle.
-   Controls to save, dismiss, or add an opportunity to the calendar.

### Content Calendar

-   Weekly calendar view and week navigation.
-   Content cards showing topic, format, platform, date, and status.
-   Ability to create an item from an opportunity or add one manually.
-   Ability to edit an item or generate its script.

### Script / Content Brief Editor

-   Editable generated output.
-   Sections for hook, script, talking points, examples, and CTA.
-   Regenerate all or part of the output where supported.
-   Access to the audience insight that informed the content.
-   Save changes to the calendar item.

### Creator Style Settings

-   Manual style and audience preferences.
-   Add/manage reference scripts or content if supported.
-   Clear indication of configured preferences versus inferred style.

## 7. Suggested data concepts

Inspect the current schema before adding tables or changing models.
Reuse existing entities wherever possible.

Likely concepts include:

-   **ContentOpportunity:** Proposed topic/angle, rationale, status, and
    links to supporting audience insights.
-   **ContentCalendarItem:** Planned content, date, platform, format,
    status, and optional link to an opportunity.
-   **ContentScript / ContentBrief:** Generated and edited content
    associated with a calendar item.
-   **CreatorStyleProfile:** Manual preferences and, if implemented,
    inferred style information and references.

These are conceptual entities, not prescribed table names or a final
database design.

Important relationships and constraints: - Opportunities should be
associated with the creator and relevant audience insights. - Calendar
items should belong to the creator and may reference an opportunity. -
Scripts/briefs should belong to a calendar item. - Style preferences
should be scoped to the creator. - All records must respect existing
ownership and authorisation rules. - Avoid duplicating comment or
insight payloads when stable references to existing records are
sufficient. - Consider what happens if a source video, comment, or
insight later becomes unavailable.

## 8. AI generation requirements

-   Use AI integration and service patterns already established in the
    codebase.
-   Keep prompts and generation logic in the backend; never expose
    secret API keys or privileged prompts in the frontend.
-   Validate and structure model output before saving or returning it.
-   Handle incomplete, malformed, or unavailable model responses
    gracefully.
-   Scope generation requests to the authenticated creator's data.
-   Do not invent audience statistics, comments, evidence, or
    percentages.
-   Do not claim numerical demand unless supported by analysis data.
-   If evidence is insufficient, say so and either request more data or
    clearly label a suggestion as a general idea.

## 9. Non-functional requirements

-   Follow existing architecture, coding conventions, naming patterns,
    and API response formats.
-   Preserve authentication, authorisation, and creator data isolation.
-   Add loading, empty, error, and success states.
-   Ensure calendar and editor interactions work on desktop and mobile.
-   Avoid unnecessary repeated AI calls. Persist useful generated
    results and regenerate only when requested or relevant inputs
    change.
-   Use the existing background-job approach for long-running tasks, if
    one exists.
-   Add tests for business logic, API behaviour, permissions, and
    important UI flows.
-   Do not introduce a new paid third-party service without approval.

## 10. Suggested implementation milestones

Work in small, independently testable milestones. Inspect the repository
and report the relevant files, services, models, and API routes before
making structural changes.

### Milestone 0 --- Repository inspection and plan

-   Inspect frontend, backend, database schema, AI integration,
    authentication, and comment-analysis workflow.
-   Identify reusable insight models and UI components.
-   Identify conventions for API responses, validation, background jobs,
    and tests.
-   Propose the smallest implementation plan that fits the current
    architecture.
-   Flag assumptions and blockers.

**Deliverable:** Repository assessment and milestone plan. Do not begin
broad implementation until the plan is approved.

### Milestone 1 --- Content opportunity generation

-   Define the opportunity data contract.
-   Generate opportunities from existing structured audience insights.
-   Persist/retrieve opportunities using existing patterns.
-   Return supporting insight references and rationale.
-   Build UI to review, save, and dismiss opportunities.
-   Add tests, including creator data-isolation checks.

**Acceptance criteria:** - A creator can generate and view opportunities
from available insights. - Each audience-derived opportunity links to
relevant supporting evidence. - Unsupported claims are not presented as
measured audience findings. - A creator cannot view or modify another
creator's opportunities.

### Milestone 2 --- Weekly content calendar

-   Define calendar item data contract and lifecycle.
-   Allow creators to add opportunities to a week.
-   Support manual calendar items.
-   Implement editing, rescheduling, removal, and status changes.
-   Build a responsive weekly calendar UI.
-   Add tests for ownership, validation, and calendar operations.

**Acceptance criteria:** - A creator can create a weekly plan from
selected opportunities. - Calendar items can be edited and moved between
dates. - Changes persist after reload. - Calendar data is isolated by
creator.

### Milestone 3 --- Script and content brief generation

-   Define structured script/brief output.
-   Generate from a calendar item and its supporting audience context.
-   Include creator style preferences where available.
-   Allow creators to edit and save generated output.
-   Add regeneration behaviour that does not unexpectedly discard user
    edits.
-   Test generation inputs, persistence, permissions, and failure
    handling.

**Acceptance criteria:** - A creator can generate a script or brief from
a calendar item. - Output reflects topic, format, audience context, and
available preferences. - Output is editable and saved. - Regeneration
does not silently overwrite creator-authored edits.

### Milestone 4 --- Creator style profile

-   Implement manual creator preferences first if no style profile
    exists.
-   Assess technical and permission requirements for learning style from
    scripts or transcripts.
-   Add reference-content ingestion only after confirming data sources
    and permissions.
-   Keep inferred style separate from explicit user preferences.

**Acceptance criteria:** - Creators can configure and update style
preferences. - Script generation uses those preferences. - The system
does not claim to have learned a creator's style when no reference
content has been analysed.

## 11. Out of scope for the initial version

Unless explicitly approved, do not include: - Automatic publishing to
social platforms. - Automatic scheduling/posting on behalf of
creators. - Full social media management. - A complete competitor
intelligence system. - Advanced predictive analytics. - A broad
multi-platform integration rebuild. - Unrequested redesign of unrelated
OluOra features.

The current product is YouTube-first. TikTok and other platform support
may be considered later. Do not imply an integration is available if it
is not implemented.

## 12. Agent working instructions

Before implementation:

1.  Read the repository `README`, architecture notes, environment
    examples, and any `AGENTS.md` or equivalent instructions.
2.  Inspect the existing implementation. Do not assume this brief
    exactly matches the current code.
3.  Identify existing models, API response formats, authentication
    dependencies, and frontend data-fetching patterns.
4.  Report proposed changes and wait for approval before starting
    Milestone 1.

During implementation:

-   Work on one milestone at a time.
-   Keep changes focused; avoid unrelated refactors.
-   Do not invent endpoints, model fields, environment variables, or
    integrations without checking the codebase.
-   Maintain compatibility between frontend expectations and backend
    responses.
-   Write and run relevant tests for each milestone.
-   Report files changed, implementation decisions, tests run, and known
    limitations.
-   Stop after each milestone and request approval before proceeding.

## 13. Open questions to resolve during planning

1.  Which existing audience-insight structures can be used directly as
    generation inputs?
2.  Should opportunities be generated automatically after analysis, or
    only when requested?
3.  What posting cadence and platform preferences are currently stored,
    if any?
4.  Which formats should the first version support (e.g. YouTube
    long-form, Shorts, or both)?
5.  What source material is available and permitted for creator-style
    learning: scripts, captions, transcripts, or manually supplied
    examples?
6.  Does the application already support background jobs for longer
    AI-generation tasks?

Resolve these by inspecting the codebase and confirming product
decisions. Do not silently make assumptions that affect user experience
or the data model.

## Definition of done

The initial Content Strategy feature is ready for review when a creator
can:

1.  Use existing OluOra audience analysis.
2.  Generate evidence-backed content opportunities from those insights.
3.  Select opportunities and organise them into an editable weekly
    calendar.
4.  Generate an editable script or content brief for a calendar item.
5.  See which audience insights informed each recommendation.
6.  Use the feature without accessing another creator's data or breaking
    existing OluOra workflows.

Deliver the work incrementally, with tests and a clear report after each
milestone.
