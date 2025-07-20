# src/core/book.py

from abc import ABC, abstractmethod
from typing import Any
from importlib import util
import inspect
import pickle
from pathlib import Path

from src.core.record import Record


class Book(ABC):
    PARAM_SEARCH_PREFIX = 'search_by'
    PARAM_UPDATE_PREFIX = 'update'

    PARAM_MULTI_VALUE_TO_SEARCH_PREFIX = 'old'
    PARAM_MULTI_VALUE_TO_UPDATE_PREFIX = 'new'
    PARAM_MULTI_VALUE_TO_DELETE_PREFIX = 'delete'

    RETURN_RESULT_NEW = 'added'
    RETURN_RESULT_FOUND = 'found'
    RETURN_RESULT_NOT_FOUND = 'not-found'
    RETURN_RESULT_DUPLICATE = 'duplicate'
    RETURN_RESULT_UPDATED = 'updated'
    RETURN_RESULT_UPDATE_CAUSES_DUPLICATE = 'update-causes-duplicate'
    RETURN_RESULT_NOT_UPDATED = 'not-updated'
    RETURN_RESULT_DELETED = 'deleted'
    RETURN_RESULT_NOT_DELETED = 'not-deleted'

    @classmethod
    def get_search_prefix (cls):
        return cls.PARAM_SEARCH_PREFIX

    @classmethod
    def get_update_prefix (cls):
        return cls.PARAM_UPDATE_PREFIX

    @classmethod
    def get_multi_value_to_search_prefix (cls):
        return cls.PARAM_MULTI_VALUE_TO_SEARCH_PREFIX

    @classmethod
    def get_multi_value_to_update_prefix (cls):
        return cls.PARAM_MULTI_VALUE_TO_UPDATE_PREFIX

    @classmethod
    def get_multi_value_to_delete_prefix (cls):
        return cls.PARAM_MULTI_VALUE_TO_DELETE_PREFIX

    @classmethod
    def get_record_class (cls):
        # getting current file path of our Book class
        book_file = Path(inspect.getfile(cls))
        book_name = cls.__name__  # e.g., ContactBook

        # computing expected file and class name
        record_file = book_file.with_name(
            book_file.name.replace('book', 'record')
        )  # e.g. replacing contact_book with contact_record
        record_class_name = book_name.replace('Book', 'Record')  # e.g. replacing ContactBook with ContactRecord

        # dynamically importing module from record file path
        module_name = f"{record_file.stem}"  # unique temp name
        spec = util.spec_from_file_location(module_name, str(record_file))
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # getting and returning the record class
        record_class = getattr(module, record_class_name)
        return record_class

    def __init__ (self):
        self.records = []

    @abstractmethod
    def get_book_name (self) -> str:
        # children classes must return the book's short name (e.g. 'contact', 'note')
        pass

    def add_record(self, **kwargs) -> tuple[str, list[Record], dict[str, str]]:
        record_class = self.get_record_class()

        result_code, found_duplicate, conditions = self.get_records(False, **kwargs)
        if result_code == self.RETURN_RESULT_FOUND:
            return self.RETURN_RESULT_DUPLICATE, found_duplicate, conditions

        record_object = record_class(**kwargs)
        self.records.append(record_object)

        return self.RETURN_RESULT_NEW, [record_object], {}

    def get_records (self, need_to_check_suffix: bool = True, **kwargs) -> tuple[str, list[Record], dict[str, str]]:
        """
        Example of 'conditions' param:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """
        conditions = {
            **self._parse_fields_conditions_from_kwargs(need_to_check_suffix, **kwargs),
            **self._parse_multi_value_fields_from_kwargs(False, **kwargs)
        }

        print(conditions)
        # returns a list of all records that match the conditions
        found_records = [record for record in self.records if self._matches_conditions(record, conditions)]

        if not found_records:
            return self.RETURN_RESULT_NOT_FOUND, [], conditions

        return self.RETURN_RESULT_FOUND, found_records, conditions

    def update_records (self, **kwargs) -> tuple[str, list[Record], dict[str, str]]:
        """
        Example of 'conditions' and 'fields_to_update' vars contents:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """

        # returns a list of all records that match the conditions
        result_code, records_to_update, conditions = self.get_records(**kwargs)
        fields_to_update = self._parse_fields_to_update_from_kwargs(**kwargs)
        multi_field_values_to_update = self._parse_multi_value_fields_from_kwargs(True, **kwargs)
        multi_field_values_to_delete = self._parse_multi_value_fields_to_delete_from_kwargs(**kwargs)

        if result_code == self.RETURN_RESULT_NOT_FOUND:
            return self.RETURN_RESULT_NOT_UPDATED, self.records, conditions

        for record in records_to_update:
            for field, value in fields_to_update.items():
                record.fields[field] = value

            for multi_value_field_name, multi_field_values in multi_field_values_to_update.items():
                for multi_value_field_value_to_replace, new_multi_value_field_value in multi_field_values.items():
                    if multi_value_field_value_to_replace == '':
                        multi_value_field_value_to_replace = new_multi_value_field_value

                    record.multi_value_fields.setdefault(multi_value_field_name, {}).pop(multi_value_field_value_to_replace, None)
                    record.multi_value_fields[multi_value_field_name][new_multi_value_field_value] = new_multi_value_field_value

            for multi_value_field_name_to_delete, multi_field_values_to_delete in multi_field_values_to_delete.items():
                for multi_value_field_value_to_delete in multi_field_values_to_delete:
                    record.multi_value_fields.setdefault(multi_value_field_name_to_delete, {}).pop(multi_value_field_value_to_delete, None)

        return self.RETURN_RESULT_UPDATED, records_to_update, conditions

    def _parse_fields_conditions_from_kwargs(self, need_to_check_suffix: bool, **kwargs):
        conditions = {}
        record_required_fields = self.get_record_class().get_record_required_fields()

        for arg_key, arg_value in kwargs.items():
            if (not need_to_check_suffix and arg_key in record_required_fields) or (arg_key.startswith(Book.get_search_prefix()) and arg_value):
                conditions[arg_key.replace(Book.get_search_prefix() + '_', '')] = arg_value

        return conditions

    def _parse_fields_to_update_from_kwargs(self, **kwargs):
        fields_to_update = {}

        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_update_prefix()) and arg_value:
                fields_to_update[arg_key.replace(Book.get_update_prefix() + '_', '')] = arg_value

        return fields_to_update

    def _parse_multi_value_fields_from_kwargs(self, update_operation: bool, **kwargs):
        multi_field_values = {}

        print(kwargs)
        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_multi_value_to_search_prefix()) and arg_value:
                if not arg_value and not update_operation:
                    continue

                multi_value_field_name = arg_key.replace(Book.get_multi_value_to_search_prefix() + '_', '')
                multi_value_field_value_to_update_arg = Book.get_multi_value_to_update_prefix() + '_' + multi_value_field_name
                print(multi_value_field_value_to_update_arg)

                if update_operation:
                    value_to_replace_by = kwargs.get(multi_value_field_value_to_update_arg)

                    if not value_to_replace_by:
                        raise ValueError(f'You didn\'t provided value to update/insert for multi value field: ' + multi_value_field_name)
                    else:
                        multi_field_values.setdefault(multi_value_field_name, {})[arg_value] = value_to_replace_by
                else:
                    multi_field_values[multi_value_field_name] = arg_value
                    continue

        return multi_field_values

    def _parse_multi_value_fields_to_delete_from_kwargs(self, **kwargs):
        multi_field_values_to_delete = {}

        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_multi_value_to_delete_prefix()) and arg_value:
                multi_value_field_name = arg_key.replace(Book.get_multi_value_to_delete_prefix() + '_', '')
                multi_field_values_to_delete.setdefault(multi_value_field_name, {})[arg_value] = arg_value

        return multi_field_values_to_delete

    def delete_records (self, **kwargs) -> tuple[str, list[Record], dict[str, str]]:
        """
        Example of 'conditions' param:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """
        result_code, records_to_delete, conditions = self.get_records(**kwargs)

        if result_code == self.RETURN_RESULT_NOT_FOUND:
            return self.RETURN_RESULT_NOT_DELETED, self.records, conditions

        for record_to_delete in records_to_delete:
            self.records.remove(record_to_delete)

        # returns deleted records
        return self.RETURN_RESULT_DELETED, records_to_delete, {}

    def _matches_conditions (self, record, conditions: dict) -> bool:
        multi_value_fields = self.get_record_class().get_record_multi_value_fields()
        multi_value_fields_entries = record.multi_value_fields

        for field, expected_value in conditions.items():
            # forcing everything to lower case
            expected_value_lower = str(expected_value).lower()

            if field in multi_value_fields:
                actual_values = multi_value_fields_entries.get(field, {}).keys()
                actual_values_lower = [str(v).lower() for v in actual_values]
                if expected_value_lower not in actual_values_lower:
                    return False
            else:
                actual_value = record.fields.get(field)
                if str(actual_value).lower() != expected_value_lower:
                    return False

        return True
