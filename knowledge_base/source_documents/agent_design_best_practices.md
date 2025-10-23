# Agent Factory: Best Practices for Agent & Crew Design (v1.0)

## I. Core Principles (Mandatory Adherence)

1.  **Security First (Human Firewall Protocol):** All agent designs MUST prioritize security, reliability, and human oversight. Integrate the AI Agent Human Firewall Protocol at all layers. Assume tools can fail or be misused; build in validation and error handling. Implement human-in-the-loop for critical decisions.
2.  **Modularity & Specialization:** Design agents with clear, distinct roles and goals (CrewAI `role` and `goal`). Avoid overly broad agents. Decompose complex problems into tasks solvable by specialized agents.
3.  **Persona Fidelity:** Craft high-fidelity personas (`backstory`) that act as the agent's "operating system." Personas must define expertise, operational boundaries, and interaction style. Consistency is key. (Reference: AE - Prompt Engineering Masterclass: Agent Personas).
4.  **Tool Standardization:** Agents MUST use tools from the certified library (`/tools`). All tools MUST adhere to the "Specification for Architect-Grade Agent Tools," including standardized response envelopes and resilience protocols.
5.  **Context Management:** Design tasks and agent interactions to manage context effectively. Use CrewAI `context` passing between tasks. Ensure agents receive only the necessary information to perform their specific role.
6.  **Clear Objectives & Outputs:** Define tasks with precise `description` and `expected_output` fields. Outputs should be structured and predictable.

***

## II. Crew Architecture Patterns (Reference: AE & G - CrewAI Architect's Handbook)

1.  **Sequential Process (`Process.sequential`):**
    * **Use Case:** Linear workflows where tasks must happen in a fixed order (e.g., data processing pipelines).
    * **Pros:** Simple, predictable, easy to debug. Full context passed between steps.
    * **Cons:** Rigid, no dynamic adaptation, potential for context overload in long chains.
2.  **Hierarchical Process (`Process.hierarchical`):**
    * **Use Case:** Complex, dynamic tasks requiring planning, delegation, and synthesis (e.g., research, coding, creative generation). **This is the default for Genesis-built crews.**
    * **Pros:** Flexible, allows for dynamic task re-ordering, enables sophisticated collaboration via a manager agent.
    * **Cons:** More complex to design and debug, requires careful manager agent persona engineering.
    * **Implementation:** Requires an explicit `manager_agent`. The manager MUST be included in the `agents` list and assigned a final task (e.g., `report_task`) to ensure the full process completes and returns the desired final output.

***

## III. Agent Design Best Practices

1.  **Role & Goal Definition:** Be specific. Instead of "Marketing Agent," use "Social Media Content Creator for Twitter." Goals should be measurable and actionable.
2.  **Backstory Crafting:** Provide context, expertise, and operational rules. Example: "You are a senior copywriter specializing in concise, engaging Twitter content. You always adhere to the company brand guide..."
3.  **Tool Selection:** Assign only the necessary tools to each agent (Principle of Least Privilege). Ensure agents understand *when* and *how* to use their tools via persona and task descriptions.
4.  **`allow_delegation`:** Set to `False` for worker agents unless explicitly needed. Only manager/coordinator agents should typically delegate.
5.  **`verbose=True`:** Keep this enabled during development for debugging. Consider disabling in production for performance unless detailed logging is required elsewhere.
6.  **LLM Selection:** Use the appropriate model for the task. Use high-speed models (e.g., `gemini-2.5-flash`) for structured, repetitive tasks. Use high-reasoning models (e.g., `gemini-2.5-pro`) for managers, complex analysis, or creative generation.

***

## IV. Task Design Best Practices

1.  **Clear Descriptions:** Explain *what* the agent needs to do and *why*. Provide necessary context or constraints.
2.  **Precise Expected Outputs:** Define the *format* and *content* of the desired result. E.g., "A JSON object containing..." or "A markdown report with sections..."
3.  **Context Passing:** Use the `context=[task1, task2]` argument to ensure agents receive necessary prior information.
4.  **Human Input:** For tasks requiring human-in-the-loop, design the task description and `expected_output` to explicitly prompt for and handle human input (often managed by the HFO agent persona).

***

## V. Knowledge Base Integration (RAG)

1.  **Curated Knowledge:** Ensure the vector store contains accurate, relevant, and well-structured information. Regularly update and curate the source documents.
2.  **Tool Usage:** Equip relevant agents (e.g., Planners, Researchers, Analysts) with the `search_knowledge_base` tool.
3.  **Prompting:** Instruct agents via persona or task description to *prioritize* using the knowledge base search before relying on internal knowledge or generating potentially inaccurate information. Example Task: "Use the `search_knowledge_base` tool *first* to find our established procedures for X, then proceed..."

By adhering to these practices, we build reliable, secure, and effective agentic crews within the Agent Factory ecosystem.