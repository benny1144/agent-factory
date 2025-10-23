import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from crewai_tools import SerperDevTool

# Load .env if present (safe if already loaded)
_dotenv = find_dotenv(filename=".env", usecwd=True)
if _dotenv:
    load_dotenv(_dotenv, override=False)

# Initialize the tool with your SERPER_API_KEY
# The key will be read automatically from the .env file
search_tool = SerperDevTool()
