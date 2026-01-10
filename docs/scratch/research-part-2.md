# Context-Specific Workflow Direction Patterns: Document, Develop and Learn.

Perfect! I've analyzed your project documents and researched the technical foundations. Let me create a comprehensive implementation guide tailored to your MCP Router project.

## MCP Router: Agent-Context Workflow Integration Guide

Based on your project documentation and the repository analysis, I've identified how to transform your foundational router (currently at Phase 1) into a sophisticated agent orchestration platform. Here's how the MCP repositories integrate with your specific architecture:

### Your Current Architecture Alignment

Your router design already implements **Pattern 2: Proxy-Based Routing**—the industry-recommended approach for aggregating multiple MCP servers[^2_1]. This positions you perfectly to add the three agent-context workflow patterns: **Documentation**, **Development**, and **Learning**.

### Pattern 1: Documentation Pipeline

**Your Use Case**: Automate technical documentation from codebases → Obsidian

**MCP Server Integration Flow**:

```
Trigger (Raycast/VS Code) 
  → Router :9090 
    → Repomix (pack codebase) 
      → Ollama Enhancement (deepseek-r1) 
        → Sequential Thinking (structure outline) 
          → Desktop Commander (write to Obsidian vault) 
            → SpellChecker (validate)
```

**Implementation** (`router/pipelines/documentation.py`):

```python
from router.jsonrpc import JSONRPCRequest, route_to_server
from router.middleware.ollama_enhance import enhance_with_system_prompt

async def documentation_pipeline(repo_path: str, project_name: str):
    # Step 1: Pack repository with Repomix
    pack_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "pack_repository",
            "arguments": {"path": repo_path, "format": "compressed"}
        },
        id=1
    )
    packed_output = await route_to_server("repomix", pack_request)
    
    # Step 2: Enhance documentation prompt via Ollama
    doc_prompt = f"Document this codebase for beginners:\n{packed_output['content']}"
    enhanced = await enhance_with_system_prompt(
        prompt=doc_prompt,
        system="""You are a technical documentation specialist. Create:
        - Architecture overview (max 500 words)
        - Setup instructions with exact commands
        - API reference with examples
        - Common pitfalls section
        Format in Markdown with code blocks.""",
        model="deepseek-r1"
    )
    
    # Step 3: Structure with Sequential Thinking
    plan_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "create_thought",
            "arguments": {"content": enhanced, "type": "plan"}
        },
        id=2
    )
    structured_doc = await route_to_server("sequential_thinking", plan_request)
    
    # Step 4: Write to Obsidian via Desktop Commander
    vault_path = f"~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault/Projects/{project_name}.md"
    write_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "write_file",
            "arguments": {"path": vault_path, "content": structured_doc['output']}
        },
        id=3
    )
    await route_to_server("desktop_commander", write_request)
    
    # Step 5: Spell check (syntax-aware for code blocks)
    check_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "check_file",
            "arguments": {"path": vault_path, "language": "en_US"}
        },
        id=4
    )
    return await route_to_server("spellchecker", check_request)
```

**Router Endpoint** (`router/main.py`):

```python
@app.post("/pipelines/documentation")
async def run_documentation_pipeline(
    repo_path: str,
    project_name: str,
    client: str = Header(None, alias="X-Client-Name")
):
    """
    Triggered from:
    - Raycast: Custom script with repo selection
    - VS Code: Extension command in workspace
    - Claude Desktop: Via MCP tool call
    """
    result = await documentation_pipeline(repo_path, project_name)
    return {
        "status": "complete",
        "obsidian_path": f"obsidian://vault/Projects/{project_name}",
        "spell_check_issues": result.get("issues", [])
    }
```

**Benefits for Your Workflow**:

- **Automated**: Trigger via `raycast://extensions/mcp-router/document-repo`
- **Context-Aware**: Ollama enhancement tailors tone for audience (beginner vs senior dev)
- **Searchable**: Obsidian storage enables graph view linking across projects
- **Quality-Controlled**: Spell checker catches typos in technical prose

### Pattern 2: Development Agent Team

**Your Use Case**: Feature request → Planning → Code → Testing → Commit

**MCP Server Integration Flow**:

```
Feature Request (Claude Desktop)
  → Memory Server (recall coding standards)
    → Sequential Thinking (break into tasks)
      → Ollama Enhancement (refine per task)
        → Code Runner (validate snippets)
          → Desktop Commander (run tests)
            → AutoGen Orchestrator (multi-agent coordination)
```

**Implementation** (`router/pipelines/development.py`):

