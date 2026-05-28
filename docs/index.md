# SourceryKit SDK
Welcome to the developer documentation for the Provably Python SDK (SourceryKit). This SDK brings verifiable guardrails to autonomous Python agents, making every outbound HTTP call observable, enforceable, and auditable.


## New to SourceryKit?
Start with the [README](src/main.md) for installation, environment configuration, and complete integration examples.


## Core Architecture & Pillars
- Dive into the [Architecture Overview](architecture.md) for a deep dive into data topologies and verification design.
- See [HTTP Interception](intercept.md) to learn how network calls are caught and recorded.
- Learn about [Handoff & Evaluation](handoff.md) to construct structured data claims for deterministic validation.
- Review [Trusted Endpoints](trusted-endpoints.md) to administer strict target destination routing policies.


## API Reference & Development
- Explore the [API Reference](api.md) for a complete mapping of all public functions, classes, and types.
- See the [Contributing Guide](src/contribute.md) for codebase requirements, styling, and pull request procedures.
- Check out the [Changelog](src/changelog.md) for tracking version upgrades and release history.


---

```{toctree}
:maxdepth: 1
:caption: Provably

src/provably
```

```{toctree}
:maxdepth: 1
:caption: SourceryKit SDK

src/main
src/changelog
src/contribute
src/license
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
:caption: API Reference

api
```
