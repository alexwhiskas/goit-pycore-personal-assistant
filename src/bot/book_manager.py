# src/bot/book_manager.py
import copy
import importlib
import inspect
import pickle
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict
from colorama import Fore, Style

from src.core.book import Book, RETURN_RESULT_NEW, RETURN_RESULT_FOUND, RETURN_RESULT_DUPLICATE, RETURN_RESULT_DELETED, RETURN_RESULT_NOT_DELETED, RETURN_RESULT_UPDATED, RETURN_RESULT_NOT_UPDATED
from src.core.response_code import PREV_OPERATION, RETRY_OPERATION, EXIT_OPERATION
from src.core.command_auto_complete.command_auto_complete import CommandAutoCompletion
from src.core.fast_search_adapter import FastSearchAdapter


class BookManager:
    # EXIT_OPERATION = 'exit'
    # PREV_OPERATION = 'prev'
    # RETRY_OPERATION = 'retry'

    books: Dict[str, Book] = {}

    def __init__ (self):
        self.books = {}
        self.supported_operations_per_book = {}

        # Get the fast search adapter instance
        self.fast_search = FastSearchAdapter.get_instance()
        self._load_books()
        self._load_supported_operations_per_book()
        # Initialize search indexes for all books
        self._initialize_search_indexes()

    def _initialize_search_indexes (self):
        """Initialize search indexes for all books"""
        print(f"{Fore.BLUE}🔍 Initializing search indexes...{Style.RESET_ALL}")
        for book_name, book in self.books.items():
            fields = book.get_record_class().get_record_fields()
            multi_value_fields = book.get_record_class().get_record_multi_value_fields()

            # Initialize the index for this book type
            self.fast_search.initialize_book_index(book_name, fields, multi_value_fields)

            # Index all existing records
            for record in book.data.values():
                self.fast_search.index_record(book_name, record)

        print(f"{Fore.GREEN}✅ Search indexes initialized{Style.RESET_ALL}")

    def end (self):
        print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
        self.animate_process_func('Saving books info. Finishing process')
        self.save_books_state()
        exit()

    def _print_supported_grouped_commands (self, grouped_commands):
        # Print commands by group - show global commands first
        if 'global' in grouped_commands:
            print(f"\n{Fore.BLUE}🌐 Global commands:{Style.RESET_ALL}")
            for cmd, params in grouped_commands['global'].items():
                params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
                print(f"{Fore.GREEN} ✓ {cmd}{params_str}")

        if 'general' in grouped_commands:
            print(f"\n{Fore.BLUE}📋 General commands:{Style.RESET_ALL}")
            for cmd, params in grouped_commands['general'].items():
                params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
                print(f"{Fore.GREEN} ✓ {cmd}{params_str}")

        # Then show book-specific commands
        for book_type, commands in grouped_commands.items():
            if book_type not in ['global', 'general']:
                print(f"\n{Fore.BLUE}📗 {book_type.capitalize()} commands:{Style.RESET_ALL}")
                for cmd, params in commands.items():
                    params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
                    print(f"{Fore.GREEN} ✓ {cmd}{params_str}")

        print(f"\n{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}ℹ️ Press Ctrl+C to exit at any time{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}\n")

    def start (self, book_selection_prompt):
        grouped_commands = self.supported_operations_per_book
        grouped_commands['global'] = {'search-all': {'query': 'text to search across all books'}}
        grouped_commands['global']['help'] = {'group': ', '.join(grouped_commands.keys())}
        grouped_commands['global']['exit'] = {}

        self._print_supported_grouped_commands(grouped_commands)
        books_records_classes = {}
        for book_name, book in self.books.items():
            books_records_classes[book_name] = book.get_record_class()

        completer = CommandAutoCompletion(list(grouped_commands.keys()), grouped_commands, books_records_classes)

        try:
            while True:
                def try_run_operation_from_customer_input():
                    cmd_and_args = completer.prompt_with_completion(f"{Fore.CYAN}💬 Enter a command: {Style.RESET_ALL}")
                    user_input, prompted_args = cmd_and_args

                    if not user_input:
                        print(f"{Fore.RED}⚠️ No command entered. Please try again.{Style.RESET_ALL}")
                        return RETRY_OPERATION

                    command_execution_result = self.run_command(user_input, **prompted_args)

                    if isinstance(command_execution_result, tuple) and len(command_execution_result) == 3:
                        result_code, result_records, conditions = command_execution_result
                        book_name_from_operation = user_input.split("-")[1]
                        current_operation_book = self.books.get(book_name_from_operation) or self.books.get(book_name_from_operation[:-1])
                        print(f"Current operation book: {current_operation_book}")

                        if result_code in [
                            RETURN_RESULT_NEW,
                            RETURN_RESULT_UPDATED,
                            RETURN_RESULT_DELETED,
                            RETURN_RESULT_FOUND
                        ]:
                            self.print_result_records(
                                f'As result of your inputs, following record(s) was/were {result_code}',
                                result_records
                            )

                            return result_code
                        elif result_code == RETURN_RESULT_DUPLICATE:
                            self.print_result_records(
                                f'Following entered params: {self._dict_to_string(conditions)}, will create collision with existing records: ',
                                result_records
                            )

                            choice_add = 'add'
                            choice_update = 'update'

                            user_preferred_record_operation = input(
                                f"Do you want to update existing record or add a new one? ({choice_add}/{choice_update}), if nothing entered, moving to prev operation: "
                            ).strip()

                            if user_preferred_record_operation == choice_add:
                                print(
                                    f'We\'ll re-start execution of current command. Please, update one of the following params to create new record when asked next time: '
                                    + self._dict_to_string(conditions)
                                )

                                return try_run_operation_from_customer_input()
                            else:
                                current_operation_book.update_records(**prompted_args) # todo: emulate update operation

                                return RETURN_RESULT_UPDATED
                        elif result_code in [RETURN_RESULT_NOT_UPDATED, RETURN_RESULT_NOT_DELETED]:
                            print(
                                f"Couldn't find record to update with entered search params: " + self._dict_to_string(
                                    conditions
                                )
                            )

                            suggest_existing = "suggest existing"
                            alternative_choice = ""
                            if result_code == RETURN_RESULT_UPDATED:
                                alternative_choice = "add new record"

                            if (alternative_choice):
                                prompt_message = f"Do you want to update existing record or add a new one? ({alternative_choice}/{suggest_existing}), if nothing entered, moving to prev operation: "
                            else:
                                prompt_message = f"Enter '{suggest_existing}' to get some suggestions for records to update. Any other input will lead to moving to prev operation: "

                            user_preferred_record_operation = str(input(prompt_message)).strip()

                            if alternative_choice and user_preferred_record_operation == alternative_choice:
                                current_operation_book.add_record(**prompted_args)

                                return PREV_OPERATION
                            elif user_preferred_record_operation == suggest_existing:
                                multi_value_fields = current_operation_book.get_record_class().get_record_multi_value_fields()

                                for multi_value_field in multi_value_fields:
                                    multi_value_condition = conditions.get(multi_value_field)

                                    if multi_value_condition:
                                        if isinstance(multi_value_condition, str):
                                            conditions[multi_value_field] = multi_value_condition
                                        else:
                                            for multi_value_condition_key, multi_value_condition_value in multi_value_condition.items():
                                                if not multi_value_condition_key:
                                                    conditions[multi_value_field] = multi_value_condition_value
                                                else:
                                                    conditions[multi_value_field] = multi_value_condition_key

                                self.animate_process_func('Looking for records to suggest')
                                found_records_result_code, found_records, conditions_to_find_by = current_operation_book.search_records(conditions)

                                if found_records:
                                    records_options = {}
                                    for found_record in found_records:
                                        records_options[found_record.record_as_option()] = found_record

                                    return_to_prev_step_option = "---Return to previous step"

                                    selection_from_founded_records = questionary.select(
                                        'Choose from one of the following records to process:',
                                        list(records_options.keys()) + [return_to_prev_step_option],
                                    ).ask()

                                    if result_code == RETURN_RESULT_NOT_UPDATED:
                                        if selection_from_founded_records == return_to_prev_step_option:
                                            return PREV_OPERATION

                                        found_record_to_update = current_operation_book.data[selection_from_founded_records]
                                        new_record_data = copy.deepcopy(prompted_args)

                                        def build_record_to_update_dict_from_objects(new_record_data, found_record_to_update):
                                            prompted_args = {}
                                            found_record_fields = found_record_to_update.get_record_fields()
                                            found_record_fields_values = found_record_to_update.fields

                                            for found_record_field in found_record_fields:
                                                found_record_field_with_search_prefix = Book.get_search_prefix() + '_' + found_record_field
                                                found_record_field_data_to_replace_in_found = str(found_record_fields_values.get(found_record_field))
                                                prompted_args.update({found_record_field_with_search_prefix:found_record_field_data_to_replace_in_found})

                                                new_record_field_with_update_prefix = Book.get_update_prefix() + '_' + found_record_field
                                                new_record_field_data_to_replace_in_found = str(new_record_data.get(new_record_field_with_update_prefix))
                                                prompted_args.update({new_record_field_with_update_prefix:new_record_field_data_to_replace_in_found})

                                            found_record_multi_value_fields = found_record_to_update.get_record_multi_value_fields()
                                            found_record_multi_value_fields_values = found_record_to_update.multi_value_fields

                                            for found_record_multi_value_field in found_record_multi_value_fields:
                                                found_record_multi_value_field_values = found_record_to_update.multi_value_fields.get(found_record_multi_value_field)
                                                if found_record_multi_value_field_values:
                                                    found_record_multi_value_field_param_key = Book.get_search_prefix() + '_' + found_record_multi_value_field
                                                    prompted_args.update({found_record_multi_value_field_param_key:list(found_record_multi_value_field_values.values())})

                                                new_record_field_with_update_prefix = Book.get_multi_value_to_update_prefix() + '_' + found_record_multi_value_field
                                                new_record_field_data_to_replace_by_in_found = str(new_record_data.get(new_record_field_with_update_prefix))
                                                prompted_args.update({new_record_field_with_update_prefix:new_record_field_data_to_replace_by_in_found})

                                                found_record_multi_value_field_with_search_prefix = Book.get_multi_value_to_search_prefix() + '_' + found_record_multi_value_field
                                                new_record_field_data_to_replace_with_in_found_from_new_record = str(new_record_data.get(found_record_multi_value_field_with_search_prefix))
                                                found_record_multi_value_field_values_to_replace = found_record_multi_value_fields_values.get(found_record_multi_value_field)
                                                found_record_multi_value_field_to_replace = str(found_record_multi_value_field_values_to_replace.get(new_record_field_data_to_replace_with_in_found_from_new_record))
                                                prompted_args.update({found_record_multi_value_field_with_search_prefix:found_record_multi_value_field_to_replace})

                                            return prompted_args

                                        prepared_prompt_args = build_record_to_update_dict_from_objects(new_record_data, found_record_to_update)
                                        suggested_update_result_code, suggested_update_result_records, suggested_update_result_conditions = current_operation_book.update_records(**prepared_prompt_args)

                                        if suggested_update_result_code == RETURN_RESULT_NOT_UPDATED:
                                            print(f"Returning to previous step, we couldn't find any records for your keywords: " + self._dict_to_string(conditions))
                                        else:
                                            self.print_result_records(
                                                print(
                                                    f"Successfully updates suggested record(s):"
                                                ),
                                                suggested_update_result_records
                                            )

                                    else:
                                        if selection_from_founded_records in records_options:
                                            del current_operation_book.data[selection_from_founded_records]
                                else:
                                    print(f"Returning to previous step, we couldn't find any records for your keywords: " + self._dict_to_string(conditions))

                            return PREV_OPERATION

                    elif isinstance(command_execution_result, list):
                        self.print_result_records(
                            print(
                                f"Function '{user_input} returned {len(command_execution_result)} record(s):"
                            ),
                            command_execution_result
                        )

                        return PREV_OPERATION
                    else:
                        return RETRY_OPERATION

                result = try_run_operation_from_customer_input()
                if result == EXIT_OPERATION:
                    break
        finally:
            self.save_books_state()
            print(f"\n{Fore.GREEN}✅ Address book saved.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")

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
        # Ensure search indices are up to date before saving
        for book_name, book in self.books.items():
            for record in book.data.values():
                self.fast_search.update_record(book_name, record)

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
                command_name = f"{operation_name}-{book_name}{plural_part}-{record_class_multi_field.replace('_', '-')}{plural_part}"

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

    def run_command(self, command_name: str, **kwargs):
        # Handle global help command
        if command_name == "help":
            group = kwargs.get("group", "")
            if group and group in self.supported_operations_per_book:
                print(f"\n{Fore.BLUE}📚 Help for {group.capitalize()} commands:{Style.RESET_ALL}")
                self._print_supported_grouped_commands({group: self.supported_operations_per_book[group]})
                return None
            else:
                print(f"\n{Fore.BLUE}📚 All available commands:{Style.RESET_ALL}")
                self._print_supported_grouped_commands(self.supported_operations_per_book)
                return None

        # Handle global search command
        if command_name == "search-all":
            query = kwargs.get("query")
            if not query or len(query) < FastSearchAdapter.MIN_SEARCH_LENGTH:
                print(
                    f"{Fore.RED}⚠️ Search query must be at least {FastSearchAdapter.MIN_SEARCH_LENGTH} characters long{Style.RESET_ALL}")
                return []

            all_results = []
            for book_name, book in self.books.items():
                try:
                    result_code, found_records, _ = book.search_records(query)
                    if result_code == RETURN_RESULT_FOUND:
                        all_results.extend(found_records)
                except ValueError as e:
                    print(f"{Fore.RED}⚠️ Error searching {book_name}: {e}{Style.RESET_ALL}")

            if not all_results:
                print(f"{Fore.YELLOW}ℹ️ No records found matching '{query}'{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✅ Found {len(all_results)} records matching '{query}'{Style.RESET_ALL}")

            return all_results

        # Regular command processing
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

    def _dict_to_string (self, data: dict, separator: str = ", ") -> str:
        return separator.join(f'{k}= {v}' for k, v in data.items())
