# Autonomous Code Generation Agents

**Version:** 3.0.0
**Status:** Implemented
**Epics:** 9-12

## Overview

This module implements autonomous AI agents that can plan, code, test, review, and create pull requests automatically. The agents work together to transform natural language requests into production-ready code changes.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                             │
│              "Add email validation"                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│              Agent Orchestrator                             │
│         (Coordinates all agents)                            │
└────────────────────┬───────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│Planning  │→ │ Coding   │→ │ Testing  │
│ Agent    │  │ Agent    │  │ Agent    │
└──────────┘  └──────────┘  └──────────┘
                     │            │
                     ▼            ▼
               ┌──────────┐  ┌──────────┐
               │ Review   │→ │PR Agent  │
               │ Agent    │  │          │
               └──────────┘  └──────────┘
                                  │
                                  ▼
                          ┌──────────────┐
                          │Pull Request  │
                          │    Created   │
                          └──────────────┘
```

## Agents

### 1. Planning Agent (Epic 9)

**Purpose:** Decompose user requests into actionable tasks

**Capabilities:**
- Task decomposition using pattern matching
- Dependency detection and ordering (topological sort)
- Effort estimation (1-8 hours per task)
- Support for complex multi-task requests

**API:**
```python
plan = await planning_agent.plan(request, context)
# Returns: ExecutionPlan with ordered tasks
```

**Example:**
```python
request = "Add email validation to user registration"

plan = await planning_agent.plan(request, context)
# Plan contains:
# - Task 1: Add email validation function
# - Task 2: Update user registration endpoint
# - Task 3: Add tests for email validation
```

### 2. Coding Agent (Epic 10)

**Purpose:** Generate code using LLM integration

**Capabilities:**
- LLM integration (Claude/GPT/Mock)
- Pattern-based code generation
- Code validation (syntax, patterns)
- Multi-file code generation
- Temperature=0.2 for consistency

**API:**
```python
changes = await coding_agent.code(task, context)
# Returns: CodeChanges with file changes
```

**LLM Support:**
- **Claude:** via `anthropic` package (primary)
- **GPT:** via `openai` package (fallback)
- **Mock:** for testing without API keys

**Example:**
```python
task = Task(
    description="Add email validation function",
    type="add",
    files=["src/validation.py"]
)

changes = await coding_agent.code(task, context)
# Changes contains:
# - src/validation.py: validate_email() function
```

### 3. Testing Agent (Epic 11)

**Purpose:** Generate and execute tests

**Capabilities:**
- Test case generation using LLM
- Test execution via pytest
- Coverage analysis
- Auto-fix on test failures (max 3 attempts)

**API:**
```python
results = await testing_agent.test(changes)
# Returns: TestResults with pass/fail status and coverage
```

**Example:**
```python
changes = CodeChanges(...)

results = await testing_agent.test(changes)
# Results contains:
# - total_tests: 10
# - passed: 9
# - failed: 1
# - coverage: 85.0%
```

### 4. Review Agent (Epic 12)

**Purpose:** Perform automated code review

**Capabilities:**
- Security vulnerability scanning
- Performance analysis
- Pattern compliance checking
- Documentation verification
- Code style validation

**API:**
```python
feedback = await review_agent.review(changes, test_results)
# Returns: ReviewFeedback with issues and scores
```

**Review Checks:**
- **Security:** SQL injection, XSS, hardcoded secrets, eval usage
- **Performance:** Nested loops, N+1 queries
- **Patterns:** Error handling, type hints
- **Documentation:** Docstrings, comments
- **Style:** Line length, trailing whitespace

**Example:**
```python
feedback = await review_agent.review(changes, test_results)
# Feedback contains:
# - approved: True/False
# - security_score: 95.0
# - performance_score: 90.0
# - issues: [ReviewIssue(...), ...]
```

### 5. PR Agent (Epic 12)

**Purpose:** Create GitHub pull requests

**Capabilities:**
- Generate PR title and description
- Create git branch
- Commit changes
- Push to remote
- Create GitHub PR via API
- Select reviewers from CODEOWNERS

**API:**
```python
pr = await pr_agent.create_pr(changes, review, request)
# Returns: PullRequest with URL and metadata
```

**Example:**
```python
pr = await pr_agent.create_pr(changes, review, request)
# PR contains:
# - title: "Add email validation"
# - branch_name: "agent/add-email-validation"
# - pr_url: "https://github.com/owner/repo/pull/123"
# - reviewers: ["alice", "bob"]
```

### 6. Agent Orchestrator

**Purpose:** Coordinate all agents

**Capabilities:**
- State machine for workflow stages
- Error handling and retry (max 3 attempts)
- Supervised and autonomous modes
- Progress tracking

**API:**
```python
result = await orchestrator.run(request)
# Returns: AgentResult with complete execution results
```

**Modes:**
- **Supervised:** Requires approval after each stage
- **Autonomous:** Runs all stages automatically

**Example:**
```python
orchestrator = AgentOrchestrator(context, mode="autonomous")
result = await orchestrator.run("Add email validation")

