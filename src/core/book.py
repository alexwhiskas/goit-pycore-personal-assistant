# src/core/book.py

from abc import ABC, abstractmethod
from typing import Any
from importlib import util
import inspect
import pickle
from pathlib import Path


def method_args_as_command_params (func):
    func._method_args_as_command_params = True
    return func

def hidden_method (func):
    func._hidden = True
    return func


class Book(ABC):
    PARAM_SEARCH_PREFIX = 'search'
    PARAM_UPDATE_PREFIX = 'update'

    PARAM_MULTI_VALUE_TO_SEARCH_PREFIX = 'old'
    PARAM_MULTI_VALUE_TO_UPDATE_PREFIX = 'new'

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

    def __init__ (self):
        self.records = []

    @abstractmethod
    def get_book_name (self) -> str:
        # children classes must return the book's short name (e.g. 'contact', 'note')
        pass

    def add_record(self, **kwargs) -> None:
        record_class = self.get_record_class()
        self.records.append(record_class(**kwargs))

    # def update_records (self, conditions: dict) -> int:
    def delete_records (self, **kwargs) -> int:
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
        to_delete = [record for record in self.records if self._matches_conditions(record, conditions)]

        # todo: add here prompt, list found records and ask to submit delete operation
        for record in to_delete:
            self.records.remove(record)

        # returns amount of deleted records
        return len(to_delete)

    # def update_records (self, conditions: dict) -> list:
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

        # returns a list of all records that match the conditions
        found_records = [record for record in self.records if self._matches_conditions(record, conditions)]

        # todo: maybe output here the list of found records info and return True?
        return found_records

    # def update_records (self, conditions: dict, fields_to_update: dict[str, str]) -> list:
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

        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_search_prefix()):
                conditions[arg_key.replace(Book.get_search_prefix() + '_', '')] = arg_value
                continue
            elif arg_key.startswith(Book.get_update_prefix()):
                fields_to_update[arg_key.replace(Book.get_update_prefix() + '_', '')] = arg_value

        # returns a list of all records that match the conditions
        updated_records = []

        for record in self.records:
            if self._matches_conditions(record, conditions):
                for field, value in fields_to_update:
                    setattr(record, field, value)
                updated_records.append(record)

        # todo: maybe output here the list of updated records info and return True?
        return updated_records

    @hidden_method
    def get_record_class (self):
        # getting current file path of our Book class
        book_file = Path(inspect.getfile(self.__class__))
        book_name = self.__class__.__name__  # e.g., ContactBook

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

    @hidden_method
    def get_record_class_fields (self):
        record_class = self.get_record_class()
        return record_class.get_record_fields()

    @hidden_method
    def get_record_multi_value_fields (self):
        record_class = self.get_record_class()
        return record_class.get_record_multi_value_fields()

    # todo: point of extension for autocomplete search by conditions
    def _matches_conditions (self, record, conditions: dict) -> bool:
        # checks whether a record matches all given field-value pairs
        for field, expected_value in conditions.items():
            if not hasattr(record, field) or getattr(record, field) != expected_value:
                return False

        return True
