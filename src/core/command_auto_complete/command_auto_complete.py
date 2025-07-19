import difflib
from typing import List, Optional, Tuple, Dict
from colorama import Fore, Style, init

from src.core.decorators import hidden_method

# Initialize colorama
init(autoreset=True)


class CommandAutoCompletion:
    def __init__(self, commands: List[str], command_params: Dict[str, Dict] = None, count_matches: int = 5, cut_off: float = 0.3):
        self.commands = commands
        self.command_params = command_params or {}  # Store parameters for each command
        self.count_matches = count_matches
        self.cut_off = cut_off

    @hidden_method
    def find_matches(self, user_input: str) -> List[str]:
        if not user_input.strip():
            return []

        # Exact matches first
        exact_matches = []
        for cmd in self.commands:
            if cmd == user_input:
                return [cmd]
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
        matches = self.find_matches(user_input)

        # Suggest if we have 2 or more matches OR if command seems incomplete
        should_suggest = (
                len(matches) >= 2 or
                self.is_incomplete_command(user_input)
        )

        return should_suggest, matches

    def prompt_for_arguments(self, command: str) -> Dict[str, str]:
        """Prompt user for command arguments if required"""
        if command not in self.command_params or not self.command_params[command]:
            return {}

        print(f"\n{Fore.CYAN}🔍 Command '{Fore.GREEN}{command}{Fore.CYAN}' requires arguments:{Style.RESET_ALL}")
        args_dict = {}

        for param_name, param_desc in self.command_params[command].items():
            # Skip optional parameters if user leaves them blank
            arg_value = input(f"{Fore.YELLOW}Enter {param_name} ({param_desc}){Fore.CYAN} [optional, press Enter to skip]: {Style.RESET_ALL}")
            if arg_value.strip():
                args_dict[param_name] = arg_value

        if not args_dict:
            print(f"{Fore.YELLOW}⚠️ No arguments provided. Command may not work as expected.{Style.RESET_ALL}")

        return args_dict

    def prompt_with_completion(self, prompt_text: str = "Enter command: ") -> Tuple[str, Dict[str, str]] | Tuple[None, None]:
        while True:
            user_input = input(prompt_text).strip()

            # If user entered nothing, continue
            if not user_input:
                return None, None

            # Check if we should suggest completions
            should_suggest, matches = self.should_suggest(user_input)

            if should_suggest and matches:
                best_match = matches[0]

                print(f"\n{Fore.CYAN}💡 Did you mean: '{Fore.GREEN}{best_match}{Fore.CYAN}'?{Style.RESET_ALL}")
                question = f"{Fore.YELLOW}Accept suggestion? (yes/no): {Style.RESET_ALL}"
                not_correct_message = f"{Fore.RED}⚠️ Please enter 'y' or 'n'{Style.RESET_ALL}"
                if len(matches) > 1:
                    not_correct_message = f"{Fore.RED}⚠️ Please enter 'y', 'n' or one of the other options{Style.RESET_ALL}"
                    question = f"{Fore.YELLOW}Accept suggestion or choose one of the other options? (yes/one of other option/no): {Style.RESET_ALL}"
                    print(f"{Fore.CYAN}🔄 Other options: {Fore.GREEN}{', '.join(matches[1:3])}{Style.RESET_ALL}")  # Show up to 2 more

                choice = input(question).strip().lower()

                if choice == 'yes' or choice == 'y':
                    selected_command = best_match
                    # Check if command needs arguments
                    if selected_command in self.command_params and self.command_params[selected_command]:
                        args = self.prompt_for_arguments(selected_command)
                        return selected_command, args
                    return selected_command, {}

                elif choice in matches[1:]:
                    selected_command = choice
                    # Check if command needs arguments
                    if selected_command in self.command_params and self.command_params[selected_command]:
                        args = self.prompt_for_arguments(selected_command)
                        return selected_command, args
                    return selected_command, {}

                elif choice == 'no' or choice == 'n':
                    print(f"{Fore.YELLOW}🔄 Please enter your command again:{Style.RESET_ALL}")
                    continue
                else:
                    print(not_correct_message)
                    continue
            else:
                # No suggestions needed or no matches found
                if user_input in self.commands:
                    selected_command = user_input
                    # Check if command needs arguments
                    if selected_command in self.command_params and self.command_params[selected_command]:
                        args = self.prompt_for_arguments(selected_command)
                        return selected_command, args
                    return selected_command, {}

                elif not matches:
                    print(f"{Fore.RED}❌ Command '{user_input}' not found. {Fore.CYAN}Available commands (10 max matched):{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}{', '.join(self.commands[:10])}{Style.RESET_ALL}")  # Show first 10 commands
                    return None, None
                else:
                    # If user already entered arguments with the command, don't prompt again
                    if ' ' in user_input:
                        return user_input, {}  # Return as-is and let main handle parsing

                    selected_command = user_input
                    # Check if command needs arguments
                    if selected_command in self.command_params and self.command_params[selected_command]:
                        args = self.prompt_for_arguments(selected_command)
                        return selected_command, args
                    return selected_command, {}
