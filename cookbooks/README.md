# SourceryKit Cookbooks

Runnable examples demonstrating SourceryKit integration with popular agent frameworks.

## Single-Agent Examples

| Framework | Description | Domain |
|---|---|---|
| [OpenAI Agents SDK](openai_agents) | Basic agent with tool interception | Weather |
| [LangChain](langchain_agent) | LangChain agent integration | Weather |
| [Claude Agent SDK](claude_agent) | Claude agent integration | Weather |

## Multi-Agent Examples

| Framework | Description | Domain | Pattern |
|---|---|---|---|
| [LangGraph](langgraph_multi_agent) | Sequential pipeline with conditional routing | Travel agency | Fetcher → Evaluator → Healer |
| [CrewAI](crewai_multi_agent) | Flow with specialist agents | Invoice auditing | Specialists → Build → Evaluate |
| [OpenAI Agents SDK](openai_agents_multi_agent) | Orchestrator-driven verification | Customer support | Orchestrator → Specialists → Verify |

## Choosing an Example

- **Single-agent**: Start with `openai_agents` or `langchain_agent` for basic integration
- **Multi-agent with healing**: Use `langgraph_multi_agent` for automatic error recovery
- **Multi-agent with specialists**: Use `crewai_multi_agent` or `openai_agents_multi_agent`
