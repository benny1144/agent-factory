from typing import TypedDict, Union, Any
import os

class SuccessResponse(TypedDict):
    """Standardized success response envelope."""
    success: bool
    result: Any

class ErrorResponse(TypedDict):
    """Standardized error response envelope."""
    success: bool
    error: str

ToolResponse = Union[SuccessResponse, ErrorResponse]

def read_file(filepath: str) -> ToolResponse:
    """Reads the content of a specified file.

    This tool opens a file at the given filepath and returns its entire content
    as a string. It handles various file-related errors gracefully, including
    file not found, permission issues, and decoding problems.

    Args:
        filepath: The absolute or relative path to the file to be read.

    Returns:
        A dictionary indicating success or failure:
        - On success: `{"success": true, "result": "file content"}`
        - On failure: `{"success": false, "error": "error message"}`
    """
    if not isinstance(filepath, str) or not filepath:
        return {"success": False, "error": "Filepath must be a non-empty string."}

    try:
        # Ensure the path is absolute for consistent behavior, though open() handles relative paths.
        # This also helps in clearer error messages if the path is malformed.
        absolute_filepath = os.path.abspath(filepath)

        if not os.path.exists(absolute_filepath):
            return {"success": False, "error": f"File not found at '{absolute_filepath}'."}

        if os.path.isdir(absolute_filepath):
            return {"success": False, "error": f"Path '{absolute_filepath}' is a directory, not a file."}

        with open(absolute_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"success": True, "result": content}
    except FileNotFoundError:
        # This case should ideally be caught by os.path.exists, but kept for robustness.
        return {"success": False, "error": f"File not found at '{absolute_filepath}'."}
    except PermissionError:
        return {"success": False, "error": f"Permission denied to read file at '{absolute_filepath}'. Check file permissions."}
    except UnicodeDecodeError as e:
        return {"success": False, "error": f"Failed to decode file content at '{absolute_filepath}' with UTF-8 encoding: {e}. The file might be in a different encoding."}
    except IOError as e:
        return {"success": False, "error": f"An I/O error occurred while reading file at '{absolute_filepath}': {e}"}
    except Exception as e:
        # Catch any other unexpected errors
        return {"success": False, "error": f"An unexpected error occurred while reading '{absolute_filepath}': {e}"}