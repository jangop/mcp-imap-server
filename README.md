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

### 🎯 Intelligent Content Processing

- **Smart Content Selection**: Automatically chooses plaintext or HTML-to-markdown based on content quality
- **Stub Detection**: Identifies placeholder text (e.g., "view in browser") and uses HTML content instead
- **Token Efficiency**: Reduces token usage by 60-80% through intelligent content selection
- **Format Flexibility**: Five content format options for different client needs:
  - `default` - Smart selection: meaningful plaintext or HTML-to-markdown
  - `original_plaintext` - Raw plaintext content
  - `original_html` - Raw HTML content  
  - `markdown_from_html` - Clean markdown converted from HTML
  - `all` - All available formats for maximum flexibility

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

Depending on your setup, you probably want your agent to handle the server,
so you will not need to install/launch manually.
However, to manage credentials (your imap server, username, and password),
you should use the command line interface.

With [uv](https://github.com/astral-sh/uv), this becomes trivial.

### Prerequisites

- [Install uv](https://docs.astral.sh/uv/getting-started/installation/) if you have not done so already.

### Add Credentials via the Command Line Interface

Use `uvx` to [invoke the application without installing](https://docs.astral.sh/uv/guides/tools/) it:

```bash
uvx --from git+https://github.com/jangop/mcp-imap-server mcp-imap-credentials add
```

Enter your credentials as requested.
They will be stored locally and securely.

Alternatively, install the application -- but why?

### Run MCP Server

You could use `uv`/`uvx` to install/run the server, but you probably want your agent (the MCP client) to handle it.

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

#### Gemini CLI

For example, to configure [Gemini CLI](https://github.com/google-gemini/gemini-cli) to use this server,
place the following in `~/.gemini/extensions/mcp-imap-server/gemini-extension.json`,
to [install the server as an extension](https://github.com/google-gemini/gemini-cli/blob/main/docs/extension.md):

```json
{
  "name": "mcp-imap-server",
  "version": "0.0.1",
  "mcpServers": {
    "mcp-imap-server": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/jangop/mcp-imap-server", "mcp-imap-server"]
    }
  }
}
```

Then, just [launch Gemini CLI](https://github.com/google-gemini/gemini-cli?tab=readme-ov-file#quickstart):

```bash
npx https://github.com/google-gemini/gemini-cli
```

## MCP Tools Available

### Authentication

- `login(username, password, server)` - Connect to IMAP server
- `logout()` - Disconnect from server
- `list_stored_accounts()` - List configured accounts

### Email Operations

- `list_emails(limit, headers_only, content_format)` - List recent emails with intelligent content processing
- `filter_emails_by_sender(sender, limit, headers_only, content_format)` - Filter emails by sender
- `filter_emails_by_subject(subject, limit, headers_only, content_format)` - Filter emails by subject
- `get_recent_emails(count, headers_only, content_format)` - Get most recent emails
- `read_email(uid, content_format)` - Get specific email with full content
- `mark_as_read(uid)` - Mark email as read
- `delete_email(uid, expunge)` - Delete email
- `bulk_mark_as_read(uids)` - Mark multiple emails as read

### Search Operations

- `search_emails_by_date_range(start_date, end_date, headers_only, content_format)` - Search by date
- `search_emails_by_size(min_size, max_size, headers_only, content_format)` - Search by size
- `search_emails_by_body_text(search_text, headers_only, content_format)` - Search in body/subject
- `search_emails_with_attachments(min_attachments, headers_only, content_format)` - Find emails with attachments
- `search_emails_by_flags(seen, flagged, deleted, headers_only, content_format)` - Search by flags
- `advanced_email_search(..., content_format)` - Combined search with multiple criteria

### Folder Management

- `list_folders()` - List all folders
- `select_folder(folder_name)` - Switch to folder
- `get_folder_statistics(folder_name)` - Get folder stats
- `get_emails_paginated(page, page_size, folder_name, headers_only, content_format)` - Paginated email retrieval
- `search_emails_paginated(search_criteria, page, page_size, headers_only, content_format)` - Paginated search results
- `get_emails_by_flag_paginated(flag, page, page_size, headers_only, content_format)` - Paginated flag-based retrieval

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
│   │   ├── content_processing.py  # Intelligent content processing & formatting
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
