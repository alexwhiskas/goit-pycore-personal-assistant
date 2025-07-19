# main.py


import signal
import sys
from functools import wraps

from src.bot.book_manager import BookManager
from src.core.record import Record
from src.core.command_auto_complete.command_auto_complete import CommandAutoCompletion
from src.core.table_formatter import TableFormatter
from src.core.fast_search_adapter import FastSearchAdapter
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

book_manager = BookManager()


# gracefully handle the exit signal
def handle_exit_signal (signum, frame):
    book_manager.save_books_state()
    print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_exit_signal)


def input_error (func):
    @wraps(func)
    def wrapper (*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (KeyError, ValueError, IndexError, TypeError) as e:
            return f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}"

    return wrapper


def main ():
    # Show all supported commands
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📚 Welcome to Personal Assistant! 📚{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    print(f"{Fore.MAGENTA}🔍 Supported commands:{Style.RESET_ALL}")
    supported_operations = book_manager.get_supported_operations()

    # Add the help command to the operations
    supported_operations['help'] = {'block': 'optional'}

    # Add global search command
    supported_operations['search-all'] = {'query': f'text to search (min {FastSearchAdapter.MIN_SEARCH_LENGTH} chars)'}

    # Add search commands for each book type
    for book_name in book_manager.books:
        supported_operations[f'search-{book_name}'] = {'query': f'text to search (min {FastSearchAdapter.MIN_SEARCH_LENGTH} chars)'}

    command_list = list(supported_operations.keys())
    completer = CommandAutoCompletion(command_list, supported_operations)

    # Group commands by book type for better organization
    grouped_commands = {}
    for cmd, params in supported_operations.items():
        if cmd == 'search-all':
            book_type = 'global'
        elif len(cmd.split('-')) > 1:
            book_type = cmd.split('-')[1]
        else:
            book_type = 'general'

        if book_type not in grouped_commands:
            grouped_commands[book_type] = []
        grouped_commands[book_type].append((cmd, params))

    # Print commands by group - show global commands first
    if 'global' in grouped_commands:
        print(f"\n{Fore.BLUE}🌐 Global commands:{Style.RESET_ALL}")
        for cmd, params in grouped_commands['global']:
            params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
            print(f"{Fore.GREEN} ✓ {cmd}{params_str}")

    if 'general' in grouped_commands:
        print(f"\n{Fore.BLUE}📋 General commands:{Style.RESET_ALL}")
        for cmd, params in grouped_commands['general']:
            params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
            print(f"{Fore.GREEN} ✓ {cmd}{params_str}")

    # Then show book-specific commands
    for book_type, commands in grouped_commands.items():
        if book_type not in ['global', 'general']:
            print(f"\n{Fore.BLUE}📗 {book_type.capitalize()} commands:{Style.RESET_ALL}")
            for cmd, params in commands:
                params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
                print(f"{Fore.GREEN} ✓ {cmd}{params_str}")

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}ℹ️ Press Ctrl+C to exit at any time{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

    try:
        while True:
            cmd_and_args = completer.prompt_with_completion(f"{Fore.CYAN}💬 Enter a command: {Style.RESET_ALL}")
            user_input, prompted_args = cmd_and_args

            if user_input is None:
                print(f"{Fore.RED}⚠️ No command entered. Please try again.{Style.RESET_ALL}")
                continue

            # Parse the command if it has inline arguments
            if ' ' in user_input:
                user_input_parts = user_input.strip().lower().split()
                cmd = user_input_parts.pop(0).strip().lower()

                args = []
                kwargs = {}
                for arg in user_input_parts:
                    if '=' in arg:
                        key, value = arg.split('=')
                        kwargs[key] = value
                    else:
                        args.append(arg)
            else:
                # Use the command as is and any prompted arguments
                cmd = user_input.strip().lower()
                args = []
                kwargs = prompted_args or {}

            if len(cmd) == 0:
                print(f"{Fore.RED}⚠️ No command entered. Please try again.{Style.RESET_ALL}")
                continue

            # Handle help command directly
            if cmd == 'help':
                block = kwargs.get('block') or (args[0] if args else None)
                print(f"{Fore.YELLOW}📖 Displaying help information...{Style.RESET_ALL}")
                help_result = book_manager.print_commands(block)
                for line in help_result:
                    print(line)
                continue

            print(f"{Fore.YELLOW}⏳ Processing command...{Style.RESET_ALL}")

            try:
                command_result = book_manager.run_command(cmd, *args, **kwargs)

                if command_result is False:
                    print(f"{Fore.RED}❌ Unknown command '{cmd}'. Try again or use 'help' for available commands.{Style.RESET_ALL}")
                    continue
                else:
                    if command_result is not True:
                        if (isinstance(command_result, dict)
                            and 'function_name' in command_result
                            and 'result' in command_result
                        ):
                            # Handle error messages
                            if isinstance(command_result['result'], str) and 'error' in command_result['function_name'].lower():
                                print(f"{Fore.RED}❌ {command_result['result']}{Style.RESET_ALL}")
                                continue

                            # Check if it's a list of records to display as a table
                            if isinstance(command_result['result'], list) and all(isinstance(r, Record) for r in command_result['result']):
                                # Get the command base and handle empty results
                                if len(command_result['result']) == 0:
                                    if cmd == 'search-all':
                                        print(f"{Fore.YELLOW}🔍 No results found for global search.{Style.RESET_ALL}")
                                    elif cmd.startswith('search-'):
                                        print(f"{Fore.YELLOW}🔍 No results found in {cmd.replace('search-', '')} for your search.{Style.RESET_ALL}")
                                    else:
                                        print(f"{Fore.YELLOW}📭 No records found{Style.RESET_ALL}")
                                    continue

                                # Get appropriate title for the table
                                if cmd == 'search-all':
                                    title = f"Global search results for '{kwargs.get('query') or args[0] if args else ''}'"
                                elif cmd.startswith('search-'):
                                    title = f"Search results for {cmd.replace('search-', '')}"
                                else:
                                    title = cmd.replace("get-", "").replace("add-", "").replace("update-", "").capitalize()

                                # Format and display as table
                                table_lines = TableFormatter.format_records_as_table(
                                    command_result['result'],
                                    f"{title} from '{command_result['function_name']}'"
                                )
                                for line in table_lines:
                                    print(line)
                            else:
                                # Handle single record creation/update
                                if cmd.startswith('add-') or cmd.startswith('update-'):
                                    if isinstance(command_result['result'], Record):
                                        # Format single record as table for better display
                                        table_lines = TableFormatter.format_records_as_table(
                                            [command_result['result']],
                                            f"Created/Updated {cmd.split('-')[1].capitalize()}"
                                        )
                                        for line in table_lines:
                                            print(line)
                                    else:
                                        print(f"{Fore.GREEN}✅ Command executed successfully: {command_result['result']}{Style.RESET_ALL}")
                                else:
                                    print(f"{Fore.GREEN}✅ Command executed successfully: {command_result['result']}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.GREEN}✅ {command_result}{Style.RESET_ALL}")
            except ValueError as e:
                print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")

    finally:
        book_manager.save_books_state()
        print(f"\n{Fore.GREEN}✅ Address book saved.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
