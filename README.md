# MCP IMAP Server

A comprehensive Model Context Protocol (MCP) server for full-featured IMAP email management with advanced search, bulk operations, and secure credential storage.

## Features

### 🔐 Authentication & Security

- Secure credential storage using system keyring
- Support for multiple IMAP accounts
- SSL/TLS connection support
- Connection testing and diagnostics

### 📧 Email Operations

- **Basic Operations**: List, read, mark as read/unread, delete emails
- **Bulk Operations**: Mark multiple emails as read, delete in batches
- **Search**: Advanced search by date, size, sender, subject, body text, flags
- **Attachments**: Extract and save email attachments
- **Composition**: Create and save draft emails

### 📁 Folder Management

- List all mailboxes/folders
- Switch between folders
- Folder statistics and analytics
- Pagination support for large folders

### 🔍 Advanced Search Capabilities

- Date range searches
- Size-based filtering
- Text search in body and subject
- Flag-based filtering (read/unread, flagged, deleted, etc.)
- Attachment presence filtering
- Combined search criteria

## Installation

### MCP

Depending on your setup, you probably want your agent to handle the server.
Use the following in your configuration:

```json
  "mcpServers": {
    "mcp-imap-server": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/jangop/mcp-imap-server", "mcp-imap-server"]
    }
  }
```

### Command Line Interface

To manage credentials, install the package.

#### Prerequisites

- Python 3.13 or higher
- `uv` package manager (recommended)

#### Install with uv

```bash
# Clone the repository
git clone <repository-url>
cd mcp-imap-server

# Install dependencies
uv sync

# Install the package
uv pip install .
```

## Quick Start

### 1. Add an IMAP Account

```bash
# Add your first IMAP account
mcp-imap-credentials add your-email@example.com your-password imap.gmail.com

# For Gmail with app password (untested)
mcp-imap-credentials add your-email@gmail.com your-app-password imap.gmail.com

# For Outlook/Office365 (untested)
mcp-imap-credentials add your-email@outlook.com your-password outlook.office365.com
```

### 2. List and Test Accounts

```bash
# List all configured accounts with connection testing
mcp-imap-credentials list

# List without testing connections
mcp-imap-credentials list --no-test
```

### 3. Run the MCP Server

```bash
# Start the MCP server
mcp-imap-server
```

## CLI Commands

### Account Management

```sh
# Add a new account
mcp-imap-credentials add <email> <password> <server> [--port 993] [--no-ssl]

# Remove an account
mcp-imap-credentials remove <email>

# Update an account
mcp-imap-credentials update <email> [--password <new-password>] [--server <new-server>]

# Test connection for a stored account
mcp-imap-credentials test <email>
```

### Examples

```sh
# Add Gmail account
mcp-imap-credentials add user@gmail.com app-password imap.gmail.com

# Add Outlook account with custom port
mcp-imap-credentials add user@outlook.com password outlook.office365.com --port 993

# Update password for existing account
mcp-imap-credentials update user@gmail.com --password new-app-password
```

## MCP Tools Available

### Authentication

- `login(username, password, server)` - Connect to IMAP server
- `logout()` - Disconnect from server
- `list_stored_accounts()` - List configured accounts

### Email Operations

- `list_emails(limit, headers_only)` - List recent emails
- `get_email(uid)` - Get specific email details
- `mark_as_read(uid)` - Mark email as read
- `delete_email(uid, expunge)` - Delete email
- `bulk_mark_as_read(uids)` - Mark multiple emails as read

### Search Operations

- `search_emails_by_date_range(start_date, end_date)` - Search by date
- `search_emails_by_size(min_size, max_size)` - Search by size
- `search_emails_by_body_text(search_text)` - Search in body/subject
- `search_emails_with_attachments(min_attachments)` - Find emails with attachments
- `search_emails_by_flags(seen, flagged, deleted)` - Search by flags
- `advanced_email_search(...)` - Combined search with multiple criteria

### Folder Management

- `list_folders()` - List all folders
- `select_folder(folder_name)` - Switch to folder
- `get_folder_statistics(folder_name)` - Get folder stats

### Attachments

- `extract_attachments(uid, save_path, include_inline)` - Extract attachments

### Email Composition

- `append_email(folder, subject, from_address, to_addresses, ...)` - Create draft email

## Configuration

### Credential Storage

Credentials are securely stored using the system keyring:

- **Linux**: Uses `secretstorage` or `kwallet`
- **macOS**: Uses `keychain` (untested)
- **Windows**: Uses `win32crypt` (untested)

### Supported IMAP Servers

- **Gmail**: `imap.gmail.com:993` (untested)
- **Outlook/Office365**: `outlook.office365.com:993` (untested)
- **Yahoo**: `imap.mail.yahoo.com:993` (untested)
- **Custom servers**: Any IMAP server with SSL support

## Development

### Setup Development Environment

```bash
# Install development dependencies
uv sync --dev

# Run linting and formatting
uvx ruff check --fix && uvx ruff format

# Run tests (if available)
uvx pytest
```

### Project Structure

```
src/mcp_imap_server/
├── cli/                 # Command-line interface
│   ├── commands.py     # Account management commands
│   └── testing.py      # Connection testing tools
├── server/             # MCP server implementation
│   ├── auth.py         # Authentication tools
│   ├── compose.py      # Email composition
│   ├── email/          # Email operations
│   │   ├── attachments.py
│   │   ├── basic_operations.py
│   │   ├── bulk_operations.py
│   │   └── search.py
│   ├── folder/         # Folder management
│   │   ├── management.py
│   │   ├── pagination.py
│   │   └── statistics.py
│   └── state.py        # Server state management
└── shared/             # Shared utilities
    └── credentials.py  # Credential management
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting: `uvx ruff check --fix && uvx ruff format`
5. Submit a pull request

## Support

For issues and questions:

- Check the existing issues
- Create a new issue with detailed information
- Include your Python version and operating system
