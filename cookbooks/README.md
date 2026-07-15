# Cookbooks

Runnable examples demonstrating SourceryKit integration with popular agent frameworks.

## Single-Agent Examples

| Framework | Description | Domain |
|---|---|---|
| [OpenAI Agents SDK](https://provably.ai/docs/cookbooks/openai_agents) | Basic agent with tool interception | Weather |
| [LangChain](https://provably.ai/docs/cookbooks/langchain_agent) | LangChain agent integration | Weather |
| [Claude Agent SDK](https://provably.ai/docs/cookbooks/claude_agent) | Claude agent integration | Weather |
| [Claude Agent SDK](https://provably.ai/docs/cookbooks/claude_agent_multi_tool) | Multi-tool-call verification | Weather |

## Multi-Agent Examples

| Framework | Description | Domain | Pattern |
|---|---|---|---|
| [LangGraph](https://provably.ai/docs/cookbooks/langgraph_multi_agent) | Sequential pipeline with conditional routing | Travel agency | Fetcher → Evaluator → Healer |
| [CrewAI](https://provably.ai/docs/cookbooks/crewai_multi_agent) | Flow with specialist agents | Invoice auditing | Specialists → Build → Evaluate |
| [OpenAI Agents SDK](https://provably.ai/docs/cookbooks/openai_agents_multi_agent) | Orchestrator-driven verification | Customer support | Orchestrator → Specialists → Verify |

## Choosing an Example

- **Single-agent:** Start with [openai_agents](https://provably.ai/docs/cookbooks/openai_agents) or [langchain_agent](https://provably.ai/docs/cookbooks/langchain_agent) for basic integration.
- **Multi-agent with healing:** Use [langgraph_multi_agent](https://provably.ai/docs/cookbooks/langgraph_multi_agent) for automatic error recovery.
- **Multi-agent with specialists:** Use [crewai_multi_agent](https://provably.ai/docs/cookbooks/crewai_multi_agent) or [openai_agents_multi_agent](https://provably.ai/docs/cookbooks/openai_agents_multi_agent).
