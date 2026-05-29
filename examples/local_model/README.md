# Local LLM

This example demonstrates how to integrate SourceryKit with an agent workflow backed by a locally hosted, OpenAI-compatible LLM inference server. This setup works seamlessly with any modern serving engine that exposes a standard `/v1/chat/completions` REST endpoint.

## How It Works

1. **Tool Invocations:** The agent requests current London weather profiles via an external endpoint.
2. **Interception:** Outbound traffic is transparently captured and written to your local audit table.
3. **Local Inference:** The tool data packages into a prompt context and routes to your local inference instance.
4. **Handoff Validation:** The agent constructs an explicit assertion tracking payload. The evaluator verifies it against the ground-truth intercept tables, producing a **PASS** or **CAUGHT** verdict.


## Requirements

### Local Inference Engine Setup
Your local server must expose an OpenAI-compatible API layer. Below are examples of runtime engines you can choose from to back your agent:

#### Option A: Ollama
[Ollama](https://ollama.com) bundles open-source models into a lightweight local daemon across macOS, Linux, and Windows.
1. Download and install Ollama from the [official downloads page](https://ollama.com/download).
2. Fetch and run your preferred model via your terminal:
	```bash
	ollama run qwen2.5:0.5b
	```
3. Set your environment variables to target Ollama’s default server port:
	```bash
	export LOCAL_MODEL_URL="http://localhost:11434/v1/chat/completions"
	export LOCAL_MODEL="qwen2.5:0.5b"
	```

#### Option B: llama.cpp / llama-server
[llama.cpp](https://github.com/ggml-org/llama.cpp) provides plain-vanilla inference in pure C/C++ with zero dependencies. It includes `llama-server` for a lightweight drop-in API server.
1. Follow the llama.cpp [Getting Started Guide](https://github.com/ggml-org/llama.cpp) to download or build the binaries.
2. Launch the server pointing to a downloaded GGUF format model:
	```bash
	./llama-server -m models/qwen2.5-1.5b-instruct-q4_k_m.gguf --port 8080 -ngl 99
	```
3. Route your local script variables to the active `llama-server` instance:
	```bash
	export LOCAL_MODEL_URL="http://localhost:8080/v1/chat/completions"
	export LOCAL_MODEL="qwen2.5-1.5b"
	```

#### Option C: oMLX
[oMLX](https://github.com/jundot/omlx) is a local inference server explicitly built to leverage Apple Silicon via continuous batching and SSD tiered KV-caching.
1. Install and launch the application or use the CLI via the oMLX [Repository Guide](https://github.com/jundot/omlx):
	```bash
	omlx serve --model-dir ~/models
	```
2. Download or load a target MLX model using the web admin dashboard or via any OpenAI-compatible integration layer.
3. Direct your environment to the oMLX server endpoint:
	```bash
	export LOCAL_MODEL_URL="http://localhost:8000/v1/chat/completions"
	export LOCAL_MODEL="your-mlx-model-name"
	```

#### Option D: vLLM
[vLLM](https://github.com/vllm-project/vllm) is a fast, easy-to-use LLM serving engine built to maximize GPU utilization via PagedAttention.
1. Install vllm via pip as outlined in the vLLM [Installation Guide](https://docs.vllm.ai/en/latest/getting_started/installation/):
	```bash
	pip install vllm
	```
2. Fire up the server hosting a target model:
	```bash
	vllm serve Qwen/Qwen2.5-1.5B-Instruct --port 8000
	```
4. Configure your local script variables to match the active host instance:
	```bash
	export LOCAL_MODEL_URL="http://localhost:8000/v1/chat/completions"
	export LOCAL_MODEL="Qwen/Qwen2.5-1.5B-Instruct"
	```

#### Option E: Docker Model Runner
If you are using [Docker Desktop](https://www.docker.com/products/docker-desktop/) 4.40+, you can leverage the built-in [Docker Model Runner](https://docs.docker.com/ai/model-runner/) features in development.
1. Pull the default test model using the Docker CLI:
	```bash
	docker model pull huggingface.co/qwen/qwen3.5-0.8b-base
	```
2. The engine serves traffic at port `12434` automatically. Keep the script defaults or explicitly state them:
	```bash
	export LOCAL_MODEL_URL="http://localhost:12434/engines/v1/chat/completions"
	export LOCAL_MODEL="huggingface.co/qwen/qwen3.5-0.8b-base"
	```

## Environment Configuration
Configure the tracking environment using your project variables or an explicit `.env` file mapping:

| Variable                   | Description |
|----------------------------|-------------|
| `SOURCERYKIT_API_KEY`      | Your active integration token from the Provably dashboard. |
| `SOURCERYKIT_ORG_ID`       | Your target workspace organization UUID. |
| `SOURCERYKIT_POSTGRES_URL` | Network DSN connection string for your hosted Postgres intercept database. |
| `LOCAL_MODEL_URL`          | Target endpoint for local text generation. |
| `LOCAL_MODEL`              | Target model signature identifier. |


## Execution
Execute a standard, fully validated transaction tracking loop:
```bash
python agent_run.py
```
Execute a validation loop with forced data modification to simulate a data hallucination catch:
```bash
python agent_run.py --tamper
```