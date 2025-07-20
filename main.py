# main.py


import signal
import sys
from functools import wraps

from colorama import init, Fore, Style

from src.bot.book_manager import BookManager

# Initialize colorama
init(autoreset=True)

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
    try:
        book_manager.start(f'Hi, I\'m a book manager, please select a book you would like to work with:')
    finally:
        book_manager.save_books_state()
        print("\nAddress book saved.")


if __name__ == "__main__":
    main()
