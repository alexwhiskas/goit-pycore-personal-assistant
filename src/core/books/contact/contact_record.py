# src/core/books/contact/contact_record.py

from src.core.book import hidden_method
from src.core.record import Record


class ContactRecord(Record):
    # ---------- Static Methods ----------
    @staticmethod
    @hidden_method
    def get_record_fields () -> list:
        return ['firstname', 'lastname', 'address', 'email', 'birthday']

    @staticmethod
    @hidden_method
    def get_record_multi_value_fields () -> list[str]:
        return ['phone_number']

    @staticmethod
    @hidden_method
    def get_record_required_fields () -> list[str]:
        return ['firstname', 'lastname']

    # ---------- Validation Helpers ----------
    def validate_email (self, email):
        return True  # todo: add email validation here, raise error in case of wrong value

    def validate_birthday (self, birthday):
        return True  # todo: add birthday validation here, raise error in case of wrong value

    def validate_phone_number (self, phone_number):
        return True  # todo: add phone number validation here, raise error in case of wrong value

    # ---------- Utility ----------
    # def __str__ (self):
    #     return f'' # todo: implement
