from collections import defaultdict


class IndexData:
    """Container for index data"""

    def __init__(self):
        self.documents = {}
        self.inverted_index = defaultdict(set)
        self.term_frequencies = defaultdict(self._create_int_defaultdict)
        self.document_count = 0
        self.term_doc_count = defaultdict(int)

    def _create_int_defaultdict(self):
        """Create a defaultdict for integers - needed for pickle serialization"""
        return defaultdict(int)