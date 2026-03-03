# bindu-broker-agent
An agent that takes any natural language goal, breaks it into subtasks, and delegates each one to a specialist Bindu agent — research, writing, code review, or analysis. Results come back in parallel and get merged into one final response.

Built this as my submission for Bindu. The idea felt like the most natural fit for what Bindu is actually trying to do — instead of one agent trying to do everything, you have a coordinator that knows what it doesn't know and hires accordingly.

---

## How it works

1. You send a goal in plain English
2. A planner LLM breaks it into 2–4 subtasks and picks the right agent type for each
3. All subtasks get dispatched in parallel via A2A
4. X402 handles micropayments to each worker agent automatically
5. An aggregator LLM combines everything into one clean response

```
User
 │
 ▼
Broker Agent (port 3773)
 │
 ├── Planner → structured JSON subtask list
 │
 ├── research_agent (3774)  ──┐
 ├── writer_agent   (3776)  ──┼── parallel dispatch
 └── code_agent     (3775)  ──┘
                               │
                          Aggregator
                               │
                          Final response
```

If a worker agent isn't reachable it falls back to a local mock automatically, so you can run and demo the broker without needing all four agents live.

---

## Setup

```bash
uv add bindu agno httpx openai

export OPENAI_API_KEY="you can set it up on your own"

uv run broker_agent.py
```

---

## Try it

```bash
curl -X POST http://localhost:3773/run \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Research the top AI agent frameworks and write a short comparison"}]}'
```

---

## What I'd add next

- Pull agent URLs live from the Bindu Directory instead of a hardcoded registry
- Show a cost estimate before running ("this will use ~3 agents, ~$0.002")
- Stream partial results back as each agent finishes
- Retry logic when a worker agent fails mid-run

---

Made with [Bindu](https://github.com/getbindu/bindu)
