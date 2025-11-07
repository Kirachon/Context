"""
Context-aware prompt tools for MCP integration
"""

import logging
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_context_aware_tools(mcp: FastMCP):
    """
    Register context-aware prompt tools with the MCP server

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def generate_contextual_prompt(
        query: str,
        context: Optional[Dict[str, Any]] = None,
        prompt_type: str = "search"
    ) -> Dict[str, Any]:
        """
        Generate a context-aware prompt based on the query and context

        Args:
            query: User query or request
            context: Optional context information
            prompt_type: Type of prompt to generate (search, analysis, etc.)

        Returns:
            Dictionary containing the generated prompt and metadata
        """
        try:
            logger.info(f"Generating contextual prompt for query: {query[:100]}...")

            # Base prompt templates
            templates = {
                "search": "Based on the following context, help me understand: {query}\n\nContext: {context}",
                "analysis": "Analyze the following information in context: {query}\n\nContext: {context}",
                "explanation": "Explain this concept with relevant context: {query}\n\nContext: {context}",
                "comparison": "Compare and contrast the following: {query}\n\nContext: {context}",
                "recommendation": "Provide recommendations based on: {query}\n\nContext: {context}"
            }

            # Select appropriate template
            template = templates.get(prompt_type, templates["search"])

            # Format context
            context_str = ""
            if context:
                if isinstance(context, dict):
                    context_parts = []
                    for key, value in context.items():
                        context_parts.append(f"{key}: {value}")
                    context_str = "\n".join(context_parts)
                else:
                    context_str = str(context)

            # Generate prompt
            prompt = template.format(query=query, context=context_str)

            # Add additional context-aware enhancements
            if context and len(str(context)) > 100:
                prompt += "\n\nNote: This query has substantial context available. Consider all relevant information when responding."

            return {
                "prompt": prompt,
                "prompt_type": prompt_type,
                "has_context": bool(context),
                "context_length": len(str(context)) if context else 0,
                "query_length": len(query)
            }

        except Exception as e:
            logger.error(f"Error generating contextual prompt: {e}")
            return {
                "error": str(e),
                "prompt": f"Help me with: {query}",
                "prompt_type": prompt_type,
                "has_context": False
            }

    @mcp.tool()
    async def extract_context_keywords(
        text: str,
        max_keywords: int = 10
    ) -> Dict[str, Any]:
        """
        Extract relevant keywords from text for context understanding

        Args:
            text: Text to analyze
            max_keywords: Maximum number of keywords to extract

        Returns:
            Dictionary containing extracted keywords and metadata
        """
        try:
            logger.info(f"Extracting keywords from text ({len(text)} chars)")

            # Simple keyword extraction (in a real implementation, you might use NLP libraries)
            words = text.lower().split()

            # Filter out common stop words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
            }

            # Filter words and count frequency
            filtered_words = [
                word.strip('.,!?;:()[]{}"\'')
                for word in words
                if word.strip('.,!?;:()[]{}"\'')
                and word.strip('.,!?;:()[]{}"\'') not in stop_words
                and len(word.strip('.,!?;:()[]{}"\'')) > 2
            ]

            # Count word frequency
            word_count = {}
            for word in filtered_words:
                word_count[word] = word_count.get(word, 0) + 1

            # Sort by frequency and limit
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            keywords = [word for word, count in sorted_words[:max_keywords]]

            return {
                "keywords": keywords,
                "count": len(keywords),
                "text_length": len(text),
                "unique_words": len(set(filtered_words))
            }

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return {
                "error": str(e),
                "keywords": [],
                "count": 0
            }

    @mcp.tool()
    async def optimize_prompt_for_context(
        prompt: str,
        context_type: str = "general",
        response_format: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Optimize a prompt based on context type and desired response format

        Args:
            prompt: Original prompt to optimize
            context_type: Type of context (code, documentation, analysis, etc.)
            response_format: Desired response format (detailed, concise, technical, etc.)

        Returns:
            Dictionary containing optimized prompt and metadata
        """
        try:
            logger.info(f"Optimizing prompt for context: {context_type}")

            # Context-specific optimizations
            context_instructions = {
                "code": "Provide clear, executable code examples with comments. Include any imports or setup needed.",
                "documentation": "Structure the response with clear headings, bullet points, and practical examples.",
                "analysis": "Provide a thorough analysis with supporting evidence and clear reasoning.",
                "troubleshooting": "Include step-by-step diagnostic procedures and potential solutions.",
                "learning": "Explain concepts progressively with analogies and practical applications.",
                "general": "Provide a comprehensive yet accessible response with relevant examples."
            }

            # Response format instructions
            format_instructions = {
                "detailed": "Provide comprehensive coverage with in-depth explanations and examples.",
                "concise": "Be brief and to the point while maintaining accuracy and clarity.",
                "technical": "Use precise terminology and include technical specifications when relevant.",
                "practical": "Focus on actionable advice and real-world applications.",
                "educational": "Structure the response for learning with clear explanations and examples."
            }

            # Get appropriate instructions
            context_instruction = context_instructions.get(context_type, context_instructions["general"])
            format_instruction = format_instructions.get(response_format, "Provide a clear and helpful response.")

            # Build optimized prompt
            optimized_prompt = f"""{prompt}

Context Guidelines: {context_instruction}
Response Style: {format_instruction}"""

            return {
                "optimized_prompt": optimized_prompt,
                "original_prompt": prompt,
                "context_type": context_type,
                "response_format": response_format,
                "context_instruction": context_instruction,
                "format_instruction": format_instruction
            }

        except Exception as e:
            logger.error(f"Error optimizing prompt: {e}")
            return {
                "error": str(e),
                "optimized_prompt": prompt,
                "original_prompt": prompt,
                "context_type": context_type,
                "response_format": response_format
            }

    logger.info("Registered context-aware prompt tools")