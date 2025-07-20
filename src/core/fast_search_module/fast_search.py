# src/core/fast_search_module/fast_search.py


import json
import re
import pickle
import os
from typing import Dict, List, Any, Set, Optional
from datetime import datetime
import math

from src.core.fast_search_module.decorators import handle_exceptions, validate_document, auto_save, validate_index_exists, cache_result
from src.core.fast_search_module.index_data import IndexData


def _tokenize(text: str) -> List[str]:
    """Simple tokenization - split on whitespace and punctuation"""
    if not isinstance(text, str):
        text = str(text)
    tokens = re.findall(r'\b\w+\b', text.lower())
    return tokens


def _normalize_value(value: Any, field_type: str) -> Any:
    """Normalize value based on field type"""
    if field_type == "text":
        return str(value)
    elif field_type == "keyword":
        return str(value)
    elif field_type == "integer":
        return int(value) if value is not None else None
    elif field_type == "float":
        return float(value) if value is not None else None
    elif field_type == "boolean":
        return bool(value) if value is not None else None
    elif field_type == "date":
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except Any:
                return value
        return value
    else:
        return value


def _calculate_tf_idf(term: str, doc_id: str, index_data: 'IndexData') -> float:
    """Calculate Term Frequency-Inverse Document Frequency (TF-IDF) score"""
    if doc_id not in index_data.term_frequencies or term not in index_data.term_frequencies[doc_id]:
        return 0.0

    tf = index_data.term_frequencies[doc_id][term]
    df = index_data.term_doc_count[term]

    if df == 0:
        return 0.0

    idf = math.log(index_data.document_count / df)
    return tf * idf


