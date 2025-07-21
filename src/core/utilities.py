# src/core/utilities.py

def dict_to_string (data: dict, separator: str = ", ") -> str:
    return separator.join(f'{k} = {v}' for k, v in data.items())
