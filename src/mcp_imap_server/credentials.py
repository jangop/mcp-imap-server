"""Credential management for IMAP accounts."""

import tomllib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from platformdirs import user_config_dir


@dataclass
class AccountCredentials:
    """Credentials for an IMAP account."""

    username: str
    password: str
    server: str


class CredentialManager:
    """Manages stored IMAP account credentials."""

    def __init__(self):
        """Initialize the credential manager."""
        self.config_dir = Path(user_config_dir("mcp-imap-server", "mcp"))
        self.config_file = self.config_dir / "accounts.toml"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _read_config(self) -> Dict:
        """Read the configuration file."""
        if not self.config_file.exists():
            return {}

        with open(self.config_file, "rb") as f:
            return tomllib.load(f)

    def _write_config(self, config: Dict) -> None:
        """Write the configuration file."""
        # Simple TOML formatting since tomllib doesn't support writing
        toml_content = []

        if "accounts" in config:
            for account_name, account_data in config["accounts"].items():
                # Quote account names that contain special characters
                if any(char in account_name for char in "@.-+"):
                    quoted_name = f'"{account_name}"'
                else:
                    quoted_name = account_name
                toml_content.append(f"[accounts.{quoted_name}]")
                toml_content.append(f'username = "{account_data["username"]}"')
                toml_content.append(f'password = "{account_data["password"]}"')
                toml_content.append(f'server = "{account_data["server"]}"')
                toml_content.append("")  # Empty line between accounts

        with open(self.config_file, "w") as f:
            f.write("\n".join(toml_content))

    def add_account(self, name: str, username: str, password: str, server: str) -> None:
        """Add or update an account's credentials."""
        config = self._read_config()

        if "accounts" not in config:
            config["accounts"] = {}

        config["accounts"][name] = {
            "username": username,
            "password": password,
            "server": server,
        }

        self._write_config(config)

    def get_account(self, name: str) -> Optional[AccountCredentials]:
        """Get credentials for a specific account."""
        config = self._read_config()

        if "accounts" not in config or name not in config["accounts"]:
            return None

        account_data = config["accounts"][name]
        return AccountCredentials(
            username=account_data["username"],
            password=account_data["password"],
            server=account_data["server"],
        )

    def list_accounts(self) -> List[str]:
        """List all stored account names."""
        config = self._read_config()

        if "accounts" not in config:
            return []

        return list(config["accounts"].keys())

    def remove_account(self, name: str) -> bool:
        """Remove an account's credentials."""
        config = self._read_config()

        if "accounts" not in config or name not in config["accounts"]:
            return False

        del config["accounts"][name]

        # Remove the accounts section if it's empty
        if not config["accounts"]:
            del config["accounts"]

        self._write_config(config)
        return True


# Global credential manager instance
credential_manager = CredentialManager()
