# src/core/record.py
from abc import abstractmethod, ABC

from src.core.book import hidden_method


class Record(ABC):
    def __init__ (self, **kwargs):
        self.fields = {}
        self._multi_value_fields = {}

        valid_fields = self.get_record_fields()
        unsupported_fields = [key for key in kwargs if key not in valid_fields]

        if unsupported_fields:
            raise ValueError(f'Unsupported field(s): {', '.join(unsupported_fields)}')

        required_fields = self.get_record_required_fields()
        missing_required_fields = [
            field for field in required_fields
            if field not in kwargs or not kwargs[field]
        ]
        if missing_required_fields:
            raise ValueError(f'Missing required field(s): {', '.join(missing_required_fields)}')

        # initializing multi value fields
        for multi_value_field in self.get_record_multi_value_fields():
            if multi_value_field in kwargs:
                if not self._multi_value_fields.get(multi_value_field):
                    self._multi_value_fields[multi_value_field] = {kwargs[multi_value_field]: kwargs[multi_value_field]}
                else:
                    self._multi_value_fields[multi_value_field][kwargs[multi_value_field]] = kwargs[multi_value_field]

        for field in valid_fields:
            if field in kwargs:
                value = kwargs[field]

                # Try to find a validator like `validate_birthday`
                validator_method_name = f"validate_{field}"
                validator = getattr(self, validator_method_name, None)

                if callable(validator):
                    value = validator(value)

                setattr(self, field, value)  # setting values like this to trigger setters

    @staticmethod
    @hidden_method
    @abstractmethod
    def get_record_fields () -> list[str]:
        pass

    @staticmethod
    @hidden_method
    @abstractmethod
    def get_record_required_fields () -> list[str]:
        pass

    @staticmethod
    @hidden_method
    @abstractmethod
    def get_record_multi_value_fields () -> list[str]:
        pass

    def add_multi_value_field_entry (self, multi_field_name: str, value):
        self._init_multi_value_field(multi_field_name)
        self._multi_value_fields[multi_field_name].update({value: value})

    def update_multi_value_field_entry (self, multi_field_name: str, old_value, new_value):
        self._init_multi_value_field(multi_field_name)
        if old_value not in self._multi_value_fields[multi_field_name]:
            raise ValueError(f'Old value {old_value} not found in {multi_field_name}')

        self._multi_value_fields[multi_field_name][old_value] = new_value

    def delete_multi_value_field_entry (self, multi_field_name: str, value):
        self._init_multi_value_field(multi_field_name)

        if value not in self._multi_value_fields[multi_field_name]:
            raise ValueError(f'{value} not found in {multi_field_name}')

        self._multi_value_fields[multi_field_name].remove(value)

    def get_multi_value_field_entries (self, multi_field_name: str):
        self._init_multi_value_field(multi_field_name)

        return self._multi_value_fields[multi_field_name].copy()

    def _init_multi_value_field (self, multi_field_name: str):
        if multi_field_name not in self._multi_value_fields:
            self._multi_value_fields[multi_field_name] = []
