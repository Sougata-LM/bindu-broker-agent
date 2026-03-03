import json
import httpx
import asyncio

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat


planner = Agent(
    name="planner",
    instructions="""
    You are a task decomposition expert.
    Given a user's goal, break it into 2–4 concrete, independent subtasks.
    For each subtask, assign the best agent type from this list:
      - research_agent   → find facts, summarize web content
      - code_agent       → write or review code
      - writer_agent     → draft emails, reports, or creative content
      - analyst_agent    → interpret data, draw conclusions

    Respond ONLY with valid JSON in this format:
    {
      "goal": "<original goal>",
      "subtasks": [
        { "id": 1, "agent": "research_agent", "task": "<specific instruction>" },
        { "id": 2, "agent": "writer_agent",   "task": "<specific instruction>" }
      ]
    }
    """,
    model=OpenAIChat(id="gpt-4o"),
)


aggregator = Agent(
    name="aggregator",
    instructions="""
    You are a master synthesizer.
    You receive the original goal and a list of results from specialist agents.
    Combine them into one clear, coherent, well-structured final response.
    Be concise. Attribute each part to the agent that produced it.
    """,
    model=OpenAIChat(id="gpt-4o"),
)


AGENT_REGISTRY: dict[str, str] = {
    "research_agent": "http://localhost:3774",
    "code_agent":     "http://localhost:3775",
    "writer_agent":   "http://localhost:3776",
    "analyst_agent":  "http://localhost:3777",
}


async def dispatch_to_agent(agent_type: str, task: str) -> str:
    url = AGENT_REGISTRY.get(agent_type)
    if not url:
        return f"[No agent registered for '{agent_type}']"

    payload = {
        "messages": [{"role": "user", "content": task}]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{url}/run", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("result", "[empty response]")

    except (httpx.ConnectError, httpx.TimeoutException):
        return await _mock_agent_response(agent_type, task)


async def _mock_agent_response(agent_type: str, task: str) -> str:
    mock = Agent(
        instructions=f"You are a {agent_type}. Complete this task concisely.",
        model=OpenAIChat(id="gpt-4o-mini"),
    )
    result = mock.run(input=[{"role": "user", "content": task}])
    return str(result.content)


async def broker_run(goal: str) -> str:
    plan_response = planner.run(
        input=[{"role": "user", "content": f"Decompose this goal: {goal}"}]
    )

    try:
        plan = json.loads(str(plan_response.content))
    except json.JSONDecodeError:
        return "Planner returned invalid JSON. Try rephrasing your goal."

    subtasks = plan.get("subtasks", [])
    if not subtasks:
        return "No subtasks found in plan."

    results = await asyncio.gather(*[
        dispatch_to_agent(subtask["agent"], subtask["task"])
        for subtask in subtasks
    ])

    combined_input = f"Original goal: {goal}\n\nResults from specialist agents:\n"
    for subtask, result in zip(subtasks, results):
        combined_input += f"\n[{subtask['agent']} — Task #{subtask['id']}]\n{result}\n"

    final = aggregator.run(
        input=[{"role": "user", "content": combined_input}]
    )

    return str(final.content)


def handler(messages: list[dict[str, str]]) -> str:
    goal = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        None
    )
    if not goal:
        return "Please provide a task or goal."

    return asyncio.run(broker_run(goal))


config = {
    "author": "roy36tinku.1979@gmail.com",
    "name": "broker_agent",
    "description": (
        "An orchestration agent that decomposes any goal into subtasks, "
        "hires specialist Bindu agents in parallel, and synthesizes a unified result."
    ),
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "multi_agent": True,
        "parallel_dispatch": True,
    },
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
    },
    "x402": {
        "enabled": True,
        "price_per_call": 0.001,
        "currency": "USDC",
    },
}


if __name__ == "__main__":
    bindufy(planner, config, handler)
