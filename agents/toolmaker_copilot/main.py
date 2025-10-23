import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser  # <-- We add an output parser

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
        with open("../../personas/toolmaker_copilot.md", "r") as f:
            persona = f.read()
    except FileNotFoundError:
        print("Error: The persona file 'personas/toolmaker_copilot.md' was not found.")
        print("Please ensure you are in the 'agents/toolmaker_copilot' directory.")
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

if __name__ == "__main__":
    main()
