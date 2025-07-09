"""CLI connection testing tools for IMAP server."""

import imaplib
import ssl
from mcp.server.fastmcp import FastMCP
from ..shared.credentials import CredentialManager
from datetime import datetime


def register_cli_testing_tools(mcp: FastMCP):
    """Register CLI testing tools with the MCP server."""

    @mcp.tool()
    async def test_imap_connection_with_credentials(email: str):
        """
        Test IMAP connection using stored credentials for a specific email account.

        Args:
            email: Email address to test connection for
        """
        try:
            # Get stored credentials
            cred_manager = CredentialManager()
            account = cred_manager.get_account(email)
            if not account:
                return f"No credentials found for {email}. Use add_imap_account first."

            # Parse server info (format: server:port:ssl)
            try:
                server_parts = account.server.split(":")
                imap_server = server_parts[0]
                imap_port = int(server_parts[1]) if len(server_parts) > 1 else 993
                use_ssl = (
                    server_parts[2].lower() == "true" if len(server_parts) > 2 else True
                )
            except (ValueError, IndexError):
                # Default values if parsing fails
                imap_server = account.server
                imap_port = 993
                use_ssl = True

            # Test the connection
            result = await test_imap_connection_direct(
                email=account.username,
                password=account.password,
                imap_server=imap_server,
                imap_port=imap_port,
                use_ssl=use_ssl,
            )
        except Exception as e:
            return f"Failed to test connection for {email}: {e!s}"
        else:
            return result

    @mcp.tool()
    async def test_imap_connection_direct(
        email: str,
        password: str,
        imap_server: str,
        imap_port: int = 993,
        use_ssl: bool = True,
    ):
        """
        Test IMAP connection with provided credentials (without storing them).

        Args:
            email: Email address
            password: Email password or app password
            imap_server: IMAP server hostname
            imap_port: IMAP port (default: 993 for SSL)
            use_ssl: Whether to use SSL connection (default: True)
        """
        connection_info = {
            "email": email,
            "server": imap_server,
            "port": imap_port,
            "ssl": use_ssl,
        }

        try:
            # Create IMAP connection
            if use_ssl:
                mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            else:
                mail = imaplib.IMAP4(imap_server, imap_port)

            # Test login
            try:
                mail.login(email, password)
                login_success = True
                login_error = None
            except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
                login_success = False
                login_error = str(e)

            # Test folder listing
            try:
                folders = mail.list()
                folder_success = True
                folder_error = None
                folder_count = len(folders[1]) if folders[1] else 0
            except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
                folder_success = False
                folder_error = str(e)
                folder_count = 0

            # Test selecting INBOX
            try:
                mail.select("INBOX")
                inbox_success = True
                inbox_error = None
            except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
                inbox_success = False
                inbox_error = str(e)

            # Logout
            mail.logout()

            # Determine overall success
            overall_success = login_success and folder_success and inbox_success

            result = {
                "message": "Connection test completed",
                "success": overall_success,
                "tests": {
                    "login": {"success": login_success, "error": login_error},
                    "folder_listing": {
                        "success": folder_success,
                        "error": folder_error,
                        "folder_count": folder_count,
                    },
                    "inbox_access": {"success": inbox_success, "error": inbox_error},
                },
                **connection_info,
            }

            if overall_success:
                result["message"] = "All connection tests passed successfully"
            else:
                result["message"] = "Some connection tests failed"
        except ssl.SSLError as e:
            return {
                "message": "SSL connection test failed",
                "success": False,
                "stage": "ssl_connection",
                "error": f"SSL Error: {e!s}",
                **connection_info,
            }
        except OSError as e:
            return {
                "message": "Network connection test failed",
                "success": False,
                "stage": "network_connection",
                "error": f"Network Error: {e!s}",
                **connection_info,
            }
        except Exception as e:
            return {
                "message": "Connection test failed",
                "success": False,
                "stage": "unknown",
                "error": f"Error: {e!s}",
                **connection_info,
            }
        else:
            return result

    @mcp.tool()
    async def diagnose_imap_connection(email: str):
        """
        Perform comprehensive IMAP connection diagnostics for a stored account.

        Args:
            email: Email address to diagnose
        """
        try:
            # Get stored credentials
            cred_manager = CredentialManager()
            account = cred_manager.get_account(email)
            if not account:
                return f"No credentials found for {email}. Use add_imap_account first."

            # Parse server info (format: server:port:ssl)
            try:
                server_parts = account.server.split(":")
                imap_server = server_parts[0]
                imap_port = int(server_parts[1]) if len(server_parts) > 1 else 993
                use_ssl = (
                    server_parts[2].lower() == "true" if len(server_parts) > 2 else True
                )
            except (ValueError, IndexError):
                # Default values if parsing fails
                imap_server = account.server
                imap_port = 993
                use_ssl = True

            # Run comprehensive diagnostics
            diagnostics = {
                "message": "IMAP connection diagnostics completed",
                "timestamp": datetime.now().isoformat(),
                "tests": {},
            }

            # Test 1: Basic connection
            try:
                if use_ssl:
                    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
                else:
                    mail = imaplib.IMAP4(imap_server, imap_port)
                diagnostics["tests"]["connection"] = {"success": True, "error": None}
            except Exception as e:
                diagnostics["tests"]["connection"] = {"success": False, "error": str(e)}
                return diagnostics

            # Test 2: Authentication
            try:
                mail.login(account.username, account.password)
                diagnostics["tests"]["authentication"] = {
                    "success": True,
                    "error": None,
                }
            except Exception as e:
                diagnostics["tests"]["authentication"] = {
                    "success": False,
                    "error": str(e),
                }
                mail.logout()
                return diagnostics

            # Test 3: Folder operations
            try:
                folders = mail.list()
                diagnostics["tests"]["folder_listing"] = {
                    "success": True,
                    "error": None,
                    "folder_count": len(folders[1]) if folders[1] else 0,
                }
            except Exception as e:
                diagnostics["tests"]["folder_listing"] = {
                    "success": False,
                    "error": str(e),
                }

            # Test 4: INBOX access
            try:
                mail.select("INBOX")
                diagnostics["tests"]["inbox_access"] = {"success": True, "error": None}
            except Exception as e:
                diagnostics["tests"]["inbox_access"] = {
                    "success": False,
                    "error": str(e),
                }

            # Test 5: Message operations
            try:
                # Try to fetch a small number of messages
                messages = mail.search(None, "ALL")
                if messages[0] == "OK":
                    message_count = len(messages[1][0].split()) if messages[1][0] else 0
                    diagnostics["tests"]["message_operations"] = {
                        "success": True,
                        "error": None,
                        "message_count": message_count,
                    }
                else:
                    diagnostics["tests"]["message_operations"] = {
                        "success": False,
                        "error": "Failed to search messages",
                    }
            except Exception as e:
                diagnostics["tests"]["message_operations"] = {
                    "success": False,
                    "error": str(e),
                }

            # Cleanup
            try:
                mail.logout()
            except Exception:
                pass  # Ignore logout errors

            # Calculate overall success
            successful_tests = sum(
                1
                for test in diagnostics["tests"].values()
                if test.get("success", False)
            )
            total_tests = len(diagnostics["tests"])

            if successful_tests == total_tests:
                diagnostics["message"] = "All diagnostic tests passed"
                diagnostics["overall_success"] = True
            else:
                diagnostics["message"] = (
                    f"Diagnostic tests completed - {successful_tests}/{total_tests} passed"
                )
                diagnostics["overall_success"] = False

        except Exception as e:
            return {
                "message": "Diagnostic test failed",
                "error": f"Unexpected error: {e!s}",
                "overall_success": False,
            }
        else:
            return diagnostics
