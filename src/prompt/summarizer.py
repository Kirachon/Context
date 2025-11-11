"""
Hierarchical Summarization Engine - Epic 3 (Part 2)

Compresses context to fit token budget using 4-tier compression:

Tier 1 (Top 20%): Include verbatim (no compression)
Tier 2 (20-50%): Summarize to 33% (medium compression)
Tier 3 (50-80%): One-line summary (high compression)
Tier 4 (Bottom 20%): Drop completely

Uses:
- Extractive summarization for code (keep important lines)
- Abstractive summarization for docs (LLM-based)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

# Lazy load tiktoken for token counting
_tiktoken_encoding = None


def get_tiktoken_encoding():
    """Lazy load tiktoken encoding"""
    global _tiktoken_encoding
    if _tiktoken_encoding is None:
        try:
            import tiktoken
            _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            # Fallback: estimate tokens as words / 0.75
            _tiktoken_encoding = None
    return _tiktoken_encoding


@dataclass
class SummarizedItem:
    """Summarized context item"""
    original: any  # Original ContextItem
    summary: Optional[str] = None  # Summarized content (None = use original)
    compression: str = 'none'  # 'none', 'medium', 'high'
    tokens: int = 0


@dataclass
class SummarizedContext:
    """Context after summarization"""
    items: List[SummarizedItem] = field(default_factory=list)
    total_tokens: int = 0

    def add(self, original, compression: str = 'none', summary: Optional[str] = None):
        """Add summarized item"""
        content = summary if summary else str(original.content)
        tokens = count_tokens(content)

        self.items.append(SummarizedItem(
            original=original,
            summary=summary,
            compression=compression,
            tokens=tokens
        ))
        self.total_tokens += tokens

    def get_by_type(self, item_type: str) -> List[SummarizedItem]:
        """Get items by type"""
        return [
            item for item in self.items
            if item.original.type == item_type
        ]

    def get_by_source(self, source: str) -> List[SummarizedItem]:
        """Get items by source"""
        return [
            item for item in self.items
            if item.original.source == source
        ]


def count_tokens(text: str) -> int:
    """Count tokens in text"""
    encoding = get_tiktoken_encoding()

    if encoding:
        try:
            return len(encoding.encode(text))
        except Exception:
            pass

    # Fallback: estimate as words / 0.75
    words = len(text.split())
    return int(words / 0.75)


class ExtractiveSummarizer:
    """
    Extractive summarization for code

    Keeps important lines based on:
    - Function/class definitions
    - Docstrings
    - Comments
    - Key logic (if/else, loops, returns)
    """

    def summarize(self, content: str, ratio: float = 0.33) -> str:
        """
        Summarize code by extracting important lines

        Args:
            content: Code content
            ratio: Target compression ratio (e.g., 0.33 = compress to 33%)

        Returns:
            Summarized code
        """
        lines = content.split('\n')
        total_lines = len(lines)
        target_lines = max(1, int(total_lines * ratio))

        # Score each line by importance
        scored_lines = []
        for i, line in enumerate(lines):
            score = self._score_line(line, i, lines)
            scored_lines.append((score, i, line))

        # Sort by score and take top N lines
        scored_lines.sort(reverse=True)
        selected_lines = scored_lines[:target_lines]

        # Re-sort by original line number
        selected_lines.sort(key=lambda x: x[1])

        # Build summarized code with ellipsis for gaps
        result = []
        last_idx = -1
        for score, idx, line in selected_lines:
            # Add ellipsis if we skipped lines
            if idx > last_idx + 1:
                result.append('    # ...')

            result.append(line)
            last_idx = idx

        return '\n'.join(result)

    def _score_line(self, line: str, idx: int, all_lines: List[str]) -> float:
        """Score a line's importance"""
        score = 0.0
        stripped = line.strip()

        # Function/class definitions are very important
        if re.match(r'^(def|class|async def)\s+', stripped):
            score += 10.0

        # Docstrings are important
        if '"""' in stripped or "'''" in stripped:
            score += 8.0

        # Comments provide context
        if stripped.startswith('#'):
            score += 5.0

        # Control flow is important
        if re.match(r'^(if|elif|else|for|while|try|except|finally|with|return)\s', stripped):
            score += 7.0

        # Imports are moderately important
        if re.match(r'^(import|from)\s+', stripped):
            score += 4.0

        # Decorators are important
        if stripped.startswith('@'):
            score += 6.0

        # Empty lines get low score
        if not stripped:
            score += 0.1

        # First and last few lines get bonus
        if idx < 5 or idx >= len(all_lines) - 5:
            score += 2.0

        return score


