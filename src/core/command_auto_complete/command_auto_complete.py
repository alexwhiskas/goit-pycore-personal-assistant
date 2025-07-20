# src/core/command_auto_complete/command_auto_complete.py

import difflib
import copy
from typing import List, Optional, Tuple, Dict

from colorama import Fore, Style, init

from src.core.response_code import PREV_OPERATION
from src.core.decorators import hidden_method
from src.core.record import Record

# Initialize colorama
init(autoreset=True)


class CommandAutoCompletion:
    def __init__ (
            self,
            groups: List[str],
            grouped_command_params: Dict[str, Dict] = None,
            books_records_classes: Dict[str, Record] = None,
            count_matches: int = 5,
            cut_off: float = 0.3
    ):
        self.groups = groups
        self.grouped_command_params = grouped_command_params or {}  # Stores parameters for grouped commands
        self.extracted_from_groups_command_params = self.extract_commands_params(grouped_command_params)  # Stores parameters for each command individually
        self.books_records_classes = books_records_classes or {}  # Stores books records required parameters
        self.count_matches = count_matches
        self.cut_off = cut_off

    def extract_commands_params(self, grouped_command_params: Dict[str, Dict]):
        extracted_from_groups_command_params = {}

        for items in grouped_command_params.values():
            extracted_from_groups_command_params.update(items)

        return extracted_from_groups_command_params

    @hidden_method
    def find_matches (self, user_input: str) -> List[str]:
        if not user_input.strip():
            return []

        # Exact matches first
        exact_matches = []
        if user_input in self.extracted_from_groups_command_params:
            exact_matches.append(user_input)

        # If no exact matches, try close matching
        if not exact_matches:
            return difflib.get_close_matches(
                user_input,
                self.extracted_from_groups_command_params,
                n=self.count_matches,
                cutoff=self.cut_off
            )

        return exact_matches

    def get_best_match (self, user_input: str) -> Optional[str]:
        matches = self.find_matches(user_input)
        return matches[0] if matches else None

    @hidden_method
    def is_incomplete_command (self, user_input: str) -> bool:
        # Check if input ends with comma (indicating incomplete)
        if user_input.strip().endswith(','):
            return True

        # Check if input is a partial match of available commands
        matches = self.find_matches(user_input)
        if matches and user_input.strip() not in self.groups:
            return True

        return False

    @hidden_method
    def should_suggest (self, user_input: str) -> Tuple[bool, List[str]]:
        matches = self.find_matches(user_input)

        # Suggest if we have 2 or more matches OR if command seems incomplete
        should_suggest = (
                len(matches) >= 2 or
                (not matches and self.is_incomplete_command(user_input))
        )

        return should_suggest, matches

    def prompt_for_arguments (self, command: str) -> str | Dict[str, str]:
        """Prompt user for command arguments if required"""
        if command not in self.extracted_from_groups_command_params or not self.extracted_from_groups_command_params[command]:
            return {}

        print(f"\n{Fore.CYAN}🔍 Command '{Fore.GREEN}{command}{Fore.CYAN}' requires arguments:{Style.RESET_ALL}")
        args_dict = {}
        requested_operation_args = copy.deepcopy(self.extracted_from_groups_command_params[command])

        # Special handling for commands without hyphens
        if "-" not in command:
            # For simple commands like "help", just prompt for each argument
            for arg_name, arg_desc in requested_operation_args.items():
                prompt = f"Enter {arg_name} ({arg_desc}) [optional, press Enter to skip]: "
                value = input(prompt).strip()
                if value:
                    args_dict[arg_name] = value
            return args_dict

        # Regular book-specific command handling
        book_name = command.split("-")[1]

        current_book_record_class = None
        required_record_fields = {}
        required_record_fields_to_validate = {}

        # Process book-specific logic
        for supported_book_name, supported_book_record_class in self.books_records_classes.items():
            plural_supported_book_name = supported_book_name + "s"
            if book_name in [supported_book_name, plural_supported_book_name]:
                current_book_record_class = supported_book_record_class
                break

        if current_book_record_class is not None:
            required_record_fields = current_book_record_class.get_record_required_fields()
            required_record_fields_to_validate = current_book_record_class.get_record_fields_to_validate()

        while requested_operation_args:
            request_operation_arg_name, value = next(iter(requested_operation_args.items()))
            requested_operation_arg_label = request_operation_arg_name.replace('_', ' ').capitalize()
            requested_operation_arg_label_prompt = f'Enter {'required' if request_operation_arg_name in required_record_fields else 'optional'} value for {requested_operation_arg_label}: '
            user_input = input(requested_operation_arg_label_prompt).strip()

            def check_input_for_required_field (required_field_input_value: str = ''):
                if not required_field_input_value and request_operation_arg_name in required_record_fields:
                    required_field_input_value = input(
                        'This is a required field, you will be returned to previous step if you won\'t define value for ' + (
                                requested_operation_arg_label[0].lower() + requested_operation_arg_label[1:]) + ': '
                    ).strip()

                    def propose_new_arg_value_or_go_to_prev_step ():
                        prev_operation_option = 'go prev'
                        define_value_again_option = 'try again'

                        prev_operation_or_define_required_field_value_answer = input(
                            f"Want to go to prev operation or try to define new value again ({prev_operation_option}/{define_value_again_option}): "
                        ).strip()

                        if prev_operation_or_define_required_field_value_answer == define_value_again_option:
                            return check_input_for_required_field('')
                        else:
                            if prev_operation_or_define_required_field_value_answer == prev_operation_option:
                                print("Sorry, you didn't entered required field value, you will be redirected to previous step.")

                            return PREV_OPERATION

                    if required_field_input_value == '':
                        required_field_input_value = propose_new_arg_value_or_go_to_prev_step()

                    if required_field_input_value == PREV_OPERATION:
                        return PREV_OPERATION

                if current_book_record_class is not None and request_operation_arg_name in required_record_fields_to_validate:
                    validation_func = getattr(current_book_record_class, "validate_" + request_operation_arg_name, None)

                    if callable(validation_func):
                        try:
                            validation_func(required_field_input_value)
                        except ValueError as val_err:
                            print(f"Validation failed for {request_operation_arg_name}. " + str(val_err))

                            prev_operation_option = "go prev"
                            define_value_again_option = "try again"

                            prev_operation_or_define_required_field_value_answer = input(
                                f"Want to go to prev operation or try to define new value again ({prev_operation_option}/{define_value_again_option}): "
                            ).strip()

                            if prev_operation_or_define_required_field_value_answer == define_value_again_option:
                                return check_input_for_required_field(required_field_input_value)
                            else:
                                if prev_operation_or_define_required_field_value_answer != prev_operation_option:
                                    print(
                                        "Sorry, you didn't entered required field value, you will be redirected to previous step."
                                        )

                                return PREV_OPERATION

                return required_field_input_value

            # we should ask user to enter required fields values or go to previous step if user won't obey to our rules
            field_input_value = check_input_for_required_field(user_input)

            if field_input_value == PREV_OPERATION:
                return field_input_value
            else:
                args_dict[request_operation_arg_name] = field_input_value
                del requested_operation_args[request_operation_arg_name]

        if not args_dict:
            print(f"{Fore.YELLOW}⚠️ No arguments provided. Command may not work as expected.{Style.RESET_ALL}")

        return args_dict

    def prompt_with_completion (self, prompt_text: str = "Enter command: ") -> None | Tuple[str, Dict[str, str]] | Tuple[None, None]:
        while True:
            user_input = input(prompt_text)
            user_input = user_input.strip()

            # If user entered nothing, continue
            if not user_input:
                continue

            # Check if we should suggest completions
            should_suggest, matches = self.should_suggest(user_input)

            if should_suggest or matches:
                best_match = matches[0]
                choice = 'y'

                if should_suggest:
                    print(f"\n{Fore.CYAN}💡 Did you mean: '{Fore.GREEN}{best_match}{Fore.CYAN}'?{Style.RESET_ALL}")
                    question = f"{Fore.YELLOW}Accept suggestion? (yes/no): {Style.RESET_ALL}"
                    not_correct_message = f"{Fore.RED}⚠️ Please enter 'y' or 'n'{Style.RESET_ALL}"

                    if len(matches) > 1:
                        not_correct_message += f" or one of the other options{Style.RESET_ALL}"
                        question = f"{Fore.YELLOW}Accept suggestion or choose one of the other options (yes/one of other option/no): {Style.RESET_ALL}"
                        print(
                            f"{Fore.CYAN}🔄 Other options: {Fore.GREEN}{', '.join(matches[1:3])}{Style.RESET_ALL}"
                        )  # Show up to 2 more

                    choice = input(question).strip().lower()

                if choice == 'yes' or choice == 'y':
                    selected_command = best_match
                elif choice in matches:
                    selected_command = choice
                elif choice == 'no' or choice == 'n':
                    print(f"{Fore.YELLOW}🔄 Please enter your command again:{Style.RESET_ALL}")
                    continue
                else:
                    print("You entered the wrong answer, let's try again.")
                    continue

                return selected_command, self.collect_command_arguments(selected_command)
            else:
                # No suggestions needed or no matches found
                if not matches:
                    print(
                        f"{Fore.RED}❌ Command '{user_input}' not found. {Fore.CYAN}Available commands (10 max matched):{Style.RESET_ALL}"
                    )

                    proposed_groups = []
                    commands_to_propose = []
                    grouped_commands_to_propose = copy.deepcopy(self.grouped_command_params)

                    for group_name in ['global', 'general']:
                        proposed_groups.append(group_name)
                        commands_to_propose += grouped_commands_to_propose[group_name].keys()

                    commands_left_to_propose = (10 - len(commands_to_propose)) / len(grouped_commands_to_propose)
                    for group_name, group_commands in grouped_commands_to_propose.items():
                        if group_name not in commands_to_propose:
                            amount_of_proposed_commands = 0

                            for group_command in group_commands.keys():
                                if amount_of_proposed_commands > commands_left_to_propose:
                                    break
                                commands_to_propose.append(group_command)
                                amount_of_proposed_commands += 1

                    print(f"{Fore.GREEN}{', '.join(self.groups[:10])}{Style.RESET_ALL}")  # Show first 10 commands
                    continue
                else:
                    continue

    def collect_command_arguments (self, selected_command: 'str' = ""):
        # Check if command needs arguments
        if selected_command in self.extracted_from_groups_command_params and self.extracted_from_groups_command_params[selected_command]:
            args = self.prompt_for_arguments(selected_command)
            return args

        return {}