# src/core/books/contact/contact_record.py

from src.core.decorators import hidden_method

from src.core.record import Record
import re
from datetime import datetime


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

    @classmethod
    @hidden_method
    def get_record_fields (cls) -> list[str]:
        return ['firstname', 'lastname']

    @classmethod
    @hidden_method
    def get_record_fields_to_validate (cls) -> list[str]:
        return ['email', 'birthday', 'phone_number']

    # ---------- Validation Helpers ----------
    @classmethod
    @hidden_method
    def validate_email (cls, email):
        email = email.strip()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if re.match(pattern, email):
            return email  # returning email if it's valid
        else:
            raise ValueError('Please use correct email format: email@domain.com')

    @classmethod
    @hidden_method
    def validate_birthday (cls, birthday):
        try:
            parsed_date = datetime.strptime(birthday.strip(), '%Y-%m-%d')
            return parsed_date.date()  # returning parsed date
        except ValueError:
            raise ValueError('Please use correct date format: %Y-%m-%d')

    @classmethod
    @hidden_method
    def validate_phone_number (cls, phone_number):
        clean_from_space = phone_number.strip()
        clean_from_symbol = re.sub(r'\D', '', clean_from_space)  # leaving only digits
        clean_numbers = None

        if clean_from_symbol.startswith('38'):
            clean_numbers = clean_from_symbol
        elif clean_from_symbol.startswith('0'):
            clean_numbers = '38' + clean_from_symbol
        elif clean_from_symbol.startswith('380'):
            clean_numbers = clean_from_symbol

        # supported phone number format is: 380XXYYYYYYY — so, checking if it consists of 12 digits
        if clean_numbers is None or len(clean_numbers) != 12:
            raise ValueError("Please use phone number which has 12 digits in total and start with '38'")

        return clean_numbers # returning phone number with only digits for easier search operations
