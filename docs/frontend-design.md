# OluOra Design System & Frontend Development Guide

## Purpose

This document defines the visual identity, UI principles, and implementation rules for OluOra.

It is the single source of truth for all frontend development.

Every page, component, interaction, and layout must follow this guide.

Consistency is more important than creativity.

---

# Design Philosophy

OluOra is not another analytics dashboard.

It is an AI intelligence platform.

The interface should feel:

* Premium
* Calm
* Elegant
* Editorial
* Intelligent
* Spacious
* Intentional
* Trustworthy

The experience should resemble a beautifully designed intelligence report rather than a traditional admin panel.

Every screen should communicate:

> "This product helps you make better decisions."

---

# Core Design Principles

## 1. Simplicity First

Remove unnecessary UI elements.

Only display information that helps the user make a decision.

Never add decorative components that do not improve usability.

---

## 2. Content Before Chrome

The content is the product.

Navigation, borders, shadows, and containers should never compete with the insights.

---

## 3. Whitespace is a Feature

Prefer generous spacing.

Never compress layouts simply to fit more content.

Users should feel relaxed while reading insights.

---

## 4. Calm Interfaces

Avoid overwhelming dashboards.

Break information into logical sections.

Use progressive disclosure.

Show summary first.

Allow deeper exploration later.

---

## 5. Every Screen Answers One Question

Landing Page

Why should I trust OluOra?

Dashboard

What should I do next?

Video Page

Which video needs attention?

Analysis Page

What is my audience telling me?

Recommendations

What content should I create next?

Settings

How do I control my experience?

Every page should have a primary purpose.

---

# Color System

## Primary

Deep Forest Green

Use for:

* Primary buttons
* Active navigation
* Links
* Charts
* Progress indicators

Never overuse.

---

## Accent

Warm Gold

Reserved for:

* AI insights
* Premium badges
* Success highlights
* Key metrics
* Logo icon

Gold is special.

Use sparingly.

---

## Background

Soft Off-White

The application should never use pure white backgrounds.

The interface should feel warm.

---

## Surface Colors

Cards should be slightly elevated from the background.

Avoid strong contrast.

---

## Text

Primary

Rich Charcoal

Secondary

Muted charcoal

Tertiary

Soft gray

---

## Borders

Very subtle.

Almost invisible.

---

# Typography

## Landing Page

### Playfair Display

Only use for:

* Hero titles
* Section titles
* Marketing headings

---

### Lora

Use for:

* Body text
* Buttons
* Descriptions
* Forms

---

## Dashboard

### Playfair Display

Only use for:

* Page titles
* Large metrics
* Section headers
* AI summary titles

---

### Lora

Use everywhere else.

Navigation

Tables

Forms

Cards

Charts

Comments

Labels

Buttons

Metadata

---

# Layout Rules

Maximum content width:

1280px

Use generous horizontal padding.

Desktop spacing should never feel cramped.

Use an 8-point spacing system.

Examples:

8px

16px

24px

32px

48px

64px

96px

Never invent arbitrary spacing.

---

# Border Radius

Cards

16px

Buttons

12px

Inputs

12px

Badges

999px

Dialogs

20px

---

# Shadows

Soft.

Diffuse.

Almost invisible.

Never use heavy drop shadows.

---

# Cards

Cards are the primary UI building block.

Every card should have:

* breathing room
* rounded corners
* subtle border
* soft elevation

Cards should never feel boxed in.

---

# Buttons

Primary

Forest Green

Filled

Secondary

Outline

Ghost

Text only

Never use more than one primary button in a section.

---

# Icons

Style:

Outline

Consistent stroke width

Minimal

Elegant

Never use filled icons unless necessary.

---

# Charts

Charts should feel like intelligence reports.

Preferred charts:

* Bar
* Line
* Area
* Donut

Avoid:

* 3D charts
* Pie charts with many slices
* Rainbow colors

Use only the brand palette.

---

# Navigation

Sidebar

Simple.

Minimal.

No decorative backgrounds.

Active item:

Forest Green indicator.

Top Navigation

Logo

Search

Notifications

Profile

Nothing more.

---

# Forms

Minimal labels.

Large inputs.

Comfortable spacing.

Clear validation.

No unnecessary fields.

---

# Tables

Minimal borders.

Large row height.

Readable typography.

Sticky headers.

Hover states.

---

# Empty States

Every empty state must include:

* Illustration
* Short explanation
* Primary CTA

Never leave blank screens.

---

# Loading States

Never show blank pages.

Always use skeleton loaders.

Long-running AI tasks should display progress.

Example:

✓ Fetching comments

✓ Cleaning data

✓ Understanding audience

✓ Detecting trends

✓ Generating recommendations

---

# Motion

Use subtle motion only.

Animations should feel smooth and calm.

Preferred:

Fade

Slide

Scale

Opacity

Never use:

Bounce

Elastic

Flash

Spin continuously

---

# Accessibility

Minimum contrast ratio:

WCAG AA

Keyboard accessible

Visible focus states

Proper ARIA labels

Readable font sizes

Never rely only on color.

---

# Responsive Design

Desktop first.

Support:

Desktop

Tablet

Mobile

Sidebar collapses on tablet.

Cards stack naturally.

Tables become cards on mobile.

---

# Component Library

Create reusable components only.

Never duplicate UI.

Core components include:

* Button
* Input
* Select
* Search
* Card
* Badge
* Avatar
* Modal
* Drawer
* Toast
* Tabs
* Breadcrumb
* Skeleton
* Tooltip
* Empty State
* Error State
* Chart Container
* Metric Card
* AI Insight Card
* Video Card
* Comment Card
* Recommendation Card

All pages must compose these components instead of creating custom variants.

---

# Dashboard Philosophy

Do not build dashboards that simply display data.

Every dashboard section should answer a question or recommend an action.

Replace passive metrics with actionable insights whenever possible.

Instead of:

2,148 comments

Prefer:

2,148 comments analyzed

Top insight:

Most viewers are requesting a beginner tutorial.

Every metric should lead to a recommendation.

---

# AI Components

AI-generated content should always be visually distinct.

Use:

Gold accent

Small AI badge

Insight icon

Recommendation cards should feel more premium than standard cards.

---

# Implementation Standards

* Use Next.js App Router.
* Use TypeScript exclusively.
* Use Tailwind CSS for styling.
* Use shadcn/ui as the component foundation.
* Extend shadcn components instead of replacing them.
* Use Lucide icons consistently.
* Use Framer Motion for subtle animations only.
* Use TanStack Query for server state.
* Use Zustand for lightweight client state.
* Create reusable layout components.
* Keep components small and composable.
* Avoid inline styles.
* Follow a mobile-friendly, responsive approach.
* Ensure every UI component is reusable and documented.

---

# Final Goal

Every page should feel like it belongs to the same product.

The experience should combine:

* Stripe's craftsmanship
* Linear's simplicity
* Notion's clarity
* Apple's restraint
* The editorial elegance of a premium magazine

OluOra should feel less like an analytics tool and more like an AI intelligence workspace that creators enjoy returning to every day.
