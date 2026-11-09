---
sidebar_position: 1
slug: /intro
title: Introduction
description: Overview of Workflow Agent and handbook navigation.
---

# Introduction

**Workflow Agent** is an autonomous workflow automation service built with **FastAPI** and **LangGraph**. It translates natural language user goals into structured execution plans, validates dependencies and security policies, retrieves standard operating procedures (SOPs) from a **Qdrant** vector store, supports human-in-the-loop approvals, and reliably executes actions with automatic verification and error recovery.

---

## Core Capabilities

| Feature | Description |
|---|---|
| **Goal Parsing & Planning** | Converts user requests into structured, multi-step execution plans. |
| **SOP Retrieval** | Finds relevant procedures from Qdrant vector database to guide plan generation. |
| **DAG Validation & Policy Enforcement** | Validates step dependencies and flags sensitive actions for approval. |
| **Human-in-the-Loop Approval** | Pauses execution using LangGraph interrupts for sensitive tasks or bulk modifications. |
| **Tool Execution** | Executes mock tools (tasks, calendar checks, notifications, template searches). |
| **Verification & Recovery** | Validates execution results, retries transient errors (up to 3 times), and replans on logical errors. |
| **State Persistence** | Checkpoints workflow state across invocations using PostgreSQL or in-memory storage. |

---

## Documentation Overview

| Section | Description |
|---|---|
| [Getting Started](./getting-started) | Prerequisites, environment setup, and running with Docker or locally |
| [Architecture](./architecture) | Workflow state graph diagram, nodes, checkpointing, and execution lifecycle |
| [API Reference](./api-reference) | Endpoints, request/response formats, and approval resume flow |
| [Configuration](./configuration) | Environment variables for LLM, Qdrant, and PostgreSQL |
| [Contributing](./contributing) | Development setup, testing, formatting, and contribution guidelines |