```python
async def development_agent_pipeline(feature_request: str, repo_path: str):
    # Step 1: Retrieve project context from Memory Server
    memory_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "search_nodes",
            "arguments": {"query": f"project:{repo_path} coding_standards"}
        },
        id=1
    )
    project_context = await route_to_server("memory", memory_request)
    
    # Step 2: Plan with Sequential Thinking (architect agent)
    context_prompt = f"""
    Project Context: {project_context['entities']}
    Feature Request: {feature_request}
    """
    
    enhanced_plan = await enhance_with_system_prompt(
        prompt=context_prompt,
        system="""You are a senior software architect. Break this feature into:
        1. MECE tasks (mutually exclusive, collectively exhaustive)
        2. Dependency ordering (what must complete first)
        3. Complexity estimates (T-shirt sizes: S/M/L)
        4. Risk assessment (High/Medium/Low with mitigation)
        Output as JSON array of task objects.""",
        model="deepseek-r1"
    )
    
    plan_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "create_thought",
            "arguments": {"content": enhanced_plan, "type": "plan"}
        },
        id=2
    )
    task_list = await route_to_server("sequential_thinking", plan_request)
    
    # Step 3: Code generation (developer agent)
    code_changes = []
    for task in task_list['thoughts']:
        enhanced_code_prompt = await enhance_with_system_prompt(
            prompt=f"Implement: {task['content']}",
            system=f"""You are a senior Python developer following:
            - Style: {project_context.get('style_guide', 'PEP 8')}
            - Test Framework: {project_context.get('test_framework', 'pytest')}
            - Type Hints: Required
            - Docstrings: Google style
            Write implementation + tests in separate files.""",
            model="llama3"
        )
        
        # Validate with Code Runner before writing
        runner_request = JSONRPCRequest(
            method="tools/call",
            params={
                "name": "run_code",
                "arguments": {"code": enhanced_code_prompt, "language": "python"}
            },
            id=3
        )
        test_result = await route_to_server("code_runner", runner_request)
        
        if test_result['exit_code'] == 0:
            code_changes.append({
                "task": task['id'],
                "code": enhanced_code_prompt,
                "tests_passed": True
            })
    
    # Step 4: Write files via Desktop Commander
    for change in code_changes:
        write_request = JSONRPCRequest(
            method="tools/call",
            params={
                "name": "write_file",
                "arguments": {
                    "path": f"{repo_path}/{change['file_path']}",
                    "content": change['code']
                }
            },
            id=4
        )
        await route_to_server("desktop_commander", write_request)
    
    # Step 5: Run full test suite
    test_request = JSONRPCRequest(
        method="tools/call",
        params={
            "name": "execute_command",
            "arguments": {"command": "pytest", "cwd": repo_path}
        },
        id=5
    )
    return await route_to_server("desktop_commander", test_request)
```

**AutoGen Integration** (future enhancement):

```python
# router/agents/autogen_wrapper.py
from autogen import McpWorkbench

async def orchestrate_with_autogen(task_list):
    """
    Use AutoGen's multi-agent framework for complex workflows
    - Planner agent: Sequential Thinking MCP
    - Coder agent: Code Runner MCP
    - Reviewer agent: Custom review prompts
    """
    workbench = McpWorkbench()
    
    # Register your MCP servers as tools
    workbench.register_tool("sequential_thinking", "http://localhost:9090/mcp/sequential_thinking")
    workbench.register_tool("code_runner", "http://localhost:9090/mcp/code_runner")
    
    # Define agent team
    planner = workbench.create_agent("planner", tools=["sequential_thinking"])
    coder = workbench.create_agent("coder", tools=["code_runner"])
    
    # Execute conversation-driven workflow
    result = await workbench.run_conversation([
        {"speaker": planner, "message": "Plan this feature: ${feature_request}"},
        {"speaker": coder, "message": "Implement task 1 from plan"},
        # ... iterative back-and-forth
    ])
    
    return result
```

**Benefits for Your Workflow**:

- **Memory-Backed**: System recalls your coding standards automatically
- **Multi-Stage**: Architect → Developer → Reviewer mimics real team structure
- **Validated**: Code Runner tests before file writes (fail-fast)
- **Traceable**: Sequential Thinking provides audit trail of decisions

### Pattern 3: Continuous Learning Loop

**Your Use Case**: Capture knowledge from every AI interaction → Memory Server → Improve future responses

**MCP Server Integration Flow**:

