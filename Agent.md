<!-- Copyright (c) 2026 QuantForgeSoftware. All rights reserved. -->
# Workflow Orchestration

## 1. Plan Node Default

— Enter plan mode for MY non—trivial task (3+ steps or architectural decisions)
— If something goes sideways, STOP and re—plan immediately — don't keep pushing
— Use plan mode for verification steps, not just building
— Write detailed specs upfront to reduce ambiguity

## 2. Subagent Strategy

— Use subagents liberally to keep main context window clean
— Offload research, exploration, and parallel analysis to subagents
— For complex problems, throw more compute at it via subagents
— One tack per subagent for focused execution

## Release notes

— Before adding or editing release notes, run `node scripts/prepare-release-notes.js` (git pull --ff-only, then stamp the newest entry from `version.json`).
— Never invent the version from conversation context; origin may already have bumped it.

## 3. Self—Improvement Loop

— After ANY correction from the user: update 'lessons.md'
— Write rules for yourself that prevent the same mistake
— Ruthlessly iterate on these lessons until mistake rate drops
— Review lessons at session start for relevant project

## 4. Verification Before Done

— Never mark a task complete without proving it works
— Diff behavior between main and your changes when relevant
— Ask yourself: "Would a staff engineer approve this?"
— Run tests, check logs, demonstrate correctness

## 5. Demand Elegance (Balanced)

— For non—trivial changes: pause and ask "is there a more elegant way?"
— If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
— Skip this for simple, obvious fixes
— don't over—engineer
— Challenge your own work before presenting it

## 6. Autonomous Bug Fizing

— When given a bug report: just fix it. Don't ask for hand—holding
— Point at logs, errors, failing tests
— then resolve them
— Zero context switching required from the user
— Go fix failing CI tests without being told how

## 7. Solution works
— Don't stop until you have a working solution. The solution must build without errors and pass all tests. Don't mark a task complete until you can demonstrate it works.

## Task Management

1. **Plan first**: Write plan to 'todo.md' with checkable items
2. **Verify plans**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High—level summary at each step
5. **Document Results**: Add review section to 'todo.md
6. **Capture Lessons**: Update 'lessons.mdS'after corrections

## Core Principles

— **Simplicity First**: Make every change as simple as possible. Impact minimal code.
— **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
— **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
