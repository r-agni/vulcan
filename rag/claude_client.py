"""
Claude API client wrapper with tool calling support for RAG system
"""

from anthropic import Anthropic
from typing import List, Dict, Any, Optional, Callable
import json
import os
from dotenv import load_dotenv

load_dotenv()


class ClaudeClient:
    """Wrapper for Claude API with tool calling support"""

    def __init__(self, api_key: str = None):
        """
        Initialize Claude client

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

        # Tool registry for function calling
        self.tools: Dict[str, Callable] = {}
        self.tool_definitions: List[Dict[str, Any]] = []

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        function: Callable
    ):
        """
        Register a tool for Claude to call

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for tool inputs
            function: Python function to execute when tool is called
        """
        self.tools[name] = function
        self.tool_definitions.append({
            "name": name,
            "description": description,
            "input_schema": input_schema
        })

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        system: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        auto_execute_tools: bool = True,
        max_tool_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Generate response with tool calling support

        Args:
            messages: Conversation messages [{"role": "user", "content": "..."}]
            system: System prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            auto_execute_tools: Automatically execute tools and continue conversation
            max_tool_iterations: Maximum number of tool calls to make

        Returns:
            Dict with response text, tool_calls, and metadata
        """
        iteration = 0
        tool_results = []

        while iteration < max_tool_iterations:
            # Make API call
            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            if system:
                kwargs["system"] = system

            if self.tool_definitions:
                kwargs["tools"] = self.tool_definitions

            response = self.client.messages.create(**kwargs)

            # Check if response has tool calls
            has_tool_use = any(block.type == "tool_use" for block in response.content)

            if not has_tool_use or not auto_execute_tools:
                # No tool calls or auto-execution disabled, return response
                text_content = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                return {
                    "text": text_content,
                    "tool_calls": tool_results,
                    "stop_reason": response.stop_reason,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    }
                }

            # Execute tools
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results_content = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_use_id = block.id

                    # Execute tool
                    if tool_name in self.tools:
                        try:
                            result = self.tools[tool_name](**tool_input)
                            tool_result = {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": str(result)
                            }
                            tool_results.append({
                                "tool": tool_name,
                                "input": tool_input,
                                "result": result
                            })
                        except Exception as e:
                            tool_result = {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": f"Error executing tool: {str(e)}",
                                "is_error": True
                            }
                            tool_results.append({
                                "tool": tool_name,
                                "input": tool_input,
                                "error": str(e)
                            })
                    else:
                        tool_result = {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"Tool {tool_name} not found",
                            "is_error": True
                        }

                    tool_results_content.append(tool_result)

            # Add tool results to conversation
            messages.append({
                "role": "user",
                "content": tool_results_content
            })

            iteration += 1

        # Max iterations reached
        return {
            "text": "Maximum tool call iterations reached",
            "tool_calls": tool_results,
            "stop_reason": "max_iterations",
            "usage": {}
        }

    def generate(
        self,
        prompt: str,
        system: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        Simple text generation without tool calling

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        # Extract text from response
        text_content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )

        return text_content

    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine search strategy

        Args:
            query: User's question

        Returns:
            Dict with search_metadata (bool), search_analysis (bool), needs_visualization (bool)
        """
        system = """You are a query analyzer for a retail analytics RAG system.
Analyze the user's query and determine:
1. Should we search metadata (structured data like occupancy, dwell times, zones)?
2. Should we search verbal analysis (Gemini's textual interpretations)?
3. Does the user want a visualization (chart, graph, diagram)?

Return JSON with: {"search_metadata": bool, "search_analysis": bool, "needs_visualization": bool, "visualization_type": string or null}

Visualization types: "line", "bar", "pie", "heatmap", "scatter", "timeline"

Default to searching metadata first. Only search analysis if the query explicitly asks for:
- "analysis", "insights", "interpretation", "what does this mean", "explain"
- Or if it's a complex qualitative question

Detect visualization requests from keywords like:
- "chart", "graph", "plot", "show me", "visualize", "draw", "diagram"
"""

        prompt = f"Query: {query}"

        response = self.generate(prompt, system=system, max_tokens=200, temperature=0.3)

        try:
            # Extract JSON from response
            # Claude might wrap JSON in markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)
        except Exception as e:
            print(f"Error parsing query intent: {e}")
            # Default fallback
            return {
                "search_metadata": True,
                "search_analysis": False,
                "needs_visualization": False,
                "visualization_type": None
            }
