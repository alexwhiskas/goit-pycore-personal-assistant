# src/core/fast_search_adapter.py

from typing import Dict, List, Any, Optional
import os
from pathlib import Path
import json

from src.core.fast_search_module.fast_search import FastSearchModule
from src.core.record import Record


class FastSearchAdapter:
    """Adapter for the FastSearchModule to work with book records"""

    _instance = None
    MIN_SEARCH_LENGTH = 3

    @classmethod
    def get_instance(cls):
        """Singleton pattern to ensure we have only one instance"""
        if cls._instance is None:
            cls._instance = FastSearchAdapter()
        return cls._instance

    def __init__(self):
        """Initialize the fast search module"""
        data_dir = Path(__file__).parent.parent.parent / "data" / "search_indices"
        os.makedirs(data_dir, exist_ok=True)
        self.search_module = FastSearchModule(data_dir=str(data_dir), auto_load=True)

    def initialize_book_index(self, book_name: str, fields: List[str], multi_value_fields: List[str]):
        """Initialize or get an index for a book type"""
        if book_name not in self.search_module.list_indices():
            # Create mapping for the book's fields
            mapping = {}
            for field in fields:
                mapping[field] = {"type": "text"}
            for field in multi_value_fields:
                mapping[field] = {"type": "text"}

            self.search_module.create_index(book_name, mapping)
            return True
        return False

    def index_record(self, book_name: str, record: Record):
        """Index a record in the search module"""
        # Create a serializable representation of the record
        record_dict = {}

        # Add all fields first
        for field, value in record.fields.items():
            record_dict[field] = value

        # Ensure we have an ID
        if "id" not in record_dict:
            record_dict["id"] = str(record.record_as_option())

        # Add multi-value fields
        for field_name, values in record.multi_value_fields.items():
            if values:
                # Join values for searchability
                if isinstance(values, dict):
                    record_dict[field_name] = ", ".join(values.keys())
                else:
                    record_dict[field_name] = str(values)

        # Create a composite searchable text field that contains all values
        all_values = []
        for field, value in record_dict.items():
            if field != "id" and value:
                all_values.append(str(value))

        record_dict["_all"] = " ".join(all_values)

        # Index the document
        self.search_module.index_document(
            book_name,
            str(record_dict["id"]),
            record_dict
        )
        return record_dict["id"]

    def search_records(self, book_name: str, query: str | Dict = None, filters: Dict = None, limit: int = 100):
        """Search for records in a book"""
        # If we have a query, validate its length and use the search function
        if query:
            # Make sure the index exists
            if book_name not in self.search_module.list_indices():
                return []

            try:
                if isinstance(query, dict):
                    results = []

                    for query_value in query.values():
                        results += self.search_module.search(book_name, query_value, filters, limit)
                else:
                    results = self.search_module.search(book_name, query, filters, limit)

                return [result["document"] for result in results]
            except Exception as e:
                print(f"Search error: {e}")
                return []

        # If we only have filters, get all documents and filter manually
        if filters:
            if book_name not in self.search_module.indices:
                return []

            all_docs = []
            # Get all documents from the index
            for doc_id in self.search_module.indices[book_name].documents:
                try:
                    doc = self.search_module.get_document(book_name, doc_id)
                    all_docs.append(doc)
                except Exception:
                    pass

            # Filter the documents
            filtered_docs = []
            for doc in all_docs:
                matches = True
                for key, value in filters.items():
                    if key not in doc or doc[key] != value:
                        matches = False
                        break
                if matches:
                    filtered_docs.append(doc)

            return filtered_docs[:limit]

        return []

    def delete_record(self, book_name: str, record_id: str):
        """Delete a record from the search index"""
        return self.search_module.delete_document(book_name, record_id)

    def update_record(self, book_name: str, record: Record):
        """Update a record in the search index (delete and re-index)"""
        record_id = record.fields.get("id") or id(record)
        self.delete_record(book_name, str(record_id))
        self.index_record(book_name, record)
        return record_id
