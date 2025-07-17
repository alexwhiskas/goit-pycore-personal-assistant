# src/core/books/contact/contact_record.py

from src.core.book import hidden_method
from src.core.record import Record
import re
from datetime import datetime


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
        email = email.strip()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return email  # Повертаємо очищений email, якщо він валідний
        else:
            return None  # Повертаємо None, якщо невалідний


    def validate_birthday (self, birthday):
        try:
            parsed_date = datetime.strptime(birthday.strip(), "%Y-%m-%d")
            return parsed_date.date()  # Повертаємо дату
        except ValueError:
            return None  # Якщо не вдалося розпарсити

    def validate_phone_number (self, phone_number):
        clean_from_space = phone_number.strip()
        clean_from_symbol = re.sub(r'\D', '', clean_from_space)  # Залишаємо лише цифри

        if clean_from_symbol.startswith('38'):
            clean_numbers = clean_from_symbol
        elif clean_from_symbol.startswith('0'):
            clean_numbers = '38' + clean_from_symbol
        elif clean_from_symbol.startswith('380'):
            clean_numbers = clean_from_symbol
        else:
            return None  # Якщо формат зовсім інший — пропускаємо

        # Очікуємо формат: 380XXYYYYYYY — перевіримо, чи 12 цифр
        if len(clean_numbers) != 12:
            return None

        # Розбиваємо на частини
        country = '+38'
        operator = clean_numbers[2:5]
        first = clean_numbers[5:8]
        second = clean_numbers[8:10]
        third = clean_numbers[10:12]

        return f"{country}({operator}){first}-{second}-{third}" # Повертаємо адекватний номер 

    # ---------- Utility ----------
    # def __str__ (self):
    #     return f'' # todo: implement
