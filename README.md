# Personal Assistant

A comprehensive personal information management system with autocomplete, fast search, and colored interface.

## 🌟 Features

- 📚 Multiple book types support (contacts, notes, etc.)
- 🔍 Fast search across all records
- ⌨️ Command auto-completion
- 🎨 Colorful CLI interface
- 🏷️ Tag management for notes
- 📱 Phone number management for contacts
- 💾 Automatic data persistence

## 🚀 Quick Start

```bash
python main.py
```

## 📖 Command Structure

Commands follow the pattern: `<action>-<book>-[subitem]`

Examples:
- `add-contact`
- `add-note-tag`
- `search-all`

## 🛠️ Available Commands

### Global Commands
- `help` - Show all available commands
- `search-all` - Search across all books
- `exit` - Save and exit

### Contact Commands
- `add-contact` - Add new contact
- `search-contacts` - Search contacts
- `update-contact` - Update existing contact
- `delete-contact` - Delete a contact
- `add-contact-phone` - Add phone to contact
- `delete-contact-phone` - Delete phone from contact

### Note Commands
- `add-note` - Add new note
- `search-notes` - Search notes
- `update-note` - Update existing note
- `delete-note` - Delete a note
- `add-note-tag` - Add tag to note
- `delete-note-tag` - Delete tag from note

## 📝 Usage Examples

### Adding a Contact
```bash
💬 Enter a command: add-contact
🔍 Command 'add-contact' requires arguments:
Enter firstname: John
Enter lastname: Doe
Enter email: john@example.com
Enter phone_number: +1234567890
```

### Searching Across All Books
```bash
💬 Enter a command: search-all
Enter query (min 3 chars): John
✅ Found 1 records matching 'John'
```

### Adding Tags to Notes
```bash
💬 Enter a command: add-note-tag
Enter title: Meeting notes
Enter tag: important
```

## 🔍 Search Features

- Minimum 3 characters required for search
- Searches across all fields
- Fast indexing for quick results
- Support for partial matches
- Case-insensitive search

## 🎨 Interface Features

- Color-coded output for better readability
- Emoji indicators for different operations
- Auto-completion suggestions
- Command history
- Interactive prompts

## 🔐 Data Persistence

All data is automatically saved:
- On normal exit
- When using the `exit` command
- On Ctrl+C interrupt

## ⚠️ Error Handling

- Graceful error messages
- Input validation
- Duplicate detection
- Required field validation

## 🎯 Tips

1. Use `help` to see all available commands
2. Use tab completion for faster command entry
3. Minimum 3 characters for search queries
4. Use Ctrl+C for safe exit at any time

## 🚫 Common Issues

- Search requires minimum 3 characters
- Commands must match the exact format
- Required fields cannot be empty
- Phone numbers must be in valid format