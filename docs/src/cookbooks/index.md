# Cookbooks

Runnable examples demonstrating SourceryKit integration with popular agent frameworks.

## Single-Agent Examples

| Framework | Description | Domain |
|---|---|---|
| [OpenAI Agents SDK](openai_agents.md) | Basic agent with tool interception | Weather |
| [LangChain](langchain_agent.md) | LangChain agent integration | Weather |
| [Claude Agent SDK](claude_agent.md) | Claude agent integration | Weather |

## Multi-Agent Examples

| Framework | Description | Domain | Pattern |
|---|---|---|---|
| [LangGraph](langgraph_multi_agent.md) | Sequential pipeline with conditional routing | Travel agency | Fetcher → Evaluator → Healer |
| [CrewAI](crewai_multi_agent.md) | Flow with specialist agents | Invoice auditing | Specialists → Build → Evaluate |
| [OpenAI Agents SDK](openai_agents_multi_agent.md) | Orchestrator-driven verification | Customer support | Orchestrator → Specialists → Verify |
| [Claude Agent SDK](claude_agent_multi_tool.md) | Multi-tool-call verification | Weather | Same tool, multiple refs |

## Choosing an Example

- **Single-agent:** Start with [openai_agents](openai_agents.md) or [langchain_agent](langchain_agent.md) for basic integration.
- **Multi-agent with healing:** Use [langgraph_multi_agent](langgraph_multi_agent.md) for automatic error recovery.
- **Multi-agent with specialists:** Use [crewai_multi_agent](crewai_multi_agent.md) or [openai_agents_multi_agent](openai_agents_multi_agent.md).
