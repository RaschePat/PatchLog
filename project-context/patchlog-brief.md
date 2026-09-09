# PatchLog — Product Brief

## Product

PatchLog is a game patch-note RAG dashboard and chatbot for:
- League of Legends
- Valorant
- Overwatch

It collects Korean official patch notes, organizes them into game-scoped patch content, retrieves relevant changes with semantic search, and generates grounded answers with citations.

## Core user value

Users should be able to understand recent game changes without manually reading every full patch note, while still being able to trace AI answers back to patch evidence.

## Current capabilities

- Select one of the supported games.
- Browse recent patch notes for the selected game.
- View structured patch-change cards rather than only raw full documents.
- Filter patch content by game-relevant sections and change types.
- Search for relevant patch content.
- Ask the AI panel questions about patch changes.
- Keep retrieval and chat scope separated by game.
- Return grounded answers with patch citations/sources.
- Maintain separate chat history per game.
- Navigate from AI evidence back toward relevant patch content when supported by the current interaction.

## Critical product rule

The selected game is the authoritative retrieval scope. The chatbot must not infer a different game from the question and silently switch scope. Same-name entities across games must not leak results into one another.

## Current implementation status

The working UI is implemented in Streamlit and connected to the existing PatchLog API/data flow. The existing visual presentation is not a product requirement. Layout, styling, colors, component forms, and information hierarchy may be redesigned as long as meaningful product capabilities remain intact.

## Current task boundary

This experiment concerns redesigning the existing PatchLog dashboard experience. It does not require changing the underlying retrieval architecture, supported games, or backend product scope unless the user explicitly asks for that.