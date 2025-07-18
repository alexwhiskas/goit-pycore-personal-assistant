# main.py


import signal
import sys
import shlex

from functools import wraps

from src.bot.book_manager import BookManager
from src.core.record import Record
from src.core.command_auto_complete.command_auto_complete import CommandAutoCompletion

book_manager = BookManager()


# gracefully handle the exit signal
def handle_exit_signal (signum, frame):
    book_manager.save_books_state()
    sys.exit(0)


signal.signal(signal.SIGINT, handle_exit_signal)


def input_error (func):
    @wraps(func)
    def wrapper (*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (KeyError, ValueError, IndexError, TypeError) as e:
            return f"Error: {str(e)}"

    return wrapper


def main ():
    # Show all supported commands
    print('📚 Supported commands:')
    supported_operations = book_manager.get_supported_operations()

    for cmd, params in supported_operations.items():
        print(f' - {cmd}')
        # uncomment if you need to check accepted by functions params
        # print(f' - {cmd}' + (f" {' '.join(f"{k}={v}" for k, v in params.items())}" if params else ""))

    try:
        command_autocompletion = CommandAutoCompletion(supported_operations.keys())

        while True:
            cmd = command_autocompletion.prompt_with_completion()

            if cmd in supported_operations:
                cmd_params = supported_operations[cmd]
                prompt_for_command_params = f' - Please enter following params: ' + (f"{' '.join(f"{k}={v}" for k, v in cmd_params.items())}" if params else "")
                user_input_parts = input(prompt_for_command_params + "\n").strip()
            else:
                raise KeyError(f'Command "{cmd}" not found')

            args = [] # todo: potentially redundant param, to delete
            kwargs = dict(part.split("=", 1) for part in shlex.split(user_input_parts))

            command_result = book_manager.run_command(cmd, *args, **kwargs)
            if command_result is False:
                break
            else:
                if command_result is not True:
                    if (isinstance(command_result, dict)
                        and 'function_name' in command_result
                        and 'result' in command_result
                    ):
                        if isinstance(command_result['result'], list) and all(isinstance(r, Record) for r in command_result['result']):
                            print(f"Function '{command_result['function_name']}' returned {len(command_result['result'])} record(s):")

                            for record in command_result['result']:
                                print(record)
                                print("-" * 30)
                else:
                    print(command_result)
    finally:
        book_manager.save_books_state()
        print("\nAddress book saved.")

if __name__ == "__main__":
    main()
