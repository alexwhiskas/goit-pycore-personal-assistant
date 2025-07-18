# src/core/books/contact/contact_record.py

from src.core.decorators import hidden_method

from src.core.record import Record


class ContactRecord(Record):
    # ---------- Static Methods ----------
    @classmethod
    @hidden_method
    def get_record_fields (cls) -> list:
        return ['firstname', 'lastname', 'address', 'email', 'birthday']

    @classmethod
    @hidden_method
    def get_record_multi_value_fields (cls) -> list[str]:
        return ['phone_number']

    @classmethod
    @hidden_method
    def get_record_required_fields (cls) -> list[str]:
        return ['firstname', 'lastname']

    # ---------- Validation Helpers ----------
    def validate_email (self, email):
        return email  # todo: add email validation here, raise error in case of wrong value

    def validate_birthday (self, birthday):
        return birthday  # todo: add birthday validation here, raise error in case of wrong value

    def validate_phone_number (self, phone_number):
        return phone_number  # todo: add phone number validation here, raise error in case of wrong value