class AbstractiveSummarizer:
    """
    Abstractive summarization for documentation using LLM

    Uses LLM to generate concise summaries of documentation.
    Falls back to extractive if LLM unavailable.
    """

    def __init__(self):
        """Initialize abstractive summarizer"""
        self.extractive = ExtractiveSummarizer()
        # LLM client would be initialized here
        self.llm_client = None

    async def summarize(self, content: str, max_length: int) -> str:
        """
        Summarize documentation using LLM

        Args:
            content: Documentation content
            max_length: Maximum length of summary

        Returns:
            Summarized documentation
        """
        # If LLM available, use it
        if self.llm_client:
            try:
                return await self._llm_summarize(content, max_length)
            except Exception:
                pass

        # Fallback to extractive summarization
        return self._extractive_fallback(content, max_length)

    async def _llm_summarize(self, content: str, max_length: int) -> str:
        """Summarize using LLM (stub)"""
        # TODO: Implement LLM-based summarization
        # This would call OpenAI/Anthropic API to generate summary
        # For now, fall back to extractive
        return self._extractive_fallback(content, max_length)

    def _extractive_fallback(self, content: str, max_length: int) -> str:
        """Fallback to extractive summarization"""
        # Calculate ratio
        current_length = len(content)
        ratio = max_length / current_length if current_length > 0 else 1.0
        ratio = min(1.0, max(0.1, ratio))

        # Use extractive summarizer
        lines = content.split('\n')

        # Simple extractive: take first and last parts
        if ratio < 0.5:
            # High compression: first 1/3 and last 1/3
            take = max(1, int(len(lines) * ratio / 2))
            result = lines[:take] + ['...'] + lines[-take:]
            return '\n'.join(result)
        else:
            # Lower compression: first 2/3
            take = int(len(lines) * ratio)
            return '\n'.join(lines[:take])


class HierarchicalSummarizer:
    """
    Apply hierarchical summarization to fit token budget

    Strategy:
    - Tier 1 (Top 20%): Include verbatim
    - Tier 2 (20-50%): Summarize to 33%
    - Tier 3 (50-80%): One-line summary
    - Tier 4 (Bottom 20%): Drop
    """

    def __init__(self):
        """Initialize hierarchical summarizer"""
        self.extractive_summarizer = ExtractiveSummarizer()
        self.abstractive_summarizer = AbstractiveSummarizer()

    async def summarize(self, ranked_context, token_budget: int) -> SummarizedContext:
        """
        Apply tiered summarization to fit token budget

        Args:
            ranked_context: RankedContext with scored chunks
            token_budget: Maximum tokens allowed

        Returns:
            SummarizedContext with compressed content
        """
        total_chunks = len(ranked_context.chunks)
        tier1_count = int(total_chunks * 0.2)
        tier2_count = int(total_chunks * 0.3)
        tier3_count = int(total_chunks * 0.3)

        summarized = SummarizedContext()
        current_tokens = 0

        # Tier 1: Critical context (verbatim)
        for scored_chunk in ranked_context.chunks[:tier1_count]:
            item = scored_chunk.chunk
            content = str(item.content)
            tokens = count_tokens(content)

            # Check if we'd exceed budget
            if current_tokens + tokens > token_budget:
                # Try compressing instead of dropping
                summary = self._compress_content(content, is_code=self._is_code(item))
                tokens = count_tokens(summary)

                if current_tokens + tokens > token_budget:
                    break  # Can't fit even compressed version

                summarized.add(item, compression='medium', summary=summary)
                current_tokens += tokens
            else:
                summarized.add(item, compression='none')
                current_tokens += tokens

        # Tier 2: Important context (summarized to 33%)
        tier2_start = tier1_count
        tier2_end = tier1_count + tier2_count

        for scored_chunk in ranked_context.chunks[tier2_start:tier2_end]:
            item = scored_chunk.chunk

            if current_tokens >= token_budget:
                break

            # Summarize based on content type
            is_code = self._is_code(item)
            content = str(item.content)

            if is_code:
                summary = self.extractive_summarizer.summarize(
                    content,
                    ratio=0.33
                )
            else:
                target_length = len(content) // 3
                summary = await self.abstractive_summarizer.summarize(
                    content,
                    max_length=target_length
                )

            tokens = count_tokens(summary)

            if current_tokens + tokens > token_budget:
                # Try even higher compression
                summary = await self._generate_one_liner(item)
                tokens = count_tokens(summary)

                if current_tokens + tokens > token_budget:
                    break

                summarized.add(item, compression='high', summary=summary)
                current_tokens += tokens
            else:
                summarized.add(item, compression='medium', summary=summary)
                current_tokens += tokens

        # Tier 3: Supporting context (one-line)
        tier3_start = tier2_end
        tier3_end = tier2_end + tier3_count

        for scored_chunk in ranked_context.chunks[tier3_start:tier3_end]:
            if current_tokens >= token_budget:
                break

            item = scored_chunk.chunk
            one_liner = await self._generate_one_liner(item)
            tokens = count_tokens(one_liner)

            if current_tokens + tokens > token_budget:
                break

            summarized.add(item, compression='high', summary=one_liner)
            current_tokens += tokens

        # Tier 4: Drop (not included)

        return summarized

    def _is_code(self, item) -> bool:
        """Check if item contains code"""
        code_types = {
            'file', 'dependency', 'reverse_dependency',
            'test', 'search_result'
        }
        return item.type in code_types

    def _compress_content(self, content: str, is_code: bool) -> str:
        """Emergency compression when nearing budget"""
        if is_code:
            # For code, use extractive with aggressive ratio
            return self.extractive_summarizer.summarize(content, ratio=0.2)
        else:
            # For docs, take first half
            lines = content.split('\n')
            return '\n'.join(lines[:len(lines)//2])

    async def _generate_one_liner(self, item) -> str:
        """Generate one-line summary of item"""
        # Format: "Type: path/file.ext (priority: X.X)"
        item_type = item.type
        path = item.metadata.get('path', 'unknown')
        priority = item.priority

        # Get first line of content
        content = str(item.content)
        first_line = content.split('\n')[0][:100]

        return f"{item_type}: {path} - {first_line}"
