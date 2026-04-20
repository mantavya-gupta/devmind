"""
react_agent.py — ReAct agent loop for DevMind
The core intelligence: Thought → Action → Observation → repeat
"""

import os
import re
import json
from groq import Groq
from .prompts import SYSTEM_PROMPT, PLAN_PROMPT

MODEL = "llama-3.3-70b-versatile"
MAX_STEPS = 15
MAX_RETRIES = 3


class AgentStep:
    def __init__(self, step_num, thought="", action="", action_input="", observation=""):
        self.step_num = step_num
        self.thought = thought
        self.action = action
        self.action_input = action_input
        self.observation = observation

    def __str__(self):
        return (
            f"Step {self.step_num}:\n"
            f"  THOUGHT: {self.thought[:100]}\n"
            f"  ACTION: {self.action}({self.action_input[:50]})\n"
            f"  OBSERVATION: {self.observation[:100]}"
        )


class DevMindAgent:
    def __init__(self, tool_registry, codebase_intelligence):
        self.tools = tool_registry
        self.ci = codebase_intelligence
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.steps = []
        self.messages = []

    def _call_llm(self, messages: list) -> str:
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1500,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"[agent] LLM call failed: {e}. Retrying...")
                else:
                    raise

    def _parse_action(self, response: str) -> tuple:
        """Parse agent response into thought, action, input, is_final."""
        if "FINAL_ANSWER:" in response:
            final = response.split("FINAL_ANSWER:")[-1].strip()
            thought = ""
            if "THOUGHT:" in response:
                thought = response.split("THOUGHT:")[1].split("FINAL_ANSWER:")[0].strip()
            return thought, "FINAL_ANSWER", final, True

        thought = ""
        if "THOUGHT:" in response:
            m = re.search(r"THOUGHT:\s*(.+?)(?=ACTION:|FINAL_ANSWER:|$)", response, re.DOTALL)
            if m:
                thought = m.group(1).strip()

        action = ""
        if "ACTION:" in response:
            m = re.search(r"ACTION:\s*(\w+)", response)
            if m:
                action = m.group(1).strip()

        action_input = ""
        if "INPUT:" in response:
            m = re.search(r"INPUT:\s*(.+?)(?=THOUGHT:|ACTION:|FINAL_ANSWER:|$)", response, re.DOTALL)
            if m:
                action_input = m.group(1).strip()

        return thought, action, action_input, False

    def _execute_tool(self, action: str, action_input: str) -> str:
        if not action:
            return "No action specified."

        action_input = action_input.strip()
        kwargs = {}

        if action_input.startswith("{"):
            try:
                kwargs = json.loads(action_input)
            except json.JSONDecodeError:
                pass

        if not kwargs:
            param_map = {
                "read_file": "relative_path",
                "list_directory": "relative_dir",
                "run_command": "command",
                "check_syntax": "file_path",
                "search_code": "query",
                "grep": "pattern",
                "run_tests": "test_path",
            }
            if action in param_map and param_map[action]:
                kwargs = {param_map[action]: action_input}
            elif action == "write_file":
                if "\n---\n" in action_input:
                    parts = action_input.split("\n---\n", 1)
                    kwargs = {"relative_path": parts[0].strip(), "content": parts[1]}
                else:
                    return "write_file requires format: 'filepath\n---\ncontent'"
            elif action == "apply_patch":
                return "apply_patch requires JSON input."
            else:
                kwargs = {"query": action_input}

        result = self.tools.call(action, **kwargs)

        if isinstance(result, dict):
            if not result.get("success", True):
                return f"ERROR: {result.get('error', 'Unknown error')}"

            if action == "read_file" and result.get("success"):
                content = result.get("content", "")
                lines = content.splitlines()
                if len(lines) > 50:
                    preview = "\n".join(lines[:25]) + f"\n... ({len(lines)-35} lines hidden) ...\n" + "\n".join(lines[-10:])
                    return f"File: {result['file_path']} ({result['line_count']} lines)\n{preview}"
                return f"File: {result['file_path']} ({result['line_count']} lines)\n{content}"

            elif action == "search_code" and result.get("success"):
                out = [f"Search results for '{result.get('query', '')}':"]
                for r in result.get("semantic_results", [])[:3]:
                    out.append(f"  [{r['score']}] {r['kind']} '{r['name']}' in {r['file_path']}")
                    out.append(f"    {r['code'][:200]}...")
                return "\n".join(out)

            elif action in ("run_command", "run_tests"):
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                rc = result.get("returncode", -1)
                out = f"Exit code: {rc}\n"
                if stdout:
                    out += f"STDOUT:\n{stdout[-2000:]}\n"
                if stderr and not result.get("success"):
                    out += f"STDERR:\n{stderr[-500:]}\n"
                return out

            elif action == "write_file":
                return f"Successfully wrote {result.get('file_path')} ({result.get('lines_written')} lines)"

            elif action == "list_directory":
                items = result.get("items", [])
                out = [f"Directory ({result.get('count')} items):"]
                for item in items[:25]:
                    out.append(f"  {item['type']} {item['name']}")
                return "\n".join(out)

        return str(result)

    def _make_plan(self, task: str) -> str:
        plan_prompt = PLAN_PROMPT.format(
            repo_name=self.ci.repo.full_name,
            task=task,
        )
        response = self._call_llm([{"role": "user", "content": plan_prompt}])
        return response

    def run(self, task: str, verbose: bool = True) -> dict:
        print(f"\n{'='*55}")
        print(f"DevMind Agent Starting")
        print(f"Task: {task[:100]}")
        print(f"{'='*55}\n")

        print("[agent] Generating plan...")
        plan = self._make_plan(task)
        print(f"\nPlan:\n{plan}\n")

        repo_context = self.ci.get_file_tree(max_files=30)
        system = SYSTEM_PROMPT.format(
            tool_descriptions=self.tools.get_descriptions_for_prompt(),
            repo_context=repo_context,
            task=task,
        )

        self.messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Plan:\n{plan}\n\n"
                    "IMPORTANT: You must actually use tools to complete this task. "
                    "Do NOT give a FINAL_ANSWER until you have:\n"
                    "1. Used search_code or list_directory to find relevant files\n"
                    "2. Used read_file to read actual file contents\n"
                    "3. Used write_file to create any required output files\n"
                    "Start with your first ACTION now."
                ),
            },
        ]
        self.steps = []
        final_answer = ""
        min_steps_before_final = 4

        for step_num in range(1, MAX_STEPS + 1):
            print(f"\n{'─'*40}")
            print(f"Step {step_num}/{MAX_STEPS}")

            response = self._call_llm(self.messages)

            if verbose:
                print(f"\nAgent:\n{response[:500]}")

            thought, action, action_input, is_final = self._parse_action(response)

            # Enforce minimum steps — agent must actually do work
            if is_final and step_num < min_steps_before_final:
                print(f"[agent] Too early for final answer. Forcing agent to continue.")
                self.messages.append({"role": "assistant", "content": response})
                self.messages.append({
                    "role": "user",
                    "content": (
                        "You haven't done enough work yet. "
                        f"You must use at least {min_steps_before_final} tools before finishing. "
                        "Continue with the next ACTION."
                    ),
                })
                continue

            if is_final:
                final_answer = action_input
                print(f"\n[agent] Task complete after {step_num} steps!")
                print(f"\nFINAL ANSWER:\n{final_answer}")
                break

            if not action:
                self.messages.append({"role": "assistant", "content": response})
                self.messages.append({
                    "role": "user",
                    "content": "Specify an ACTION to take next."
                })
                continue

            print(f"\nTHOUGHT: {thought[:200]}")
            print(f"ACTION: {action}")
            print(f"INPUT: {action_input[:100]}")

            observation = self._execute_tool(action, action_input)
            print(f"\nOBSERVATION: {observation[:300]}")

            step = AgentStep(step_num, thought, action, action_input, observation)
            self.steps.append(step)

            self.messages.append({"role": "assistant", "content": response})
            self.messages.append({
                "role": "user",
                "content": (
                    f"OBSERVATION:\n{observation}\n\n"
                    f"Steps completed: {step_num}. "
                    f"Continue with next ACTION. "
                    f"Remember to write_file to create devmind_analysis.md when ready."
                ),
            })

        else:
            final_answer = f"Reached max steps ({MAX_STEPS})."

        return {
            "task": task,
            "plan": plan,
            "steps": len(self.steps),
            "final_answer": final_answer,
            "success": len(self.steps) >= min_steps_before_final,
            "modified_files": self.tools.write.modified_files,
            "agent_steps": [str(s) for s in self.steps],
        }
