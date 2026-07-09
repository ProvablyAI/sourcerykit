# SourceryKit SDK
Welcome to the developer documentation for the Provably Python SDK (**SourceryKit**). This SDK brings verifiable guardrails to autonomous Python agents, making every outbound HTTP call observable, enforceable, and auditable.

## New to SourceryKit?
* Start with the [README](src/main.md) for installation, environment configuration, and quick start concepts.
* Follow the [End-to-End Walkthrough](example.md) for a step-by-step code execution blueprint using local simulated steps.

## Core Architecture & Pillars
* Dive into the [Architecture Overview](architecture.md) for a deep dive into data topologies and verification design.
* See [HTTP Interception](intercept.md) to learn how network calls are caught and recorded.
* Learn about [Handoff & Evaluation](handoff.md) to construct structured data claims for deterministic validation.
* Review [Trusted Endpoints](trusted-endpoints.md) to administer strict target destination routing policies.

## Cookbooks
Explore how to integrate SourceryKit seamlessly into your favorite production development stack — see the [Cookbooks Overview](src/cookbooks/index.md) for a full comparison table and guidance on choosing an example.

## API Reference & Development
* Consult the [CLI Reference](cli.md) for all available commands, options, and usage examples.
* Explore the [API Reference](api.md) for a complete mapping of all public functions, classes, and types.
* See the [Contributing Guide](src/contribute.md) for codebase requirements, styling, and pull request procedures.
* Check out the [Changelog](src/changelog.md) for tracking version upgrades and release history.

---

```{toctree}
:maxdepth: 1
:titlesonly:

Provably Technologies <src/provably>
```

```{toctree}
:maxdepth: 1
:caption: SDK Documentation

src/main
src/changelog
src/contribute
src/license
cli
```

```{toctree}
:maxdepth: 1
:caption: Getting Started

onboarding
example
```

```{toctree}
:maxdepth: 1
:caption: Cookbooks

src/cookbooks/index
src/cookbooks/openai_agents
src/cookbooks/langchain_agent
src/cookbooks/claude_agent
src/cookbooks/openai_agents_multi_agent
src/cookbooks/crewai_multi_agent
src/cookbooks/langgraph_multi_agent
src/cookbooks/claude_agent_multi_tool
```


```{toctree}
:maxdepth: 2
:caption: Architecture & Pillars

architecture
intercept
handoff
trusted-endpoints
```

```{toctree}
:maxdepth: 1
:caption: Migration Guides

migrations/v1_0/v1_0
```

```{toctree}
:maxdepth: 1
:caption: API Reference

src/api
```
