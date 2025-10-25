import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser  # <-- We add an output parser

# Add src path for utilities and audit
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "src"))

from agent_factory.services.audit.audit_logger import log_tool_creation
from utils.paths import TOOLS_DIR, TESTS_DIR, PERSONAS_DIR
from utils.procedural_memory_pg import register_tool

def main():
    """
    Main function to run the Toolmaker's Co-Pilot agent.
    """
    # Load environment variables from .env file
    load_dotenv()

    # --- 1. Agent Setup ---
    # Initialize the Large Language Model (LLM) from Google
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

    # Load the agent's persona from the markdown file
    try:
        persona_path = PERSONAS_DIR / "toolmaker_copilot.md"
        with open(persona_path, "r", encoding="utf-8") as f:
            persona = f.read()
    except FileNotFoundError:
        print(f"Error: The persona file '{persona_path}' was not found.")
        return

    # --- 2. Prompt Engineering ---
    # Create a prompt template.
    prompt = PromptTemplate(
        template="""
        {persona}

        ---
        **New Tool Request**

        **Tool Name:** `{tool_name}`
        **Tool Description:** `{tool_description}`
        **Core Logic Snippet:**
        ```python
        {core_logic}
        ```
        ---

        Based on your role and the request above, generate the complete, specification-compliant Python code for this new tool.
        """,
        input_variables=["persona", "tool_name", "tool_description", "core_logic"]
    )

    # --- 3. Create the LangChain "Chain" (The NEW Way) ---
    # This is the modern LangChain Expression Language (LCEL) syntax.
    # We "pipe" the prompt to the llm, and then pipe the llm's output
    # to a simple string output parser.
    agent_chain = prompt | llm | StrOutputParser()

    # --- 4. Get User Input for a New Tool ---
    print("--- Toolmaker's Co-Pilot ---")
    print("Provide the details for the new tool you want to build.")

    tool_name = input("Enter the tool's name (e.g., 'file_reader'): ")
    tool_description = input("Enter a one-sentence description: ")
    print("Enter the core Python logic (press Ctrl+D or Ctrl+Z then Enter when done):")
    core_logic = ""
    while True:
        try:
            line = input()
        except EOFError:
            break
        core_logic += line + "\n"

    # --- 5. Run the Agent ---
    # With LCEL, we use .invoke() and pass in the dictionary of inputs.
    print("\n--- Generating new tool... ---")
    response = agent_chain.invoke({
        "persona": persona,
        "tool_name": tool_name,
        "tool_description": tool_description,
        "core_logic": core_logic
    })

    # --- 6. Display the Result ---
    print("\n--- Generated Tool Code ---")
    print(response)

    # --- 7. Parse code block and save tool ---
    code_match = re.search(r"```(?:python)?\n(.*?)```", response, re.DOTALL)
    if not code_match:
        print("[Toolmaker] No Python code block found in response. Aborting save.")
        return
    code_str = code_match.group(1).strip()

    tool_filename = f"{tool_name}.py"
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    tool_path = TOOLS_DIR / tool_filename
    tool_path.write_text(code_str, encoding="utf-8")
    print(f"[Toolmaker] Saved tool to {tool_path}")

    # Try to extract schema JSON block if present
    schema = None
    schema_match = re.search(r"```json\n(\{[\s\S]*?\})\n```", response)
    if schema_match:
        try:
            import json
            schema = json.loads(schema_match.group(1))
        except Exception:
            schema = None
    else:
        try:
            from agent_factory.services.audit.audit_logger import log_event
            log_event("tool_schema_missing", {"tool_name": tool_name})
        except Exception:
            pass

    # --- 8. Audit log and DB register ---
    log_tool_creation(tool_name, {"path": str(tool_path)})
    try:
        register_tool(tool_name, path=tool_path, schema=schema)
    except Exception as e:
        print(f"[Toolmaker] Warning: failed to register tool in DB: {e}")

    # --- 9. Auto-generate a basic test ---
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    test_file = TESTS_DIR / f"test_{tool_name}.py"
    if not test_file.exists():
        test_file.write_text(
            f"from importlib.machinery import SourceFileLoader\n\n"
            f"mod = SourceFileLoader('{tool_name}', r'{tool_path}').load_module()\n\n"
            f"def test_module_loads():\n    assert hasattr(mod, '__doc__')\n",
            encoding="utf-8",
        )
        print(f"[Toolmaker] Generated test at {test_file}")

if __name__ == "__main__":
    main()
