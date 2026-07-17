# Multi-Protocol AI Runtime Diagram

Bootstrap resolves the configured protocol once. Prompt execution depends only
on the `AIProvider` boundary.

```mermaid
flowchart TD
    Settings[ATLAS_AI_* Settings] --> Config[ProviderConfig]
    Config --> Factory[ProtocolFactory Registry]
    Factory -->|GEMINI| Gemini[Gemini Adapter]
    Factory -->|OPENAI_COMPATIBLE| OpenAI[OpenAI-Compatible Adapter]
    Factory -->|ANTHROPIC| Anthropic[Anthropic Adapter]
    Factory -->|OLLAMA| Ollama[Ollama Adapter]
    Gemini --> Provider[AIProvider]
    OpenAI --> Provider
    Anthropic --> Provider
    Ollama --> Provider
    Provider --> Executor[PromptExecutor]
    Templates[Prompt Management] --> Executor
    Executor -->|AIRequest| Provider
    Provider -->|AIResponse| Executor
```

Adding a protocol requires an adapter implementation plus factory registration.
Adding a vendor for an existing protocol requires configuration only.
