# src/bot/book_manager.py

import importlib
import inspect
import pickle
from pathlib import Path
from typing import Dict, List
from src.core.book import Book
from src.core.record import Record
from src.core.fast_search_adapter import FastSearchAdapter
from colorama import Fore, Style


class BookManager:
    books: Dict[str, Book] = {}

    def __init__ (self):
        self.books = {}
        # Get the fast search adapter instance
        self.fast_search = FastSearchAdapter.get_instance()
        self._load_books()
        # Initialize search indexes for all books
        self._initialize_search_indexes()

    def _load_books (self):
        books_root = Path(__file__).parent.parent / 'core' / 'books'

        for path in books_root.rglob("*_book.py"):
            rel_path = path.relative_to(Path(__file__).parent.parent.parent)
            module_path = '.'.join(rel_path.with_suffix('').parts)  # e.g. src.core.books.contact.contact_book

            module = importlib.import_module(module_path)

            for name, obj in inspect.getmembers(module, inspect.isclass): # looping through
                if issubclass(obj, Book) and obj is not Book: # looping through specific Book classes

                    bookInstance = obj()
                    book_name = bookInstance.get_book_name()

                    # to delete start
                    self.books[book_name] = bookInstance  # e.g. "contact": ContactBook()
                    continue
                    # to delete end
                    # book_pkl_data_file_path = books_root / book_name / f'{book_name}_book_data.pkl'
                    # try:
                    #     with open(book_pkl_data_file_path, "rb") as f:
                    #         self.books[book_name] = pickle.load(f)
                    # except FileNotFoundError:
                    #     self.books[book_name] = bookInstance  # e.g. "contact": ContactBook()

    def _initialize_search_indexes(self):
        """Initialize search indexes for all books"""
        print(f"{Fore.BLUE}🔍 Initializing search indexes...{Style.RESET_ALL}")
        for book_name, book in self.books.items():
            fields = book.get_record_class_fields()
            multi_value_fields = book.get_record_multi_value_fields()

            # Initialize the index for this book type
            self.fast_search.initialize_book_index(book_name, fields, multi_value_fields)

            # Index all existing records
            for record in book.records:
                self.fast_search.index_record(book_name, record)

        print(f"{Fore.GREEN}✅ Search indexes initialized{Style.RESET_ALL}")

    def save_books_state (self):
        pass
        # books_root = Path(__file__).parent.parent / 'core' / 'books'
        #
        # for book in self.books:
        #     book_obj = self.books[book]
        #     book_name = book_obj.get_book_name()
        #     book_pkl_data_file_path = books_root / book_name / f'{book_name}_book_data.pkl'
        #
        #     with open(book_pkl_data_file_path, "wb") as f:
        #         pickle.dump(book_obj, f)

    def get_book (self, book_name: str):
        if book_name not in self.books:
            raise ValueError(f'No such book: {book_name}')
        return self.books[book_name]

    def get_supported_operations (self) -> dict[str, list]:
        commands = {}

        for book_name, book in self.books.items():
            # book records operations
            methods_to_process = self._get_class_methods_for_operations_preparing(book)

            for method_to_process in methods_to_process:
                method_acceptable_params = self._get_book_operation_params(book_name, method_to_process)
                cmd = method_to_process.replace('record', book_name).replace('_', '-')
                commands[cmd] = method_acceptable_params

            # for children fields operations - show all record fields to search by
            record_fields = self.books[book_name].get_record_class_fields() + book.get_record_class_fields()

            # child fields operations
            for record_class_multi_field in book.get_record_multi_value_fields():
                standard_ops = ['add', 'update', 'get', 'delete']

                for operation_name in standard_ops:
                    params = {}
                    command_name = f"{operation_name}-{book_name}-{record_class_multi_field.replace('_', '-')}"

                    if operation_name in ['add', 'update', 'delete']:
                        for field_name in record_fields:
                            params.update({Book.get_search_prefix() + '_' + field_name: field_name})

                        if operation_name in ['add', 'update']:
                            params.update({Book.get_multi_value_to_update_prefix() + '_' + record_class_multi_field: record_class_multi_field})

                        if operation_name == 'update':
                            params.update({Book.get_multi_value_to_search_prefix() + '_' + record_class_multi_field: record_class_multi_field})
                        if operation_name == 'delete':
                            params.update({Book.get_multi_value_to_delete_prefix() + '_' + record_class_multi_field: record_class_multi_field})

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
                        and not isinstance(inspect.getattr_static(book, method_name), classmethod)):
                    methods_to_process.append(method_name)

        return methods_to_process

    def run_command(self, command_name: str, *args, **kwargs):
        # Check if this is a global search command
        if command_name == 'search-all':
            query = kwargs.get('query', '')

            if not query and args:
                query = args[0]  # Use first positional arg as query

            # Perform global search across all books
            try:
                all_results = self.global_search(query)
                return {'function_name': 'global_search', 'result': all_results}
            except ValueError as e:
                return {'function_name': 'error_global_search', 'result': str(e)}

        # Check if this is a book-specific search command
        elif command_name.startswith('search-'):
            # Extract book name from command
            parts = command_name.split('-')
            if len(parts) < 2:
                return False

            book_name = parts[1]
            query = kwargs.get('query', '')

            if not query and args:
                query = args[0]  # Use first positional arg as query

            # Get the book
            try:
                book = self.get_book(book_name)

                # Perform the search
                results = book.search_records(query)

                # If no results were found but we have records, try doing a simple text match
                if not results and book.records and len(query) >= FastSearchAdapter.MIN_SEARCH_LENGTH:
                    for record in book.records:
                        # Check if query appears in any field value
                        for field, value in record.fields.items():
                            if query.lower() in str(value).lower():
                                results.append(record)
                                break

                        # Also check multi-value fields
                        if not results:
                            for field, values in record.multi_value_fields.items():
                                if isinstance(values, dict) and any(query.lower() in k.lower() for k in values.keys()):
                                    results.append(record)
                                    break

                return {'function_name': f'search_{book_name}', 'result': results}
            except ValueError as e:
                return {'function_name': f'error_search_{book_name}', 'result': str(e)}
            except Exception as e:
                return {'function_name': f'error_search_{book_name}', 'result': f"Error searching: {str(e)}"}

        # dispatches and runs a command like 'add-contact' or 'add-note-tag'
        additional_params = command_name.split("-")[2:]  # ['phone', 'number']
        func_name = command_name.replace('-', '_')

        func = None
        for book_name, book in self.books.items():
            if hasattr(book, func_name) and callable(getattr(book, func_name)):
                func = getattr(book, func_name)  # gets the method
            elif ('_' + book_name) in func_name:  # if '-contact' in 'add-contact' or 'get-contacts'
                if not additional_params:
                    func_name = func_name.replace(book_name, 'record')
                    func = getattr(book, func_name)  # gets the method
                else:
                    multi_value_fields = book.get_record_multi_value_fields()
                    for multi_value_field in multi_value_fields:
                        if func_name.endswith(multi_value_field):
                            func = getattr(book, 'update_records')

        if func is None:
            return False
        else:
            return {'function_name': func_name, 'result': func(*args, **kwargs)}

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
            record_fields = book.get_record_class_fields() + book.get_record_multi_value_fields()
            if operation_name == 'add':
                params.update({record_field:record_field for record_field in record_fields})
            else:
                # for operations which require search operations - show fields to search by
                if operation_name in ['update', 'get', 'delete']:
                    for field_name in record_fields:
                        params.update({Book.get_search_prefix() + '_' + field_name: field_name})

                        # for update operations - show also multi value fields user can modify
                        if operation_name == 'update':
                            if field_name in book.get_record_multi_value_fields():
                                params.update({Book.get_multi_value_to_search_prefix() + '_' + field_name: field_name})
                                params.update({Book.get_multi_value_to_update_prefix() + '_' + field_name: field_name})
                            else:
                                params.update({Book.get_update_prefix() + '_' + field_name: field_name})

            # if not generic record operations - show function arguments as commands params
            if len(params) == 0:
                params = self._generate_params_from_method_args(module_path, book_name, operation_name)

        return params

    def _generate_params_from_method_args(self, module_path, book_name, operation_name):
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

    def print_commands(self, block=None):
        """Print all supported commands or commands for a specific block"""
        supported_operations = self.get_supported_operations()

        # Group commands by book type for better organization
        grouped_commands = {}
        for cmd, params in supported_operations.items():
            book_type = cmd.split('-')[1] if len(cmd.split('-')) > 1 else 'general'
            if book_type not in grouped_commands:
                grouped_commands[book_type] = []
            grouped_commands[book_type].append((cmd, params))

        result = []

        # If a specific block is requested
        if block and block in grouped_commands:
            result.append(f"\n{Fore.BLUE}📗 {block.capitalize()} commands:{Style.RESET_ALL}")
            for cmd, params in grouped_commands[block]:
                params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
                result.append(f"{Fore.GREEN} ✓ {cmd}{params_str}")
        # If no block specified or invalid block, print all commands
        elif block is None:
            result.append(f"{Fore.MAGENTA}🔍 All supported commands:{Style.RESET_ALL}")
            for book_type, commands in grouped_commands.items():
                result.append(f"\n{Fore.BLUE}📗 {book_type.capitalize()} commands:{Style.RESET_ALL}")
                for cmd, params in commands:
                    params_str = f" {' '.join(f'{Fore.YELLOW}{k}{Style.RESET_ALL}={Fore.CYAN}{v}{Style.RESET_ALL}' for k, v in params.items())}" if params else ""
                    result.append(f"{Fore.GREEN} ✓ {cmd}{params_str}")
        else:
            result.append(f"{Fore.RED}❌ Block '{block}' not found. Available blocks:{Style.RESET_ALL}")
            result.append(f"{Fore.CYAN}{', '.join(grouped_commands.keys())}{Style.RESET_ALL}")

        return result

    def get_record_fields(self, book_name: str) -> List[str]:
        """Get all available field names for a given book's records"""
        if book_name not in self.books:
            raise ValueError(f"No such book: {book_name}")

        book = self.books[book_name]
        return book.get_record_class_fields() + book.get_record_multi_value_fields()

    def global_search(self, query: str) -> List[Record]:
        """Search across all books for records matching the query"""
        # Validate minimum search length
        min_length = FastSearchAdapter.MIN_SEARCH_LENGTH
        if len(query.strip()) < min_length:
            raise ValueError(f"Search query must be at least {min_length} characters long")

        all_results = []

        # Search in each book
        for book_name, book in self.books.items():
            try:
                # Get results from this book
                book_results = book.search_records(query)

                # Add book origin information to each record
                for record in book_results:
                    # Add book type to record if possible
                    if hasattr(record, 'fields'):
                        record.fields['_book_type'] = book_name

                # Add to combined results
                all_results.extend(book_results)
            except ValueError:
                # Skip books that raise validation errors
                continue

        return all_results
