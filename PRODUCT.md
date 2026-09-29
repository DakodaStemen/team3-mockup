# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Students** (primary): CSUSB BS Computer Science students planning their path to graduation, especially after a failed course, a withdrawal, a lighter load, or a missed once-a-year offering.
- **Academic advisors**: check a generated plan for correctness; they care about flags, unconfirmed placements.
- **Instructor and class** (CSE 6550, Fall 2026): see the app in demos, often on a projector. It has to explain a what-if at a glance from across a room.

All three scenes matter equally over the next few weeks (confirmed 2026-09-28).

## Product Purpose

Build a valid term-by-term pathway from a student's history and the BS CS requirements, recalculate it when something changes, and explain the graduation impact. Success: a student or advisor sees what moved, why, and when they now graduate, without reading a degree audit.

## Positioning

PAWS, myCAP, roadmap PDFs, and Schedule Planner never show how one change ripples through a path. ADPP recalculates the whole pathway over the real prerequisite graph and shows the ripple. A deterministic engine makes every scheduling decision.

## Operating Context

Local web app (React + Vite frontend, FastAPI backend). Data is the public CSUSB 2026-27 catalog and 12 CSE roadmaps; students are synthetic unless a transcript is uploaded. Used on laptops and on a classroom projector.

## Capabilities and Constraints

- What-if events: Fail, Withdraw, Pass, Add Summer, Add Winter, Change Unit Load (3–21 units). Preview, then keep or discard; undo/reset history. When a setback delays graduation, the planner suggests the fewest opt-in Summer/Winter terms that win the time back (marked unconfirmed).
- Alternative pathways, bottleneck ranking (measured: the delay if each course is failed), prerequisite DAG (67 courses, 76 edges, AND/OR) on the plan's timeline, discrepancies, placements to confirm.
- Students are synthetic, each with past terms, or the user uploads an unofficial transcript (PDF, text, or CSV). An upload is parsed in memory, never saved, and shows what could not be read.
- Playwright e2e tests depend on accessible names, labels, and `data-testid` hooks; keep them.

## Brand Commitments

- Name: Adaptive Degree Pathway Planner (ADPP).
- Visual theme pinned by the team (2026-09-28): modern and minimal, matching the csusb.edu theme. Uses the CSUSB logo (`csusb-logo.svg`, supplied by the team) with the arc and mountain in CSUSB blue and the wordmark in CSUSB gray.
- Must always show: "Planning aid only: this is not an official degree audit or advising decision."

## Evidence on Hand

Real catalog data in `backend/planner/catalog.json`; synthetic students in `backend/planner/students.json`. No real student records, testimonials, or advisor endorsements exist; never imply them. The transcript parser has only seen a synthetic sample.

## Product Principles

1. The engine decides, and every decision is deterministic and explainable.
2. Show the ripple: every change explains what moved and what it costs.
3. Never hide uncertainty: unconfirmed offerings and discrepancies stay visible.
4. A planning aid, never an authority.

## Accessibility & Inclusion

WCAG AA contrast; status is never color-only (text labels like "(affected)"); keyboard-reachable controls; light theme by default with a remembered light/dark toggle (team request 2026-09-28).
