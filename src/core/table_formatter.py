from typing import List, Dict, Any
from colorama import Fore, Style


class TableFormatter:
    """Utility class for formatting data as tables in the console"""

    @staticmethod
    def format_records_as_table(records: List, title: str = "Records") -> List[str]:
        """Format a list of records as a table"""
        if not records:
            return [f"{Fore.YELLOW}📭 No records found{Style.RESET_ALL}"]

        result = []
        result.append(f"\n{Fore.BLUE}📊 {title} ({len(records)} total):{Style.RESET_ALL}")

        # Extract all field names from all records
        all_fields = set()
        multi_value_fields = set()

        # First pass: collect all possible field names
        for record in records:
            if hasattr(record, 'fields'):
                all_fields.update(record.fields.keys())
            if hasattr(record, 'multi_value_fields'):
                multi_value_fields.update(record.multi_value_fields.keys())

        # Sort fields for consistent display
        all_fields = sorted(list(all_fields))
        multi_value_fields = sorted(list(multi_value_fields))

        # Filter out common method names and internal attributes
        excluded_attrs = {'id', '_id', '_book_type', 'save', 'load', 'get', 'add', 'delete', 'update'}
        filtered_fields = [f for f in all_fields if f not in excluded_attrs]

        # All columns we'll display
        columns = filtered_fields + multi_value_fields

        # Calculate column widths (min 15 characters)
        col_widths = {field: max(15, len(field)) for field in columns}

        for record in records:
            for field in filtered_fields:  # Use filtered_fields instead of all_fields
                if field in record.fields:
                    value_str = str(record.fields.get(field, ''))
                    col_widths[field] = max(col_widths[field], len(value_str))

            for field in multi_value_fields:
                if field in record.multi_value_fields and record.multi_value_fields[field]:
                    # Format multi-value fields
                    values = record.multi_value_fields[field]
                    if isinstance(values, dict):
                        value_str = ", ".join(values.keys())
                    else:
                        value_str = str(values)
                    col_widths[field] = max(col_widths[field], len(value_str))

        # Create header
        header = f"{Fore.CYAN}│ "
        for field in columns:
            header += f"{field.ljust(col_widths[field])} │ "
        result.append(header + Style.RESET_ALL)

        # Create separator
        separator = f"{Fore.YELLOW}├─"
        for field in columns:
            separator += "─" * col_widths[field] + "─┼─"
        separator = separator[:-2] + "┤" + Style.RESET_ALL
        result.append(separator)

        # Add each record
        for i, record in enumerate(records):
            row = f"{Fore.GREEN}│ "
            for field in columns:
                # Handle regular fields
                if field in filtered_fields:  # Use filtered_fields instead of all_fields
                    value = record.fields.get(field, '')
                    row += f"{str(value).ljust(col_widths[field])} │ "
                # Handle multi-value fields
                elif field in multi_value_fields:
                    if field in record.multi_value_fields and record.multi_value_fields[field]:
                        # Format multi-value fields
                        values = record.multi_value_fields[field]
                        if isinstance(values, dict):
                            value_str = ", ".join(values.keys())
                        else:
                            value_str = str(values)
                        row += f"{value_str.ljust(col_widths[field])} │ "
                    else:
                        row += f"{''.ljust(col_widths[field])} │ "
                else:
                    row += f"{''.ljust(col_widths[field])} │ "
            result.append(row + Style.RESET_ALL)

        return result
