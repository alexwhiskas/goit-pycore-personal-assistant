# src/core/books/note/note_record.py

from src.core.book import hidden_method
from src.core.record import Record


class NoteRecord(Record):
    # ---------- Static Methods ----------
    @staticmethod
    @hidden_method
    def get_record_fields () -> list:
        return ['title', 'body']

    @staticmethod
    @hidden_method
    def get_record_multi_value_fields () -> list[str]:
        return ['tag']

    @staticmethod
    @hidden_method
    def get_record_required_fields () -> list[str]:
        return ['title', 'body']

    # ---------- Utility ----------
    # def __str__ (self):
    #     return f'' # todo: implement
