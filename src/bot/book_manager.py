# src/bot/book_manager.py

import importlib
import inspect
import pickle
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict

import questionary

from src.core.book import Book


class BookManager:
    EXIT_OPERATION = 'exit'
    PREV_OPERATION = 'prev'

    books: Dict[str, Book] = {}

    def __init__ (self):
        self.books = {}
        self.supported_operations_per_book = {}
        self._load_books()
        self._load_supported_operations_per_book()

    def end (self):
        self.animate_process_func('Saving books info. Finishing process')
        self.save_books_state()
        exit()

    def start (self, book_selection_prompt):
        supported_books = list(self.supported_operations_per_book.keys())

        while True:
            customer_input = questionary.select(
                book_selection_prompt,
                choices=supported_books + [self.EXIT_OPERATION],
            ).ask()

            if customer_input == self.EXIT_OPERATION:
                self.end()
                break
            else:
                result = self.continue_with_book_operations(customer_input)

                if result:
                    self.start('Please, select a book you would like to work with:')
                elif result == self.PREV_OPERATION:
                    continue
                elif result == self.EXIT_OPERATION:
                    self.end()

    def continue_with_book_operations (self, book_name):
        supported_operations = self.supported_operations_per_book[book_name]
        supported_operations_keys = list(supported_operations.keys())
        book_operation_selection_prompt = f'Please, select operation you would like to perform on your {book_name} book:'
        process_management_commands = [self.EXIT_OPERATION, self.PREV_OPERATION]

        book = self.books.get(book_name)
        book_record = book.get_record_class()
        required_record_fields = book_record.get_record_required_fields()

        def run_operation_from_customer_input (user_operation_input: str = ''):
            while True:
                if user_operation_input == '':
                    user_operation_input = questionary.select(
                        book_operation_selection_prompt,
                        choices=supported_operations_keys + process_management_commands,
                    ).ask()

                if user_operation_input in supported_operations_keys:
                    requested_operation_params = supported_operations[user_operation_input].copy()
                    operation_params = {}

                    prompt_for_command_params = f'Please define requested params below, leave empty if not required and you don\'t want to use it: '
                    print(prompt_for_command_params)

                    while requested_operation_params:
                        key, value = next(iter(requested_operation_params.items()))

                        key_label = key.replace('_', ' ').capitalize()
                        # todo: implement variation of list of required fields based on user operation input
                        key_label_prompt = f'Enter {'required' if key in required_record_fields else 'optional'} value for {key_label}: '
                        user_input = input(key_label_prompt).strip()
                        # todo: add validation here based on field name and Record validate_* methods

                        def check_input_for_required_field (required_field_input_value: str = ''):
                            if not required_field_input_value and key in required_record_fields:
                                required_field_input_value = input(
                                    'This is a required field, you will be returned to previous step if you won\'t define value for ' + (
                                            key_label[0].lower() + key_label[1:]) + ': '
                                ).strip()

                                if required_field_input_value == '':
                                    prev_operation_option = 'go to previous step'
                                    define_value_again_option = 'try to define value again'

                                    # # used for testing purposes start
                                    # # prev_operation_or_define_required_field_value_answer = prev_operation_option
                                    # prev_operation_or_define_required_field_value_answer = define_value_again_option
                                    # # used for testing purposes end

                                    prev_operation_or_define_required_field_value_answer = questionary.select(
                                        'Want to go to prev operation or try to define new value again?',
                                        choices=[prev_operation_option, define_value_again_option],
                                    ).ask()

                                    if prev_operation_or_define_required_field_value_answer == define_value_again_option:
                                        return check_input_for_required_field(required_field_input_value)
                                    else:
                                        return self.PREV_OPERATION

                            return required_field_input_value

                        field_input_value = check_input_for_required_field(user_input)

                        if field_input_value == self.PREV_OPERATION:
                            return field_input_value
                        else:
                            operation_params[key] = field_input_value
                            del requested_operation_params[key]

                    command_execution_result = self.run_command(user_operation_input, **operation_params)

                    if isinstance(command_execution_result, tuple) and len(command_execution_result) == 3:
                        result_code, result_records, conditions = command_execution_result

                        if result_code in [
                            book.RETURN_RESULT_NEW, book.RETURN_RESULT_UPDATED, book.RETURN_RESULT_DELETED,
                            book.RETURN_RESULT_FOUND
                        ]:
                            self.print_result_records(
                                f'As result of your inputs, following record(s) was {result_code}',
                                result_records
                            )
                        elif result_code == book.RETURN_RESULT_DUPLICATE:
                            self.print_result_records(
                                f'Your input created following conditions: {self._dict_to_string(conditions)}, and we found this record: ',
                                result_records
                            )

                            choice_add = 'add'
                            choice_update = 'update'

                            # # used for testing purposes start
                            # # user_preferred_record_operation = choice_add
                            # user_preferred_record_operation = choice_update
                            # # used for testing purposes end

                            user_preferred_record_operation = questionary.select(
                                'Do you want to update existing record or add a new one?',
                                choices=[choice_add, choice_update],
                            ).ask()

                            if user_preferred_record_operation == choice_add:
                                print(
                                    f'We\'ll re-start execution of current command. Please, update one of the following params to create new record when asked next time: '
                                    + self._dict_to_string(conditions)
                                )

                                return run_operation_from_customer_input(user_operation_input)
                            else:
                                book.update_records(**operation_params)
                        elif result_code == book.RETURN_RESULT_NOT_UPDATED:
                            print(
                                f'Couldn\'t find record to update with entered search params: ' + self._dict_to_string(
                                    conditions
                                )
                            )

                            choice_add = 'add new'
                            suggest_existing = 'suggest existing'

                            user_preferred_record_operation = questionary.select(
                                f'Do you want me to {suggest_existing} record or help you to add a new one?',
                                choices=[choice_add, suggest_existing],
                            ).ask()

                            if user_preferred_record_operation == choice_add:
                                book.add_record(**operation_params)
                                return self.PREV_OPERATION
                            elif user_preferred_record_operation == suggest_existing:
                                self.animate_process_func('Looking for records to suggest')
                                # perform here fuzzy search
                                return self.PREV_OPERATION
                        elif result_code == book.RETURN_RESULT_NOT_DELETED:
                            print(
                                f'Couldn\'t find record to delete with entered search params: ' + self._dict_to_string(
                                    conditions
                                )
                            )

                            go_back = 'go back'
                            suggest_existing = 'suggest existing'

                            user_preferred_record_operation = questionary.select(
                                f'Do you want me to {suggest_existing} record or {go_back} to previous step?',
                                choices=[go_back, suggest_existing],
                            ).ask()

                            if user_preferred_record_operation == go_back:
                                return self.PREV_OPERATION
                            elif user_preferred_record_operation == suggest_existing:
                                self.animate_process_func('Looking for records to suggest')
                                # perform here fuzzy search
                                return self.PREV_OPERATION

                    elif isinstance(command_execution_result, list):
                        self.print_result_records(
                            print(
                                f"Function '{user_operation_input} returned {len(command_execution_result)} record(s):"
                            ),
                            command_execution_result
                        )
                        command_execution_result = self.PREV_OPERATION
                elif user_operation_input in process_management_commands:
                    command_execution_result = user_operation_input
                else:
                    command_execution_result = self.PREV_OPERATION

                return command_execution_result

        return run_operation_from_customer_input()

    def animate_process_func (self, animation_command):
        print(f'\n{animation_command}...')

        for i in range(0, 10):
            time.sleep(0.2)
            print('.' * i)

    def _load_books (self):
        books_root = Path(__file__).parent.parent / 'core' / 'books'

        for path in books_root.rglob("*_book.py"):
            rel_path = path.relative_to(Path(__file__).parent.parent.parent)
            module_path = '.'.join(rel_path.with_suffix('').parts)  # e.g. src.core.books.contact.contact_book

            module = importlib.import_module(module_path)

            for name, obj in inspect.getmembers(module, inspect.isclass):  # looping through
                if issubclass(obj, Book) and obj is not Book:  # looping through specific Book classes

                    bookInstance = obj()
                    book_name = bookInstance.get_book_name()

                    # # to delete start
                    # self.books[book_name] = bookInstance  # e.g. "contact": ContactBook()
                    # continue
                    # to delete end
                    book_pkl_data_file_path = books_root / book_name / f'{book_name}_book_data.pkl'
                    try:
                        with open(book_pkl_data_file_path, "rb") as f:
                            self.books[book_name] = pickle.load(f)
                    except FileNotFoundError:
                        self.books[book_name] = bookInstance  # e.g. "contact": ContactBook()

    def _load_supported_operations_per_book (self):
        for book_name, book in self.books.items():
            self.supported_operations_per_book[book_name] = self.get_book_supported_operations(book_name, book)

    def save_books_state (self):
        books_root = Path(__file__).parent.parent / 'core' / 'books'

        for book in self.books:
            book_obj = self.books[book]
            book_name = book_obj.get_book_name()
            book_pkl_data_file_path = books_root / book_name / f'{book_name}_book_data.pkl'

            with open(book_pkl_data_file_path, "wb") as f:
                pickle.dump(book_obj, f)

    def get_book (self, book_name: str):
        if book_name not in self.books:
            raise ValueError(f'No such book: {book_name}')
        return self.books[book_name]

    def get_supported_operations (self) -> dict[str, list]:
        commands = {}

        for book_name, book in self.books.items():
            book_supported_operations = self.get_book_supported_operations(book_name, book)
            commands = {**commands, **book_supported_operations}

        return commands

    def get_book_supported_operations (self, book_name: str, book: Book):
        commands = {}
        # book records operations
        methods_to_process = self._get_class_methods_for_operations_preparing(book)

        for method_to_process in methods_to_process:
            method_acceptable_params = self._get_book_operation_params(book_name, method_to_process)
            cmd = method_to_process.replace('record', book_name).replace('_', '-')
            commands[cmd] = method_acceptable_params

        # for children fields operations - show all record fields to search by
        record_fields = self.books[
                            book_name].get_record_class().get_record_fields() + book.get_record_class().get_record_multi_value_fields()

        # child fields operations
        for record_class_multi_field in book.get_record_class().get_record_multi_value_fields():
            standard_ops = ['add', 'update', 'get', 'delete']

            for operation_name in standard_ops:
                params = {}
                plural_part = ('s' if operation_name == 'get' else '')
                # e.g. get-notes-tags, get-contacts-phone-numbers
                command_name = f'{operation_name}-{book_name}{plural_part}-{record_class_multi_field.replace('_', '-')}{plural_part}'

                if operation_name in ['add', 'get', 'update', 'delete']:
                    for field_name in record_fields:
                        params.update({Book.get_search_prefix() + '_' + field_name: field_name})

                    if operation_name in ['add', 'update']:
                        params.update(
                            {
                                Book.get_multi_value_to_update_prefix() + '_' + record_class_multi_field: record_class_multi_field
                            }
                        )

                    if operation_name == 'update':
                        params.update(
                            {
                                Book.get_multi_value_to_search_prefix() + '_' + record_class_multi_field: record_class_multi_field
                            }
                        )
                    if operation_name == 'delete':
                        params.update(
                            {
                                Book.get_multi_value_to_delete_prefix() + '_' + record_class_multi_field: record_class_multi_field
                            }
                        )

                commands[command_name] = params

        return commands

    def _get_class_methods_for_operations_preparing (self, book):
        methods_to_process = []

        for method_name in dir(book):
            # checking only public methods
            if method_name.startswith('_') is False:
                method = getattr(book, method_name)
                # preparing for processing only not static and not hidden from bot user functions
                if (callable(getattr(book, method_name))
                        and getattr(method, '_hidden', False) is not True
                        and getattr(method, '_method_for_bot_interface', False) is True
                        and not isinstance(inspect.getattr_static(book, method_name), classmethod)):
                    methods_to_process.append(method_name)

        return methods_to_process

    def run_command (self, command_name: str, **kwargs):
        # dispatches and runs a command like 'add-contact' or 'add-note-tag'
        additional_params = command_name.split("-")[2:]  # ['phone', 'number']
        func_name = command_name.replace('-', '_')

        func = None

        for book_name, book in self.books.items():
            if hasattr(book, func_name) and callable(getattr(book, func_name)):
                func = getattr(book, func_name)  # gets the method
                break
            elif ('_' + book_name) in func_name:  # if '-contact' in 'add-contact' or 'get-contacts'
                if not additional_params:
                    func_name = func_name.replace(book_name, 'record')
                    func = getattr(book, func_name)  # gets the method
                    break
                else:
                    multi_value_fields = book.get_record_class().get_record_multi_value_fields()
                    for multi_value_field in multi_value_fields:
                        if func_name.endswith(multi_value_field):
                            func = getattr(book, 'update_records')
                            break

        if func is not None:
            return func(**kwargs)
        else:
            raise ValueError(f'No such function: {func_name}')

    def _get_book_operation_params (self, book_name: str = '', method_name: str = '') -> dict:
        params = {}
        method_name_parts = method_name.split("_")
        operation_name = method_name_parts[0]
        module_path = f'src.core.books.{book_name}.{book_name}'
        book = self.books[book_name]
        attr = getattr(book, method_name)

        if callable(attr) and getattr(attr, '_method_args_as_command_params', False) is True:
            params = self._generate_params_from_method_args(module_path, book_name, method_name)
        else:
            # record fields should be included as searchable
            record_fields = book.get_record_class().get_record_fields() + book.get_record_class().get_record_multi_value_fields()

            if operation_name == 'add':
                params.update({record_field: record_field for record_field in record_fields})
            else:
                # for operations which require search operations - show fields to search by
                if operation_name in ['update', 'get', 'delete']:
                    for field_name in record_fields:
                        params.update({Book.get_search_prefix() + '_' + field_name: field_name})

                        # for update operations - show also multi value fields user can modify
                        if operation_name == 'update':
                            if field_name in book.get_record_class().get_record_multi_value_fields():
                                params.update({Book.get_multi_value_to_search_prefix() + '_' + field_name: field_name})
                                params.update({Book.get_multi_value_to_update_prefix() + '_' + field_name: field_name})
                            else:
                                params.update({Book.get_update_prefix() + '_' + field_name: field_name})

                if operation_name == 'update':
                    params = self.sort_dict_by_key_prefix(params, record_fields)

            # if not generic record operations - show function arguments as commands params
            if len(params) == 0:
                params = self._generate_params_from_method_args(module_path, book_name, operation_name)

        return params

    def sort_dict_by_key_prefix (self, dict_to_group_keys: dict, suffixes: list[str]) -> dict:
        prefix_groups = defaultdict(dict)

        for key in dict_to_group_keys:
            for suffix in suffixes:
                if key.endswith(suffix):
                    prefix = key[: -len(suffix)]
                    prefix_groups[prefix][key] = dict_to_group_keys[key]
                    break

        # flatten the grouped dicts by sorted prefix
        sorted_result = {}
        for prefix in sorted(prefix_groups.keys()):
            sorted_keys = sorted(prefix_groups[prefix])
            for k in sorted_keys:
                sorted_result[k] = prefix_groups[prefix][k]

        return sorted_result

    def _generate_params_from_method_args (self, module_path, book_name, operation_name):
        params = {}
        module_path += '_book'
        module = importlib.import_module(module_path)
        class_name = book_name.capitalize() + 'Book'
        record_class = getattr(module, class_name)
        # sig = inspect.signature(record_class.__init__)

        # get the method by name (could be 'add_record', 'get_records', etc.)
        method = getattr(record_class, operation_name, None)
        if method is not None:
            # inspect the method signature
            sig = inspect.signature(method)
            # return list of parameter names (skip 'self' or 'cls')
            params = {
                name: name
                for name in sig.parameters
                if name not in ['self', 'cls']
            }

        return params

    def print_result_records (self, text_before_records_output, records):
        print(text_before_records_output)

        for record in records:
            print(record)
            print("-" * 30)

    def _dict_to_string (data: dict, separator: str = ", ") -> str:
        return separator.join(f'{k}= {v}' for k, v in data.items())