```
AI Response (Claude/VS Code)
  → Extract entities/relations
    → Ollama Enhancement (synthesize knowledge)
      → Memory Server (store graph)
        → Context Sync (propagate to other devices)
```

**Implementation** (`router/middleware/learning_loop.py`):

```python
from router.jsonrpc import JSONRPCRequest, route_to_server

async def capture_knowledge(response_text: str, user_query: str):
    """
    Run after every AI response to extract learnings
    """
    # Step 1: Synthesize knowledge with Ollama
    synthesis_prompt = f"""
    User Query: {user_query}
    AI Response: {response_text}
    
    Extract reusable knowledge as entity-relation triples.
    """
    
    enhanced = await enhance_with_system_prompt(
        prompt=synthesis_prompt,
        system="""Extract knowledge as JSON triples:
        {
          "entities": [{"name": "Docker", "type": "technology"}],
          "relations": [{"subject": "Docker", "predicate": "requires", "object": "Colima"}],
          "insights": ["Docker Desktop consumes 4GB RAM vs Colima's 2GB"]
        }
        Focus on: definitions, best practices, common pitfalls, tool relationships.""",
        model="llama3"
    )
    
    # Step 2: Store in Memory Server
    knowledge = json.loads(enhanced)
    
    for entity in knowledge['entities']:
        create_entity = JSONRPCRequest(
            method="tools/call",
            params={
                "name": "create_entities",
                "arguments": {"entities": [entity]}
            },
            id=1
        )
        await route_to_server("memory", create_entity)
    
    for relation in knowledge['relations']:
        create_relation = JSONRPCRequest(
            method="tools/call",
            params={
                "name": "create_relations",
                "arguments": {"relations": [relation]}
            },
            id=2
        )
        await route_to_server("memory", create_relation)
    
    # Step 3: Sync to other devices (future - Context Sync MCP)
    # sync_request = JSONRPCRequest(...)
    # await route_to_server("context_sync", sync_request)
    
    return knowledge

# Integrate into router responses
@app.middleware("http")
async def learning_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Extract query and response from context
    if request.url.path.startswith("/mcp/"):
        user_query = request.state.get("original_prompt")
        ai_response = response.body.decode()
        
        # Background task to avoid blocking response
        asyncio.create_task(capture_knowledge(ai_response, user_query))
    
    return response
```

**Memory Server Configuration** (`configs/memory-config.json`):

```json
{
  "memory_file_path": "~/Library/Application Support/MCP-Router/knowledge-graph.json",
  "entities_schema": {
    "project": ["name", "language", "framework"],
    "tool": ["name", "category", "install_command"],
    "concept": ["name", "domain", "difficulty_level"]
  },
  "relation_types": [
    "requires", "alternative_to", "integrates_with", 
    "best_practice_for", "pitfall_in"
  ]
}
```

**Benefits for Your Workflow**:

- **Passive Learning**: No manual knowledge base maintenance
- **Cross-Session**: Memory persists across Claude Desktop restarts
- **Personalized**: System learns your specific tech stack/preferences
- **Compounding**: Each interaction makes future responses smarter

### Integration Checklist for Your Router

**Phase 2 Completion** (Next 2 weeks):

```bash
# 1. Add JSON-RPC models
touch router/jsonrpc.py  # Request/Response/Error classes

# 2. Implement enhancement middleware
touch router/middleware/ollama_enhance.py  # Per-client rules

# 3. Create pipeline modules
mkdir router/pipelines
touch router/pipelines/documentation.py
touch router/pipelines/development.py
touch router/pipelines/learning.py

# 4. Add MCP server configs
touch configs/mcp-servers.json  # STDIO + HTTP servers

# 5. Test with Claude Desktop
# Edit ~/Library/Application Support/Claude/claude_desktop_config.json
```

**Phase 3 Desktop Integration** (Weeks 3-4):

```bash
# 1. Claude Desktop
cp configs/claude-desktop.json ~/Library/Application\ Support/Claude/

# 2. VS Code
cp configs/vscode-mcp.json .vscode/

# 3. Raycast scripts
mkdir -p ~/Library/Application\ Support/Raycast/Scripts/
cp scripts/raycast-*.sh ~/Library/Application\ Support/Raycast/Scripts/

# 4. Obsidian MCP plugin
# Install community plugin, point to localhost:9090
```

**Phase 4 Monitoring Dashboard** (Month 2):

- **Tech Stack**: React + FastAPI WebSockets + D3.js for workflow viz
- **Features**:
    - Real-time server health (green/yellow/red indicators)
    - Token consumption charts (Ollama model usage)
    - Knowledge graph viewer (Memory Server entities)
    - Pipeline editor (drag-drop workflow builder)

