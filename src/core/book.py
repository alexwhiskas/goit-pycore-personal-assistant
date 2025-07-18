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
    def get_record_class_fields (cls):
        record_class = cls.get_record_class()
        return record_class.get_record_fields()

    @classmethod
    def get_record_multi_value_fields (cls):
        record_class = cls.get_record_class()
        return record_class.get_record_multi_value_fields()

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

    def add_record(self, **kwargs) -> list[Record]:
        record_class = self.get_record_class()
        record_object = record_class(**kwargs)
        self.records.append(record_object)

        return [record_object]

    def delete_records (self, **kwargs) -> list[Record]:
        """
        Example of 'conditions' param:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """
        conditions = {}

        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_search_prefix()):
                conditions[arg_key.replace(Book.get_search_prefix() + '_', '')] = arg_value
                continue

        # looks for matching records and deletes them
        records_to_delete = [record for record in self.records if self._matches_conditions(record, conditions)]

        # todo: add here prompt, list found records and ask to submit delete operation
        for record_to_delete in records_to_delete:
            self.records.remove(record_to_delete)

        # returns amount of deleted records
        return records_to_delete

    def get_records (self, **kwargs) -> list:
        """
        Example of 'conditions' param:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """
        conditions = {}
        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_search_prefix()):
                conditions[arg_key.replace(Book.get_search_prefix() + '_', '')] = arg_value
                continue
            if arg_key.startswith(Book.get_multi_value_to_search_prefix()):
                conditions[arg_key.replace(Book.get_multi_value_to_search_prefix() + '_', '')] = arg_value
                continue

        # returns a list of all records that match the conditions
        found_records = [record for record in self.records if self._matches_conditions(record, conditions)]

        return found_records

    def update_records (self, **kwargs) -> list:
        """
        Example of 'conditions' and 'fields_to_update' vars contents:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """
        conditions = {}
        fields_to_update = {}
        multi_field_values_to_update = {}
        multi_field_values_to_delete = {}
        multi_values_fields = self.get_record_multi_value_fields()

        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_search_prefix()):
                conditions[arg_key.replace(Book.get_search_prefix() + '_', '')] = arg_value
                continue
            elif arg_key.startswith(Book.get_update_prefix()):
                fields_to_update[arg_key.replace(Book.get_update_prefix() + '_', '')] = arg_value
            elif arg_key.startswith(Book.get_multi_value_to_search_prefix()):
                multi_value_field_name = arg_key.replace(Book.get_multi_value_to_search_prefix() + '_', '')
                multi_value_field_value_to_update_arg = Book.get_multi_value_to_update_prefix() + '_' + multi_value_field_name

                if multi_value_field_value_to_update_arg in kwargs:
                    value_to_replace_by = kwargs[multi_value_field_value_to_update_arg]
                    multi_field_values_to_update.setdefault(multi_value_field_name, {})[arg_value] = value_to_replace_by
                else:
                    raise ValueError('You didn\'t provided value to update/insert for multi value field: ' + multi_value_field_name)
            elif arg_key.startswith(Book.get_multi_value_to_delete_prefix()):
                multi_value_field_name = arg_key.replace(Book.get_multi_value_to_delete_prefix() + '_', '')
                multi_field_values_to_delete.setdefault(multi_value_field_name, {})[arg_value] = arg_value
            elif arg_key in multi_values_fields:
                multi_field_values_to_update.setdefault(arg_key, {})[''] = arg_value

        # returns a list of all records that match the conditions
        updated_records = []
        for record in self.records:
            if self._matches_conditions(record, conditions):
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

                updated_records.append(record)

        return updated_records

    # todo: point of extension for autocomplete search by conditions
    def _matches_conditions (self, record, conditions: dict) -> bool:
        multi_value_fields = self.get_record_multi_value_fields()
        multi_value_fields_entries = record.multi_value_fields

        # checks whether a record matches all given field-value pairs
        for field, expected_value in conditions.items():
            if field in multi_value_fields:
                if expected_value not in multi_value_fields_entries.setdefault(field, {}):
                    return False
            elif not record.fields.get(field) or record.fields.get(field) != expected_value:
                return False

        return True