class FastSearchModule:
    def __init__(self, data_dir: str = "es_data", auto_load: bool = True, enable_caching: bool = True):
        # Initialize the FastSearchModule instance
        # Parameters:
        self.data_dir = data_dir # Directory to store index data
        self.enable_caching = enable_caching # Enable caching for search results
        self.indices = {}  # index_name -> IndexData
        self.mappings = {}  # index_name -> field mappings

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        # Auto-load existing data
        if auto_load:
            self._load_all_indices()

    @handle_exceptions(default_return=False)
    def _load_all_indices(self):
        """Load all existing indices from disk"""
        indices_file = os.path.join(self.data_dir, "indices.json")
        if os.path.exists(indices_file):
            with open(indices_file, 'r') as f:
                index_list = json.load(f)
                for index_name in index_list:
                    self._load_index(index_name)
        return True

    @handle_exceptions(default_return=False)
    def _load_index(self, index_name: str):
        """Load a specific index from disk"""
        index_file = os.path.join(self.data_dir, f"{index_name}.pkl")
        if os.path.exists(index_file):
            with open(index_file, 'rb') as f:
                self.indices[index_name] = pickle.load(f)

            # Load mappings
            mapping_file = os.path.join(self.data_dir, f"{index_name}_mapping.json")
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    self.mappings[index_name] = json.load(f)
        return True

    def create_index(self, index_name: str, mapping: Optional[Dict[str, Any]] = None):
        """Create a new index with optional field mappings"""
        if index_name in self.indices:
            return False  # Index already exists

        self.indices[index_name] = IndexData()
        self.mappings[index_name] = mapping or {}

        # Save to disk
        self._save_index(index_name)
        self._save_indices_list()
        return None

    @handle_exceptions(default_return=False)
    def _save_index(self, index_name: str):
        """Save a specific index to disk"""
        # Save index data
        index_file = os.path.join(self.data_dir, f"{index_name}.pkl")
        with open(index_file, 'wb') as f:
            pickle.dump(self.indices[index_name], f)

        # Save mappings
        mapping_file = os.path.join(self.data_dir, f"{index_name}_mapping.json")
        with open(mapping_file, 'w') as f:
            json.dump(self.mappings[index_name], f, indent=2)

        return True

    @handle_exceptions(default_return=False)
    def _save_indices_list(self):
        """Save list of all indices"""
        indices_file = os.path.join(self.data_dir, "indices.json")
        with open(indices_file, 'w') as f:
            json.dump(list(self.indices.keys()), f)
        return True

    def _analyze_document(self, doc: Dict[str, Any], mapping: Dict[str, Any]) -> Set[str]:
        """Extract and tokenize searchable fields from a document"""
        all_tokens = set()

        def extract_text(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    field_mapping = mapping.get(current_path, {})
                    field_type = field_mapping.get("type", "text")

                    if field_type in ["text", "keyword"]:
                        if isinstance(value, (str, int, float, bool)):
                            all_tokens.update(_tokenize(str(value)))
                        elif isinstance(value, (list, dict)):
                            extract_text(value, current_path)
                    elif field_type in ["integer", "float"]:
                        # Numbers can be searched as text too
                        all_tokens.update(_tokenize(str(value)))
                    elif isinstance(value, (dict, list)):
                        extract_text(value, current_path)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text(item, path)
            else:
                all_tokens.update(_tokenize(str(obj)))

        extract_text(doc)
        return all_tokens

    @validate_document
    @auto_save
    def index_document(self, index_name: str, doc_id: str, document: Dict[str, Any]):
        """Index a document in the specified index"""
        if index_name not in self.indices:
            self.create_index(index_name)

        index_data = self.indices[index_name]
        mapping = self.mappings[index_name]

        # Normalize document based on mapping
        normalized_doc = self._normalize_document(document, mapping)

        # Store the document
        index_data.documents[doc_id] = normalized_doc

        # Tokenize and build inverted index
        tokens = self._analyze_document(normalized_doc, mapping)

        def extract_all_tokens(obj):
            if isinstance(obj, str):
                return _tokenize(obj)
            elif isinstance(obj, dict):
                tokens_dict = []
                for value in obj.values():
                    tokens_dict.extend(extract_all_tokens(value))
                return tokens_dict
            elif isinstance(obj, list):
                tokens_list = []
                for item in obj:
                    tokens_list.extend(extract_all_tokens(item))
                return tokens_list
            else:
                return _tokenize(str(obj))

        all_tokens = extract_all_tokens(normalized_doc)

        # Calculate term frequencies
        for token in all_tokens:
            index_data.term_frequencies[doc_id][token] += 1

        # Update inverted index
        for token in tokens:
            if doc_id not in index_data.inverted_index[token]:
                index_data.inverted_index[token].add(doc_id)
                index_data.term_doc_count[token] += 1

        index_data.document_count += 1

    def _normalize_document(self, doc: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize document fields based on mapping"""
        def normalize_field(obj, path=""):
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    field_mapping = mapping.get(current_path, {})
                    field_type = field_mapping.get("type", "text")

                    if isinstance(value, (dict, list)):
                        result[key] = normalize_field(value, current_path)
                    else:
                        result[key] = _normalize_value(value, field_type)
                return result
            elif isinstance(obj, list):
                return [normalize_field(item, path) for item in obj]
            else:
                return obj

        return normalize_field(doc) # Ensure we return a normalized document, use recursion to handle nested structures

    @validate_index_exists
    @cache_result(max_size=64)
    def search(self, index_name: str, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for documents in the specified index"""
        index_data = self.indices[index_name]
        query_tokens = _tokenize(query)

        if not query_tokens or not index_data or not index_data.inverted_index:
            return []

        # Find documents containing query terms
        candidate_docs = set()
        for token in query_tokens:
            candidate_docs.update(index_data.inverted_index[token])

        # Score documents
        scored_docs = []
        for doc_id in candidate_docs:
            score = 0.0
            for token in query_tokens:
                score += _calculate_tf_idf(token, doc_id, index_data)

            if score > 0:
                scored_docs.append({
                    'id': doc_id,
                    'score': score,
                    'document': index_data.documents[doc_id]
                })

        # Sort by score (descending) and return top results
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        return scored_docs[:limit]

    @validate_index_exists
    @handle_exceptions(default_return=None)
    def get_document(self, index_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID"""
        result = self.indices[index_name].documents.get(doc_id)

        return result

    @validate_index_exists
    @auto_save
    def delete_document(self, index_name: str, doc_id: str) -> bool:
        """Delete a document from the index"""
        index_data = self.indices[index_name]
        if doc_id not in index_data.documents:
            return False

        # Remove from inverted index
        mapping = self.mappings[index_name]
        tokens = self._analyze_document(index_data.documents[doc_id], mapping)

        for token in tokens:
            index_data.inverted_index[token].discard(doc_id)
            if not index_data.inverted_index[token]:
                del index_data.inverted_index[token]
                del index_data.term_doc_count[token]
            else:
                index_data.term_doc_count[token] -= 1

        # Remove document and term frequencies
        del index_data.documents[doc_id]
        del index_data.term_frequencies[doc_id]
        index_data.document_count -= 1
        return True

    def list_indices(self) -> List[str]:
        """List all available indices"""
        return list(self.indices.keys())

    def delete_index(self, index_name: str) -> bool:
        """Delete an entire index"""
        if index_name not in self.indices:
            return False

        del self.indices[index_name]
        del self.mappings[index_name]

        # Remove files
        try:
            os.remove(os.path.join(self.data_dir, f"{index_name}.pkl"))
            os.remove(os.path.join(self.data_dir, f"{index_name}_mapping.json"))
        except:
            pass

        self._save_indices_list()
        return True

    @validate_index_exists
    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get statistics about an index"""
        index_data = self.indices[index_name]
        return {
            'document_count': index_data.document_count,
            'unique_terms': len(index_data.inverted_index),
            'mapping': self.mappings[index_name]
        }

    def clear_cache(self):
        """Clear search cache if caching is enabled"""
        if hasattr(self.search, 'cache'):
            self.search.cache.clear()
        print("[INFO] Search cache cleared")
