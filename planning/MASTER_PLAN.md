# Master Plan

## Project
Multi-Agent Orchestration System — Python/LangGraph, OpenAI+Anthropic, FastAPI,
PostgreSQL, ChromaDB, Redis/Celery, Streamlit. See `docs/ARCHITECTURE.md` and
`docs/PHASES.md` for full detail.

## Roadmap Tiers

### MVP (Phases 1–8)
Foundations, data layer, tool system, single-agent then multi-agent LangGraph
flow, async Celery execution, HITL, FastAPI. Produces a working, API-driven,
async, escalatable agent system — no UI polish, minimal observability.

### Post-MVP (Phases 9–11)
Streamlit UI, full observability (logging/tracing/metrics), evaluation harness.

### Production Hardening (Phase 12)
Auth, secrets, hardened Docker build, load testing, runbook.

## Phase Status

| Phase | Name | Status |
|---|---|---|
| 1 | Foundations & Scaffolding | DONE |
| 2 | Data Layer (PostgreSQL) | DONE |
| 3 | Tool System | DONE |
| 4 | Single-Agent LangGraph Flow | TODO |
| 5 | Multi-Agent Graph & Semantic Memory | TODO |
| 6 | Async Execution (Celery) | TODO |
| 7 | Human-in-the-Loop | TODO |
| 8 | FastAPI API Layer | TODO |
| 9 | Streamlit UI | TODO |
| 10 | Observability | TODO |
| 11 | Evaluation Harness | TODO |
| 12 | Production Hardening | TODO |

## Rules of Engagement
See `AGENTS.md`. Do not start a phase until the prior phase's acceptance
criteria are met and recorded in `planning/TEST_STATUS.md`.
