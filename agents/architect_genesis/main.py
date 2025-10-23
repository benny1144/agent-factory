import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from crewai import Agent, Task, Crew, Process, LLM

# --- Setup Project Root Path ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))
from tools.charter_tools import search_knowledge_base
from tools.search_tools import search_tool

def main():
    """
    Main function to run the Ultimate Genesis Architect Crew.
    """
    # --- 0. Setup Environment ---
    dotenv_path = find_dotenv(filename=".env", usecwd=True) or (PROJECT_ROOT / ".env")
    if dotenv_path:
        load_dotenv(dotenv_path)

    # --- Env key mapping for robustness between Google/Gemini ---
    # Ensure both GEMINI_API_KEY and GOOGLE_API_KEY are available when only one is set.
    if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

    # --- Resilient LLM Initialization without unsupported probe calls ---
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))

    # Choose worker model by available keys (preference: Groq → Gemini → OpenAI)
    if has_groq:
        worker_model = "groq/llama3-70b-8192"
        print("Using Groq as the primary worker LLM.")
    elif has_gemini:
        worker_model = "gemini/gemini-2.5-flash"
        print("Using Gemini Flash as the primary worker LLM.")
    elif has_openai:
        worker_model = "openai/gpt-4o-mini"
        print("Using OpenAI as the primary worker LLM.")
    else:
        raise RuntimeError(
            "No supported LLM API keys found. Set GROQ_API_KEY, GEMINI_API_KEY/GOOGLE_API_KEY, or OPENAI_API_KEY."
        )

    llm = LLM(model=worker_model, temperature=0.2)

    # Manager LLM preference (Gemini Pro if available, else OpenAI, else Groq)
    if has_gemini:
        manager_model = "gemini/gemini-2.5-pro"
    elif has_openai:
        manager_model = "openai/gpt-4-turbo"
    elif has_groq:
        manager_model = "groq/llama3-70b-8192"
    else:
        manager_model = worker_model  # Should be unreachable due to earlier check

    manager_llm = LLM(model=manager_model, temperature=0.2)

    # --- 1. DEFINE AGENTS ---
    knowledge_seeker = Agent(
        role="Senior AI Research Analyst",
        goal="Conduct comprehensive research to inform the creation of a new agentic crew based on the user's request.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_knowledge_seeker.md").read_text(encoding="utf-8"),
        tools=[search_knowledge_base, search_tool],
        llm=llm,
        verbose=True,
    )

    charter_agent = Agent(
        role="Principal Solutions Architect",
        goal="Create a detailed, structured Project Charter for a new agentic crew based on provided research.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_charter_agent.md").read_text(encoding="utf-8"),
        llm=llm,
        verbose=True,
    )

    code_architect_agent = Agent(
        role="Lead Agent Engineer",
        goal="Take a Project Charter and write the complete, production-ready Python code for the new CrewAI agent crew.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_code_architect.md").read_text(encoding="utf-8"),
        llm=llm,
        verbose=True,
    )

    critic_agent = Agent(
        role="Principal Quality Assurance Engineer",
        goal="Review the Project Charter and the generated Python code to ensure they are aligned, complete, and adhere to all best practices.",
        backstory=(PROJECT_ROOT / "personas" / "genesis_critic_agent.md").read_text(encoding="utf-8"),
        llm=llm,
        verbose=True,
    )

    manager_agent = Agent(
        role="Genesis Crew Manager",
        goal="Orchestrate the research, planning, coding, and critique process to build a new agentic crew. Ensure the final deliverable is a high-quality, runnable Python script that meets the user's goal.",
        backstory="You are the master architect of the Agent Factory. You manage your expert team to ensure a flawless execution from concept to code.",
        llm=manager_llm,
        verbose=True
    )

    # --- 2. DEFINE TASKS ---
    print("--- Welcome to the Ultimate Genesis Architect ---")
    # Allow non-interactive runs via env var or CLI arg
    user_goal = os.getenv("GENESIS_USER_GOAL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not user_goal:
        user_goal = input("What kind of agentic crew would you like to build today?\n> ")

    research_task = Task(
        description=f"Conduct thorough research on the user's goal: '{user_goal}'. First, search the internal knowledge base for best practices and templates. If needed, use the web search tool to find modern, external examples and architectural patterns.",
        expected_output="A markdown research brief summarizing findings, including internal best practices and external examples relevant to the user's goal.",
        agent=knowledge_seeker,
    )

    charter_task = Task(
        description="Using the research brief, create a comprehensive Project Charter for the new agent crew. The charter must be detailed and follow the standard template.",
        expected_output="A complete Project Charter in markdown format.",
        agent=charter_agent,
        context=[research_task],
    )

    code_task = Task(
        description="Based ONLY on the Project Charter provided, write the complete, runnable Python script for the new agent crew. Do not use any other examples.",
        expected_output="A single Python code block containing the full CrewAI script.",
        agent=code_architect_agent,
        context=[charter_task],
    )

    critique_task = Task(
        description="Review the Project Charter and the generated Python code. Check for alignment, completeness, and adherence to our best practices. Provide actionable feedback or approve the code.",
        expected_output="Either the original Python code block if it is perfect, or a list of required changes.",
        agent=critic_agent,
        context=[charter_task, code_task],
    )

    report_task = Task(
        description="Compile the final report. Review the critique and the code. If the critique required changes, ask the Lead Agent Engineer to rewrite the code incorporating the feedback. The final output MUST be only the finished, approved Python code block.",
        expected_output="The final, complete, runnable Python code block for the new agent crew.",
        agent=manager_agent,
        context=[critique_task, code_task],
    )

    # --- 3. CREATE AND RUN THE CREW ---
    genesis_crew = Crew(
        agents=[knowledge_seeker, charter_agent, code_architect_agent, critic_agent],
        tasks=[research_task, charter_task, code_task, critique_task, report_task],
        process=Process.hierarchical,
        manager_agent=manager_agent,
        verbose=True,
    )

    print("\n--- Ultimate Genesis Crew is now building your new agent crew... ---")
    result = genesis_crew.kickoff()

    print("\n--- Genesis Crew Work Complete ---")
    print("Final Result:")
    print(result)

if __name__ == "__main__":
    main()
