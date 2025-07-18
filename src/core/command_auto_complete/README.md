# Command Auto-Complete

The `CommandAutoCompletion` class provides an intelligent autocomplete system for command-line interfaces. It helps users by suggesting the most relevant commands based on their input, improving user experience and reducing errors.

## Features

1. **Exact Match Suggestions**:
   - If the user's input matches the beginning of any command, those commands are suggested first
   - Prioritizes exact prefix matches over fuzzy matches

2. **Fuzzy Matching**:
   - When no exact matches are found, the system uses fuzzy matching to suggest similar commands
   - Uses Python's `difflib` to find commands that closely resemble the user's input

3. **Incomplete Command Detection**:
   - Detects if a command is incomplete (e.g., ends with a comma)
   - Identifies partial matches that could be completed to valid commands

4. **Interactive Suggestions**:
   - Presents users with the best match and additional options
   - Allows users to accept the suggestion, choose from alternatives, or reject suggestions
   - Provides clear prompts for user decision-making

5. **Fallback Mechanism**:
   - When no matches are found, displays a list of available commands (up to 10)
   - Provides informative feedback to help users navigate the command set

## Usage

```python
from src.core.command_auto_complete.command_auto_complete import CommandAutoCompletion

# Initialize with available commands
commands = ["add", "add-contact", "add-phone", "change", "delete", "exit", "help"]
autocomplete = CommandAutoCompletion(commands)

# Use in your application
user_command = autocomplete.prompt_with_completion("Enter command: ")
if user_command:
    # Process the command
    print(f"Executing: {user_command}")
else:
    print("No valid command provided")
```

## Key Methods

- **`get_best_match(user_input: str) -> Optional[str]`**:  
  Returns the best matching command or None if no matches are found.

- **`prompt_with_completion(prompt_text: str = "Enter command: ") -> str | None`**:  
  Provides an interactive prompt with autocomplete suggestions, returning the selected command or None if no valid selection.

## Example Interaction

```
Enter command: ad

Did you mean: 'add'?
Other options: add-contact, add-phone
Accept suggestion or choose one of the other options? (yes/one of other option/no): add-contact
```

## Implementation Details

- Uses a configurable cutoff value (default 0.3) for fuzzy matching to balance precision and recall
- Shows a configurable number of close matches (default 5) for any given input
- Limits displayed available commands to 10 to avoid overwhelming the user
- Returns None when no valid command is selected or user rejects suggestions
- Shows up to 2 additional suggestions when multiple matches are found
- Handles both exact prefix matches and fuzzy matches for maximum flexibility
- Accepts direct selection of alternative options (not just yes/no)
- If user enters a valid command directly, it's accepted without suggestions
