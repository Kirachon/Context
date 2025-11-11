"""
Coding Agent - Epic 10

Generates code using LLM integration with pattern-based validation.
"""

import os
import ast
import asyncio
from typing import List, Optional, Dict, Any

from .base_agent import BaseAgent
from .models import Task, CodeChanges, FileChange, AgentContext


class CodingAgent(BaseAgent):
    """
    Coding Agent that generates code using LLM APIs.

    Capabilities:
    - LLM integration (Claude/GPT)
    - Pattern-based code generation
    - Code validation (syntax, patterns)
    - Multi-file code generation
    """

    # Temperature for code generation (lower = more consistent)
    TEMPERATURE = 0.2

    # Max tokens for code generation
    MAX_TOKENS = 4000

    def __init__(self, context: AgentContext):
        """Initialize the Coding Agent"""
        super().__init__(context)
        self.llm_client = self._initialize_llm()

    def _initialize_llm(self):
        """
        Initialize LLM client based on available API keys.

        Tries in order:
        1. Anthropic (Claude)
        2. OpenAI (GPT)
        3. Mock client (for testing)

        Returns:
            LLM client instance
        """
        # Try Anthropic Claude first
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                from anthropic import Anthropic
                self.log_info("Using Anthropic Claude for code generation")
                return Anthropic(api_key=anthropic_key)
            except ImportError:
                self.log_warning("anthropic package not installed")

        # Try OpenAI GPT
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI
                self.log_info("Using OpenAI GPT for code generation")
                return OpenAI(api_key=openai_key)
            except ImportError:
                self.log_warning("openai package not installed")

        # Fallback to mock client
        self.log_warning("No LLM API key found, using mock client")
        return MockLLMClient()

    async def code(self, task: Task, context: AgentContext) -> CodeChanges:
        """
        Generate code for a task.

        Args:
            task: Task to implement
            context: Agent execution context

        Returns:
            CodeChanges with generated code
        """
        self.log_info(f"Generating code for task: {task.description}")

        # Step 1: Build enhanced prompt using context
        prompt = await self._build_code_generation_prompt(task, context)

        # Step 2: Generate code using LLM
        code_response = await self._generate_code(prompt)

        # Step 3: Parse response into file changes
        changes = self._parse_code_response(code_response, task)

        # Step 4: Validate generated code
        validation_errors = self._validate_code(changes)

        # Step 5: Create CodeChanges object
        code_changes = CodeChanges(
            task_id=task.id,
            changes=changes,
            summary=task.description,
            language=context.language,
            validation_errors=validation_errors,
            metadata={
                "model": self._get_model_name(),
                "temperature": self.TEMPERATURE,
            }
        )

        self.log_info(f"Generated {len(changes)} file changes")
        if validation_errors:
            self.log_warning(f"Validation errors: {validation_errors}")

        return code_changes

    async def execute(self, task: Task) -> CodeChanges:
        """Execute code generation for a task"""
        return await self.code(task, self.context)

    async def _build_code_generation_prompt(self, task: Task, context: AgentContext) -> str:
        """
        Build enhanced prompt for code generation.

        Uses context from prompt enhancement engine and memory system.

        Args:
            task: Task to implement
            context: Agent execution context

        Returns:
            Enhanced prompt string
        """
        prompt_parts = []

        # Add task description
        prompt_parts.append(f"# TASK\n{task.description}\n")

        # Add project context
        if context.language:
            prompt_parts.append(f"# LANGUAGE\n{context.language}\n")

        if context.framework:
            prompt_parts.append(f"# FRAMEWORK\n{context.framework}\n")

        # Add coding patterns from memory
        if context.coding_patterns:
            prompt_parts.append("# CODING PATTERNS (Follow these patterns)\n")
            for pattern_name, pattern_code in context.coding_patterns.items():
                prompt_parts.append(f"## {pattern_name}\n```\n{pattern_code}\n```\n")

        # Add user preferences
        if context.user_preferences:
            prompt_parts.append("# USER PREFERENCES\n")
            for pref_key, pref_value in context.user_preferences.items():
                prompt_parts.append(f"- {pref_key}: {pref_value}\n")

        # Add enhanced context from prompt enhancement engine
        if context.enhanced_prompt:
            prompt_parts.append(f"# ADDITIONAL CONTEXT\n{context.enhanced_prompt}\n")

        # Add file context
        if task.files:
            prompt_parts.append(f"# FILES TO MODIFY\n")
            for file_path in task.files:
                prompt_parts.append(f"- {file_path}\n")

        # Add instructions
        prompt_parts.append("""
# INSTRUCTIONS
Generate complete, production-ready code following these guidelines:
1. Follow the coding patterns provided above
2. Include proper error handling
3. Add comprehensive docstrings
4. Use type hints (if applicable)
5. Follow PEP 8 / language style guides
6. Make code maintainable and readable
7. Include inline comments for complex logic

# OUTPUT FORMAT
Provide the code in the following format:

```filename: path/to/file.ext
// Code content here
```

For multiple files, repeat the format for each file.
""")

        return "\n".join(prompt_parts)

    async def _generate_code(self, prompt: str) -> str:
        """
        Generate code using LLM.

        Args:
            prompt: Code generation prompt

        Returns:
            Generated code response
        """
        try:
            if hasattr(self.llm_client, "messages"):
                # Anthropic Claude
                response = await asyncio.to_thread(
                    self.llm_client.messages.create,
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                return response.content[0].text

            elif hasattr(self.llm_client, "chat"):
                # OpenAI GPT
                response = await asyncio.to_thread(
                    self.llm_client.chat.completions.create,
                    model="gpt-4",
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                return response.choices[0].message.content

            else:
                # Mock client
                return self.llm_client.generate(prompt)

        except Exception as e:
            self.log_error(f"Error generating code: {e}", exc_info=True)
            return self._generate_fallback_code(prompt)

    def _parse_code_response(self, response: str, task: Task) -> List[FileChange]:
        """
        Parse LLM response into file changes.

        Expects format:
        ```filename: path/to/file.py
        code content
        ```

        Args:
            response: LLM response
            task: Original task

        Returns:
            List of FileChange objects
        """
        changes = []
        current_file = None
        current_content = []

        lines = response.split("\n")
        in_code_block = False

        for line in lines:
            # Check for file marker
            if line.startswith("```filename:"):
                # Save previous file if exists
                if current_file and current_content:
                    changes.append(FileChange(
                        path=current_file,
                        new_content="\n".join(current_content),
                        operation=task.type if task.type in ["create", "update", "delete"] else "update"
                    ))
                    current_content = []

                # Extract filename
                current_file = line.split("```filename:", 1)[1].strip()
                in_code_block = True

            elif line.strip() == "```" and in_code_block:
                # End of code block
                in_code_block = False

            elif in_code_block and current_file:
                # Accumulate code content
                current_content.append(line)

        # Save last file
        if current_file and current_content:
            changes.append(FileChange(
                path=current_file,
                new_content="\n".join(current_content),
                operation=task.type if task.type in ["create", "update", "delete"] else "update"
            ))

        # If no files parsed, create a default file
        if not changes and task.files:
            changes.append(FileChange(
                path=task.files[0] if task.files else "output.py",
                new_content=response,
                operation="update"
            ))

        return changes

    def _validate_code(self, changes: List[FileChange]) -> List[str]:
        """
        Validate generated code.

        Checks:
        - Syntax validity (for Python)
        - Basic code patterns
        - File path validity

        Args:
            changes: List of file changes

        Returns:
            List of validation error messages
        """
        errors = []

        for change in changes:
            # Validate file path
            if not change.path or change.path.strip() == "":
                errors.append(f"Invalid file path: {change.path}")
                continue

            # Validate Python syntax
            if change.path.endswith(".py"):
                try:
                    ast.parse(change.new_content)
                except SyntaxError as e:
                    errors.append(f"Syntax error in {change.path}: {e}")

            # Check for empty files
            if not change.new_content.strip():
                errors.append(f"Empty file content: {change.path}")

            # Check for obvious issues
            if "TODO" in change.new_content.upper() and "# TODO" not in change.new_content:
                errors.append(f"Contains TODO markers: {change.path}")

        return errors

    def _generate_fallback_code(self, prompt: str) -> str:
        """
        Generate fallback code when LLM fails.

        Creates a basic stub based on the prompt.

        Args:
            prompt: Original prompt

        Returns:
            Fallback code
        """
        return '''"""
Fallback code stub - LLM generation failed.

Task: Generated from prompt
"""

# TODO: Implement functionality
pass
'''

    def _get_model_name(self) -> str:
        """Get the name of the current LLM model"""
        if hasattr(self.llm_client, "messages"):
            return "claude-3-5-sonnet"
        elif hasattr(self.llm_client, "chat"):
            return "gpt-4"
        else:
            return "mock"


class MockLLMClient:
    """Mock LLM client for testing without API keys"""

    def generate(self, prompt: str) -> str:
        """Generate mock code response"""
        # Check if this is a test generation request
        if "pytest" in prompt.lower() or "test" in prompt.lower():
            return '''```filename: tests/test_generated.py
"""
Mock generated test code for testing.
"""

import pytest


def test_generated_function():
    """Test the generated function"""
    # This is mock test code generated by the MockLLMClient
    assert True


class TestGeneratedClass:
    """Test class for generated code"""

    def test_init(self):
        """Test initialization"""
        # Mock test implementation
        assert True

    def test_process(self):
        """Test process method"""
        # Mock test implementation
        assert True
```
'''

        # Default: generate regular code
        return '''```filename: src/generated.py
"""
Mock generated code for testing.
"""

def generated_function():
    """
    This is mock code generated by the MockLLMClient.

    In production, this would be replaced with actual LLM-generated code.
    """
    # TODO: Implement actual functionality
    pass


class GeneratedClass:
    """Mock generated class"""

    def __init__(self):
        """Initialize the generated class"""
        self.value = None

    def process(self):
        """Process some data"""
        return self.value
```
'''
