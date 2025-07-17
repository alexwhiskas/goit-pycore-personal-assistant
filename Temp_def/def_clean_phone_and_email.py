import re
# Функція перевірки формату телефону
def normalize_phone(phone_number: str):
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

    return f"{country}({operator}){first}-{second}-{third}"

# Функція перевірки формату имейл
def is_valid_email(email: str):
    email = email.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return email  # Повертаємо очищений email, якщо він валідний
    else:
        return None  # Повертаємо None, якщо невалідний


# Тест перевірки формату имейл
raw_emails = [
    " test.user@example.com ",
    "admin@my-site.org",
    "user.name+tag+sorting@gmail.com",
    "zhakun@uhp.kharkov.ua",
    "invalidemail@.com",
    "validemail@hh.com",
    "just_text",
    "another.test@domain",
    "email@domain.com",
    "bad@email@double.com",
    "correct123@mail.co",
]


valid_emails = [email.strip() for email in raw_emails if is_valid_email(email)]
print("Валідні email-адреси:")
for email in valid_emails:
    print(email)

# Тест перевірки формату телефона
raw_numbers = [
    "067\\t123 4567",
    "(095) 234-5678\\n",
    "+380 44 123 4567",
    "380501234567",
    "    +38(050)123-32-34",
    "     0503451234",
    "(050)8889900",
    "38050-111-22-22",
    "38050 111 22 11   ",
]

sanitized_numbers = [normalize_phone(num) for num in raw_numbers if normalize_phone(num)]
print("Нормалізовані номери телефонів для SMS-розсилки:")
for number in sanitized_numbers:
    print(number)