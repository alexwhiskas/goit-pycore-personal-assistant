# src/core/books/note/note_book.py

from src.core.book import Book, hidden_method


class NoteBook(Book):
    @hidden_method
    def get_book_name (self) -> str:
        return 'note'
