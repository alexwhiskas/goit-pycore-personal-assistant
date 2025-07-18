import difflib
from typing import List, Optional, Tuple

from src.core.decorators import hidden_method


class CommandAutoCompletion:
    def __init__(self, commands: List[str], count_matches: int = 5, cut_off: float = 0.3):
        self.commands = commands
        self.count_matches = count_matches
        self.cut_off = cut_off

    @hidden_method
    def find_matches(self, user_input: str) -> List[str]:
        if not user_input.strip():
            return []

        # Exact matches first
        exact_matches = []
        for cmd in self.commands:
            # Check if command starts with user input
            if cmd.startswith(user_input):
                exact_matches.append(cmd)

        # If no exact matches, try close matching
        if not exact_matches:
            return difflib.get_close_matches(
                user_input,
                self.commands,
                n=self.count_matches,
                cutoff=self.cut_off
            )

        return exact_matches

    def get_best_match(self, user_input: str) -> Optional[str]:
        matches = self.find_matches(user_input)
        return matches[0] if matches else None

    @hidden_method
    def is_incomplete_command(self, user_input: str) -> bool:
        # Check if input ends with comma (indicating incomplete)
        if user_input.strip().endswith(','):
            return True

        # Check if input is a partial match of available commands
        matches = self.find_matches(user_input)
        if matches and user_input.strip() not in self.commands:
            return True

        return False

    @hidden_method
    def should_suggest(self, user_input: str) -> Tuple[bool, List[str]]:
        if user_input in self.commands:
            should_suggest = False
            matches = [user_input]
        else:
            matches = self.find_matches(user_input)
            # Suggest if we have 2 or more matches OR if command seems incomplete
            should_suggest = (
                    len(matches) >= 2 or
                    self.is_incomplete_command(user_input)
            )

        return should_suggest, matches

    def prompt_with_completion(self, prompt_text: str = "Enter command: ") -> str | None:
        while True:
            user_input = input(prompt_text).strip()

            # If user entered nothing, continue
            if not user_input:
                return None

            # Check if we should suggest completions
            should_suggest, matches = self.should_suggest(user_input)

            if should_suggest and matches:
                best_match = matches[0]
                allowed_matches = matches[:self.count_matches]

                print(f"\nDid you mean: '{best_match}'?")
                question = "Accept suggestion? (yes/no): "
                not_correct_message = "Please enter 'y' or 'n'"
                if len(matches) > 1:
                    not_correct_message = "Please enter 'y', 'n' or one of the other options"
                    question = "Accept suggestion or choose one of the other options? (yes/one_of_other_option/no): "
                    print(f"Other options: {', '.join(allowed_matches[1:])}")  # Show up to configured amount of matches

                choice = input(question).strip().lower()

                if choice == 'yes':
                    return best_match
                elif choice in allowed_matches:
                    return choice
                elif choice == 'no':
                    print("Please enter your command again:")
                    return None
                else:
                    print(not_correct_message)
                    return None
            else:
                # No suggestions needed or no matches found
                if len(matches) == 1:
                    return user_input
                else:
                    return None  # return nothing