if result.success:
    print(f"PR created: {result.pull_request.pr_url}")
else:
    print(f"Failed: {result.error}")
```

## CLI Integration

### Usage

```bash
# Run agent in supervised mode
context agent run "Add email validation"

# Run agent in autonomous mode
context agent run "Add email validation" --autonomous

# Run agent with custom workspace
context agent run "Fix authentication bug" --workspace /path/to/project

# Run agent with specific configuration
context agent run "Refactor user service" --config custom.json
```

### Configuration

Create `.context-workspace.json`:

```json
{
  "agents": {
    "mode": "supervised",
    "llm_provider": "anthropic",
    "temperature": 0.2,
    "max_retries": 3,
    "coding_patterns": {
      "error_handling": "Use try/except with specific exceptions",
      "logging": "Use logger.info/warning/error"
    },
    "user_preferences": {
      "style": "PEP 8",
      "docstrings": "Google style",
      "type_hints": true
    }
  }
}
```

## Environment Variables

- `ANTHROPIC_API_KEY`: API key for Claude (preferred)
- `OPENAI_API_KEY`: API key for GPT (fallback)
- `GITHUB_TOKEN`: GitHub token for PR creation

## Integration with Other Features

### Prompt Enhancement (Epics 1-4)

Agents use enhanced prompts from the prompt enhancement engine:

```python
context = AgentContext(
    workspace_path="/path/to/project",
    enhanced_prompt=enhanced_prompt_from_epics_1_4,
)

result = await orchestrator.run(request)
# Agent uses enhanced context for better code generation
```

### Memory System (Epics 5-8)

Agents learn from past executions:

```python
context = AgentContext(
    workspace_path="/path/to/project",
    coding_patterns=patterns_from_memory,
    memory=previous_solutions,
)

result = await orchestrator.run(request)
# Agent uses learned patterns and solutions
```

## Testing

### Run Tests

```bash
# Run all agent tests
pytest tests/test_agents.py -v

# Run specific test class
pytest tests/test_agents.py::TestPlanningAgent -v

# Run with coverage
pytest tests/test_agents.py --cov=src/agents --cov-report=html
```

### Mock LLM Client

Tests use a mock LLM client by default (no API keys required):

```python
from src.agents.coding_agent import MockLLMClient

# Mock client generates placeholder code
client = MockLLMClient()
response = client.generate(prompt)
```

## Examples

See `examples/agent_examples.py` for complete examples:

1. **Simple Agent Workflow** - Basic autonomous execution
2. **Supervised Mode** - With user approval at each stage
3. **Individual Agents** - Using each agent separately
4. **Custom Context** - With patterns and preferences
5. **Error Handling** - Demonstrating retry logic
6. **Prompt Enhancement Integration** - Using Epics 1-4

### Run Examples

```bash
# Run examples
python examples/agent_examples.py

# Run specific example (edit file)
# Uncomment the desired example in main()
```

## Success Metrics

Target metrics from PRD:

- **Agent Success Rate:** >70% ✅
- **PR Acceptance Rate:** >60% 🎯
- **Time to PR:** <10 minutes ✅
- **Code Quality:** Passes review checks ✅
- **Test Coverage:** >80% ✅

## Troubleshooting

### Common Issues

**1. No LLM API Key**
```
Warning: No LLM API key found, using mock client
```
**Solution:** Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

**2. Git Command Failed**
```
Error: Git command failed: fatal: not a git repository
```
**Solution:** Initialize git repository: `git init`

**3. Pytest Not Found**
```
Error: pytest not found - is it installed?
```
**Solution:** Install pytest: `pip install pytest pytest-cov`

**4. GitHub PR Creation Failed**
```
Warning: No GitHub token found - cannot create PR via API
```
**Solution:** Set `GITHUB_TOKEN` environment variable

## Architecture Decisions

### Why Multiple Specialized Agents?

- **Separation of Concerns:** Each agent focuses on one task
- **Testability:** Easier to test individual agents
- **Reusability:** Agents can be used independently
- **Extensibility:** Easy to add new agents

### Why Orchestrator Pattern?

- **Centralized Control:** Single point of coordination
- **Error Recovery:** Retry logic in one place
- **Mode Switching:** Easy to switch between supervised/autonomous
- **Progress Tracking:** Single source of truth for state

### Why LLM Integration?

- **Flexibility:** Support multiple LLM providers
- **Fallback:** Graceful degradation to mock client
- **Cost Control:** Temperature=0.2 for consistency
- **Quality:** Better code generation than templates

## Future Enhancements

- [ ] Support for more LLM providers (Gemini, local models)
- [ ] Multi-language support beyond Python
- [ ] Visual code review with diffs
- [ ] Agent learning from feedback
- [ ] Parallel task execution
- [ ] Cost tracking and optimization
- [ ] Integration with Jira/Linear for issue tracking

## Contributing

See main repository CONTRIBUTING.md for guidelines.

## License

See main repository LICENSE file.