### Configuration Files for Immediate Use

**`configs/enhancement-rules.json`**:

```json
{
  "claude_desktop": {
    "model": "deepseek-r1",
    "system": "Provide structured responses with clear reasoning. Use Markdown formatting.",
    "max_tokens": 2000
  },
  "vscode": {
    "model": "llama3",
    "system": "Code-first responses. Always include file paths. Minimal prose.",
    "max_tokens": 1500
  },
  "obsidian": {
    "model": "llama3",
    "system": "Format in Markdown. Include [[wikilinks]] for concepts and #tags for categories.",
    "max_tokens": 3000
  },
  "raycast": {
    "model": "llama3",
    "system": "Action-oriented. Suggest CLI commands. Keep responses under 200 words.",
    "max_tokens": 500
  }
}
```

**`docker-compose.yml`** (updated with all MCP servers):

```yaml
version: '3.8'

services:
  router:
    build: .
    ports:
      - "9090:9090"
    environment:
      - OLLAMA_HOST=ollama
      - OLLAMA_PORT=11434
    volumes:
      - ./configs:/app/configs
      - ~/.keychain:/root/.keychain:ro
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama

  # MCP servers as sidecars (HTTP transport)
  context7:
    image: context7/mcp-server:latest
    environment:
      - CONTEXT7_API_KEY=${CONTEXT7_API_KEY}

volumes:
  ollama_models:
```

### Common Pitfalls to Avoid

Based on the MCP Inspector issues you attached and best practices research:

1. **OAuth State Management**[^2_2]: Use `ks` (Keychain) for tokens, not environment variables
2. **Null Default Values**[^2_2]: Explicitly set `null` in JSON-RPC params, don't omit
3. **Progress Notifications**[^2_2]: Implement timeout reset for long-running Ollama enhancements
4. **STDIO vs HTTP Mixing**: Router must handle both transparently—use transport abstraction layer
5. **Token Limits**: Monitor Ollama context windows; Repomix compression helps but validate before sending

### Next Steps: Quick Wins

**This Week**:

1. Copy `router/pipelines/documentation.py` from above
2. Test documentation pipeline with one repo
3. Verify Obsidian integration (check vault path)

**Next Week**:

1. Add Memory Server to `docker-compose.yml`
2. Implement learning loop middleware
3. Test with 5-10 Claude Desktop interactions

**Month 1 Goal**: All three workflow patterns operational with your existing clients (Claude, VS Code, Obsidian)

**Would you like me to generate the complete implementation files for any specific pattern, or help debug the current `/ollama/enhance` endpoint integration with these workflows?**
<span style="display:none">[^2_10][^2_11][^2_12][^2_13][^2_14][^2_15][^2_16][^2_17][^2_18][^2_19][^2_3][^2_4][^2_5][^2_6][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://www.alibabacloud.com/blog/602266
[^2_2]: https://github.com/modelcontextprotocol/inspector
[^2_3]: HISTORY.md
[^2_4]: README.md
[^2_5]: REFACTOR_PLAN.md
[^2_6]: https://www.kubiya.ai/blog/model-context-protocol-mcp-architecture-components-and-workflow
[^2_7]: https://docs.jarvislabs.ai/blog/prompt-enhancing
[^2_8]: https://www.getknit.dev/blog/how-mcp-works-a-look-under-the-hood-client-server-discovery-tools
[^2_9]: https://johnwlittle.com/supercharging-ollama-mastering-system-prompts-for-better-results/
[^2_10]: https://dysnix.com/blog/mcp-architecture
[^2_11]: https://zeo.org/resources/blog/mcp-server-architecture-state-management-security-tool-orchestration
[^2_12]: https://www.youtube.com/watch?v=Pj-lQ5YlfVE
[^2_13]: https://stytch.com/blog/model-context-protocol-introduction/
[^2_14]: https://modelcontextprotocol.info/docs/concepts/architecture/
[^2_15]: https://mybyways.com/blog/llm-prompt-generation-with-ollama-in-comfyui
[^2_16]: https://modelcontextprotocol.io/specification/2025-03-26/basic
[^2_17]: https://api7.ai/blog/understanding-mcp-gateway
[^2_18]: https://www.reddit.com/r/StableDiffusion/comments/1ev2n7o/integrating_llms_with_ollama_for_advanced_and/
[^2_19]: https://modelcontextprotocol.io/specification/2025-06-18/architecture

