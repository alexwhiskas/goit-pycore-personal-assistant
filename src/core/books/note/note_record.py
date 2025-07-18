# src/core/books/note/note_record.py

from src.core.decorators import hidden_method
from src.core.record import Record


class NoteRecord(Record):
    # ---------- Static Methods ----------
    @classmethod
    @hidden_method
    def get_record_fields (cls) -> list:
        return ['title', 'body']

    @classmethod
    @hidden_method
    def get_record_multi_value_fields (cls) -> list[str]:
        return ['tag']

    @classmethod
    @hidden_method
    def get_record_required_fields (cls) -> list[str]:
        return ['title', 'body']
