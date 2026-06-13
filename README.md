# OpenAI vLLM SSO Proxy

A lightweight, production-ready proxy that:
- Provides OpenAI-compatible API
- Enforces SSO (JWT) authentication
- Allows only pre-approved users
- Routes requests to vLLM backends based on model
- Logs usage (tokens only) to SQLite
- Never logs prompts or completions

## Features
- FastAPI + async
- Docker-ready
- SQLite for usage + approved users
- Streaming support
- Configurable model routing

## Quick Start
1. Copy `config.example.yaml` to `config.yaml`
2. Set environment variables
3. `docker compose up --build`