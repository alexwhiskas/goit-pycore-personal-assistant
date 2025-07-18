from functools import wraps
from typing import Callable, Dict, Any


def validate_index_exists(func: Callable) -> Callable:
    """Decorator to validate that index exists"""

    @wraps(func)
    def wrapper(self, index_name: str, *args, **kwargs):
        if index_name not in self.indices:
            raise ValueError(f"Index '{index_name}' does not exist")
        return func(self, index_name, *args, **kwargs)

    return wrapper


def auto_save(func: Callable) -> Callable:
    """Decorator to automatically save index after modifications"""

    @wraps(func)
    def wrapper(self, index_name: str, *args, **kwargs):
        result = func(self, index_name, *args, **kwargs)
        if hasattr(self, '_save_index'):
            self._save_index(index_name)
        return result

    return wrapper


def handle_exceptions(default_return=None):
    """Decorator for exception handling with optional default return"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                class_name = args[0].__class__.__name__ if args else "Unknown"
                print(f"[ERROR] {class_name}.{func.__name__}: {str(e)}")
                return default_return

        return wrapper

    return decorator


def cache_result(max_size: int = 128):
    """Simple cache decorator for search results"""

    def decorator(func: Callable) -> Callable:
        cache = {}
        access_order = []

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from args and kwargs
            cache_key = str(args) + str(sorted(kwargs.items()))

            if cache_key in cache:
                # Move to end (most recently used)
                access_order.remove(cache_key)
                access_order.append(cache_key)
                return cache[cache_key]

            # Execute function
            result = func(*args, **kwargs)

            # Add to cache
            cache[cache_key] = result
            access_order.append(cache_key)

            # Remove oldest if cache is full
            if len(cache) > max_size:
                oldest_key = access_order.pop(0)
                del cache[oldest_key]

            return result

        return wrapper

    return decorator


def validate_document(func: Callable) -> Callable:
    """Decorator to validate document structure"""

    @wraps(func)
    def wrapper(self, index_name: str, doc_id: str, document: Dict[str, Any], *args, **kwargs):
        if not isinstance(document, dict):
            raise ValueError("Document must be a dictionary")

        if not doc_id or not isinstance(doc_id, str):
            raise ValueError("Document ID must be a non-empty string")

        # Validate against mapping if it exists
        if index_name in self.mappings:
            self._validate_document_against_mapping(document, self.mappings[index_name])

        return func(self, index_name, doc_id, document, *args, **kwargs)

    return wrapper
