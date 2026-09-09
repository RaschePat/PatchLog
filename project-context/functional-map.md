# PatchLog — Functional Map

This file describes product behavior without prescribing visual design.

## Primary browsing flow

```text
Select game
  ↓
Load patch notes for that game
  ↓
Browse structured patch-change content
  ↓
Filter by relevant section / change type
  ↓
Search or inspect a specific change
```

## AI question flow

```text
Selected game
  +
User question
  ↓
Game-scoped retrieval
  ↓
Relevant patch chunks
  ↓
Grounded answer
  +
Sources / citations
  ↓
User can inspect the underlying patch evidence
```

## State that should remain meaningful

- Active game selection.
- Per-game chat history.
- Per-game retrieval scope.
- Current patch/filter/search state where applicable.
- Source/evidence references returned by AI answers.
- Navigation or highlighting that helps connect an answer to relevant patch content where supported by the current implementation.

## Functional invariants

1. A question asked while LoL is selected must remain scoped to LoL unless the user explicitly changes game.
2. Valorant and Overwatch follow the same game-scoped principle.
3. Same-name entities must not cause cross-game retrieval leakage.
4. AI answers should remain grounded in patch evidence rather than becoming unsupported general game advice.
5. Redesign may change where controls and information appear, but should not remove the core browse → inspect → ask → verify experience.