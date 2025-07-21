# src/core/book.py

from abc import ABC, abstractmethod
from collections import UserDict

import questionary

from src.core.decorators import method_for_bot_interface
from src.core.fast_search_adapter import FastSearchAdapter
from src.core.record import Record
from src.core.utilities import dict_to_string

RETURN_RESULT_NEW = 'added'
RETURN_RESULT_FOUND = 'found'
RETURN_RESULT_NOT_FOUND = 'not-found'
RETURN_RESULT_DUPLICATE = 'duplicate'
RETURN_RESULT_UPDATED = 'updated'
RETURN_RESULT_UPDATE_CAUSES_DUPLICATE = 'update-causes-duplicate'
RETURN_RESULT_NOT_UPDATED = 'not-updated'
RETURN_RESULT_DELETED = 'deleted'
RETURN_RESULT_NOT_DELETED = 'not-deleted'

class Book(ABC, UserDict[str, Record]):
    PARAM_SEARCH_PREFIX = 'search_by'
    PARAM_UPDATE_PREFIX = 'update'

    PARAM_MULTI_VALUE_TO_SEARCH_PREFIX = 'old'
    PARAM_MULTI_VALUE_TO_UPDATE_PREFIX = 'new'
    PARAM_MULTI_VALUE_TO_DELETE_PREFIX = 'delete'

    fast_search = FastSearchAdapter.get_instance()

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
    @abstractmethod
    def get_record_class (cls):
        pass

    @abstractmethod
    def get_book_name (self) -> str:
        # children classes must return the book's short name (e.g. 'contact', 'note')
        pass

    @method_for_bot_interface
    def add_record (self, **kwargs) -> tuple[str, list[Record], dict[str, str]]:
        record_class = self.get_record_class()

        result_code, found_duplicate, conditions = self.get_records(False, True, **kwargs)
        if result_code == RETURN_RESULT_FOUND:
            return RETURN_RESULT_DUPLICATE, found_duplicate, conditions

        record_object = record_class(**kwargs)
        self.data[record_object.record_as_option()] = record_object

        # Index the new record for searching
        self.fast_search.index_record(self.get_book_name(), record_object)

        return RETURN_RESULT_NEW, [record_object], {}

    @method_for_bot_interface
    def get_records (self, need_to_check_suffix: bool = True, for_update_operations: bool = False, **kwargs) -> tuple[
        str, list[Record], dict[str, str]]:
        """
        Example of 'conditions' param:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """
        conditions = {
            **self._parse_fields_conditions_from_kwargs(need_to_check_suffix, **kwargs),
            **self._parse_multi_value_fields_from_kwargs(need_to_check_suffix, for_update_operations, **kwargs)
        }

        # returns a list of all records that match the conditions
        found_records = [record for record in self.data.values() if self._matches_conditions(record, conditions)]

        if not found_records:
            if not for_update_operations:
                suggest_option = "try to search"

                suggest_search_answer = "try to search"
                # suggest_search_answer = questionary.select(
                #     f"Couldn't find any matches for following conditions: {dict_to_string(conditions)}. Want to try to perform search? ",
                #     ["no, go back", suggest_option],
                # ).ask()

                if suggest_search_answer == suggest_option:
                    return self.search_records(conditions)
            else:
                return RETURN_RESULT_NOT_FOUND, [], conditions

        return RETURN_RESULT_FOUND, found_records, conditions

    def search_records(self, query: str | dict[str, str]) -> tuple[str, list[Record], dict[str, str]]:
        """Search records using full-text search"""
        if not query:
            return RETURN_RESULT_NOT_FOUND, [], {}

        # Validate minimum search length if string query
        min_length = FastSearchAdapter.MIN_SEARCH_LENGTH
        if isinstance(query, str) and len(query) < min_length:
            raise ValueError(f"Search query must be at least {min_length} characters long")

        # Use fast search with query
        try:
            result_dicts = self.fast_search.search_records(
                self.get_book_name(),
                query,
                None,  # No filters
                100    # Limit to 100 results
            )

            if not result_dicts:
                return RETURN_RESULT_NOT_FOUND, [], {"query": query}

            # Map results back to actual record objects
            found_records = []
            for result in result_dicts:
                record_id = result.get("id")

                # Find matching record by ID or key fields
                record_found = False
                for record in self.data.values():
                    # Try matching by ID first
                    rec_id = record.fields.get("id") or record.record_as_option()
                    if str(rec_id) == str(record_id):
                        found_records.append(record)
                        record_found = True
                        # Ensure ID is consistent
                        if "id" not in record.fields:
                            record.fields["id"] = str(rec_id)
                        break

                # If we couldn't find by ID, try matching on key fields
                if not record_found:
                    for record in self.data.values():
                        # Compare required fields
                        matches = True
                        required_fields = self.get_record_class().get_record_required_fields()
                        for field in required_fields:
                            if field in result and field in record.fields:
                                if str(record.fields[field]) != str(result[field]):
                                    matches = False
                                    break
                        if matches:
                            found_records.append(record)
                            # Update the ID for future searches
                            record.fields['id'] = record_id
                            # Also update the search index with this record to maintain consistency
                            self.fast_search.update_record(self.get_book_name(), record)
                            break

            # Remove duplicates
            unique_records = []
            seen_ids = set()
            for record in found_records:
                rec_id = record.fields.get("id") or record.record_as_option()

                if str(rec_id) not in seen_ids:
                    seen_ids.add(str(rec_id))
                    unique_records.append(record)

            return RETURN_RESULT_FOUND, unique_records, {"query": query}
        except ValueError as e:
            # Re-raise with the same message
            raise ValueError(str(e))

    @method_for_bot_interface
    def update_records (self, emulation = False, need_to_check_suffix = True, **kwargs) -> tuple[str, list[Record], dict[str, str]]:
        """
        Example of 'conditions' and 'fields_to_update' vars contents:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """

        # returns a list of all records that match the conditions
        result_code, records_to_update, conditions = self.get_records(need_to_check_suffix, True, **kwargs)

        if result_code == RETURN_RESULT_NOT_FOUND:
            return RETURN_RESULT_NOT_UPDATED, list(self.data.values()), conditions

        fields_to_update = self._parse_fields_to_update_from_kwargs(emulation, **kwargs)
        multi_field_values_to_update = self._parse_multi_value_fields_from_kwargs(False, False, emulation, **kwargs)
        multi_field_values_to_delete = self._parse_multi_value_fields_to_delete_from_kwargs(**kwargs)

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

            # Update the search index with the modified record
            self.fast_search.update_record(self.get_book_name(), record)

        return RETURN_RESULT_UPDATED, records_to_update, conditions

    def _parse_fields_conditions_from_kwargs (self, need_to_check_suffix: bool, **kwargs):
        conditions = {}
        record_required_fields = self.get_record_class().get_record_required_fields()

        for arg_key, arg_value in kwargs.items():
            if (
                    (not need_to_check_suffix and arg_key in record_required_fields)
                    or (arg_key.startswith(Book.get_search_prefix()) and arg_value)
            ):
                conditions[arg_key.replace(Book.get_search_prefix() + '_', '')] = arg_value

        return conditions

    def _parse_fields_to_update_from_kwargs (self, emulation = False, **kwargs):
        fields_to_update = {}

        for arg_key, arg_value in kwargs.items():
            if arg_key not in self.get_record_class().get_record_multi_value_fields():
                if emulation:
                    fields_to_update[arg_key] = arg_value
                elif arg_key.startswith(Book.get_update_prefix()) and arg_value:
                    fields_to_update[arg_key.replace(Book.get_update_prefix() + '_', '')] = arg_value

        return fields_to_update

    def _parse_multi_value_fields_from_kwargs (self, need_to_check_suffix: bool = True, for_update_operation: bool = False, for_emulation = False, **kwargs):
        multi_field_values = {}

        if for_update_operation and not for_emulation:
            return {}

        multi_value_fields = self.get_record_class().get_record_multi_value_fields()

        for multi_value_field_name in multi_value_fields:
            if for_emulation:
                multi_value_field_value_to_update_with_arg = multi_value_field_name
            else:
                multi_value_field_value_to_update_with_arg = Book.get_multi_value_to_update_prefix() + '_' + multi_value_field_name

            multi_value_field_value_to_search_by_arg = (Book.get_search_prefix() if need_to_check_suffix else Book.get_multi_value_to_search_prefix()) + '_' + multi_value_field_name
            new_value = kwargs.get(multi_value_field_value_to_update_with_arg) or ""
            old_value = kwargs.get(multi_value_field_value_to_search_by_arg) or ""

            if old_value:
                if need_to_check_suffix:
                    multi_field_values.setdefault(multi_value_field_name, {})[old_value] = new_value
                else:
                    multi_field_values.setdefault(multi_value_field_name, {})[old_value] = old_value
            elif new_value:
                multi_field_values.setdefault(multi_value_field_name, {})[new_value] = new_value

        return multi_field_values

    def _parse_multi_value_fields_to_delete_from_kwargs (self, **kwargs):
        multi_field_values_to_delete = {}

        for arg_key, arg_value in kwargs.items():
            if arg_key.startswith(Book.get_multi_value_to_delete_prefix()) and arg_value:
                multi_value_field_name = arg_key.replace(Book.get_multi_value_to_delete_prefix() + '_', '')
                multi_field_values_to_delete.setdefault(multi_value_field_name, {})[arg_value] = arg_value

        return multi_field_values_to_delete

    @method_for_bot_interface
    def delete_records (self, **kwargs) -> tuple[str, list[Record], dict[str, str]]:
        """
        Example of 'conditions' param:
        conditions = {
            "firstname": "Alice",
            "lastname": "Smith"
        }
        """
        result_code, records_to_delete, conditions = self.get_records(**kwargs)

        if result_code == RETURN_RESULT_NOT_FOUND:
            return RETURN_RESULT_NOT_DELETED, list(self.data.values()), conditions

        for record_to_delete in records_to_delete:
            # Remove from search index first
            record_id = record_to_delete.fields.get("id") or record_to_delete.record_as_option()
            self.fast_search.delete_record(self.get_book_name(), str(record_id))
            # Then remove from data
            record_to_delete_key = record_to_delete.record_as_option()
            if record_to_delete_key in self.data:
                del self.data[record_to_delete.record_as_option()]

        # returns deleted records
        return RETURN_RESULT_DELETED, records_to_delete, {}

    def _matches_conditions (self, record, conditions: dict) -> bool:
        multi_value_fields = self.get_record_class().get_record_multi_value_fields()
        multi_value_fields_entries = record.multi_value_fields

        for field, expected_value in conditions.items():
            # forcing everything to lower case

            if field in multi_value_fields:
                expected_values = expected_value
                if isinstance(expected_values, str):
                    expected_values = [expected_value]

                actual_values = multi_value_fields_entries.get(field, {}).keys()
                actual_values_lower = str([str(v).lower() for v in actual_values])
                for expected_value_entry in expected_values:
                    expected_value_entry_lower = expected_value_entry.lower()
                    if expected_value_entry_lower not in actual_values_lower:
                        return False
            else:
                expected_value_lower = str(expected_value).lower()
                actual_value = record.fields.get(field)
                if str(actual_value).lower() != expected_value_lower:
                    return False

        return True
