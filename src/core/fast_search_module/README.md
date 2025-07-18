# FastSearchModule

The `FastSearchModule` is a lightweight, in-memory search engine that allows you to create indices, index documents, and perform fast searches with optional filtering and scoring.

## Features
- Create and manage multiple indices.
- Index documents with customizable field mappings.
- Perform full-text search with tokenization and scoring (TF-IDF).
- Apply filters to narrow down search results.
- Cache search results for improved performance.
- Export and import indices.

## Installation
Ensure you have Python 3.8+ installed.

## Usage

### Initialization
```python
from src.modules.fast_search.fast_search import FastSearchModule

# Initialize the search module
search = FastSearchModule(data_dir="search_data", enable_caching=True)
```

### Creating an Index
```python
# Define a mapping for the index
user_mapping = {
    "name": {"type": "text"},
    "email": {"type": "keyword"},
    "age": {"type": "integer"},
    "active": {"type": "boolean"},
    "created_at": {"type": "date"}
}

# Create an index
search.create_index("users", user_mapping)
```

### Indexing Documents
```python
# Add documents to the index
user1 = {"name": "John Doe", "email": "john@example.com", "age": 30, "active": True, "created_at": "2024-01-15"}
user2 = {"name": "Jane Smith", "email": "jane@example.com", "age": 25, "active": False, "created_at": "2024-02-10"}

search.index_document("users", "user_1", user1)
search.index_document("users", "user_2", user2)
```

### Searching
```python
# Perform a search
results = search.search("users", "John")
for result in results:
    print(result)
```

### Managing Indices
```python
# List all indices
print(search.list_indices())

# Get index statistics
print(search.get_index_stats("users"))

# Delete an index
search.delete_index("users")
```

### Clearing Cache
```python
# Clear the search cache
search.clear_cache()
```

## Example
## Examples

### Example 1: Basic Search
```python
from src.modules.fast_search.fast_search import FastSearchModule

# Initialize the search module
search = FastSearchModule(data_dir="search_data", enable_caching=True)

# Define a mapping and create an index
user_mapping = {
    "name": {"type": "text"},
    "email": {"type": "keyword"},
    "age": {"type": "integer"},
    "active": {"type": "boolean"},
    "created_at": {"type": "date"}
}
search.create_index("users", user_mapping)

# Index some documents
user1 = {"name": "Alice Johnson", "email": "alice@example.com", "age": 28, "active": True, "created_at": "2024-03-01"}
user2 = {"name": "Bob Brown", "email": "bob@example.com", "age": 35, "active": False, "created_at": "2024-03-05"}
search.index_document("users", "user_1", user1)
search.index_document("users", "user_2", user2)

# Perform a search
results = search.search("users", "Alice")
for result in results:
    print(result)
```
Example 2: Managing Indices
```python
# List all indices
print(search.list_indices())

# Get statistics for the "users" index
print(search.get_index_stats("users"))

# Delete the "users" index
search.delete_index("users")
```
Example 3: Clearing Cache
```python
# Clear the search cache
search.clear_cache()
```