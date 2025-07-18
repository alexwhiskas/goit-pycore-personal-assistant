# main.py


import signal
import sys
from functools import wraps

from src.bot.book_manager import BookManager
from src.core.record import Record

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
        print(f' - {cmd}' + (f" {' '.join(f"{k}={v}" for k, v in params.items())}" if params else ""))

    try:
        while True:
            user_input = input("Enter a command: ").strip().lower()
            user_input_parts = user_input.split()

            args = []
            kwargs = {}
            for arg in user_input_parts:
                if '=' in arg:
                    key, value = arg.split('=')
                    kwargs[key] = value
                else:
                    args.append(arg)

            cmd = args.pop(0).strip().lower()

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
