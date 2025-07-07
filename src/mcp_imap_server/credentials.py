"""Credential management for IMAP accounts using secure keyring storage."""

import tomllib
import tomlkit
import keyring
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
    """Manages IMAP account credentials with secure keyring password storage."""

    def __init__(self):
        """Initialize the credential manager."""
        self.config_dir = Path(user_config_dir("mcp-imap-server", "mcp"))
        self.config_file = self.config_dir / "accounts.toml"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.keyring_service = "mcp-imap-server"

    def _read_config(self) -> Dict:
        """Read the configuration file."""
        if not self.config_file.exists():
            return {}

        with open(self.config_file, "rb") as f:
            return tomllib.load(f)

    def _write_config(self, config: Dict) -> None:
        """Write the configuration file using tomlkit."""
        # Convert to tomlkit document for proper formatting
        doc = tomlkit.document()

        if "accounts" in config and config["accounts"]:
            accounts_table = tomlkit.table()

            for account_name, account_data in config["accounts"].items():
                account_table = tomlkit.table()
                account_table["username"] = account_data["username"]
                account_table["server"] = account_data["server"]
                # Note: passwords are stored in keyring, not in TOML

                accounts_table[account_name] = account_table

            doc["accounts"] = accounts_table

        with open(self.config_file, "w") as f:
            f.write(tomlkit.dumps(doc))

    def _get_keyring_key(self, account_name: str) -> str:
        """Generate keyring key for an account."""
        return f"account.{account_name}"

    def _migrate_plaintext_password(
        self, account_name: str, plaintext_password: str
    ) -> None:
        """Migrate a plaintext password from TOML to keyring."""
        try:
            keyring.set_password(
                self.keyring_service,
                self._get_keyring_key(account_name),
                plaintext_password,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to store password in keyring: {e}")

    def add_account(self, name: str, username: str, password: str, server: str) -> None:
        """Add or update an account's credentials."""
        config = self._read_config()

        if "accounts" not in config:
            config["accounts"] = {}

        # Store password securely in keyring
        try:
            keyring.set_password(
                self.keyring_service, self._get_keyring_key(name), password
            )
        except Exception as e:
            raise RuntimeError(f"Failed to store password in keyring: {e}")

        # Store account metadata in TOML (no password)
        config["accounts"][name] = {"username": username, "server": server}

        self._write_config(config)

    def get_account(self, name: str) -> Optional[AccountCredentials]:
        """Get credentials for a specific account."""
        config = self._read_config()

        if "accounts" not in config or name not in config["accounts"]:
            return None

        account_data = config["accounts"][name]

        # Check for legacy plaintext password in config (migration case)
        if "password" in account_data:
            # Migrate plaintext password to keyring
            plaintext_password = account_data["password"]
            self._migrate_plaintext_password(name, plaintext_password)

            # Remove password from TOML and update config
            del account_data["password"]
            self._write_config(config)

            password = plaintext_password
        else:
            # Get password from keyring
            try:
                password = keyring.get_password(
                    self.keyring_service, self._get_keyring_key(name)
                )
                if password is None:
                    raise RuntimeError(
                        f"Password not found in keyring for account '{name}'"
                    )
            except Exception as e:
                raise RuntimeError(f"Failed to retrieve password from keyring: {e}")

        return AccountCredentials(
            username=account_data["username"],
            password=password,
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

        # Remove password from keyring
        try:
            keyring.delete_password(self.keyring_service, self._get_keyring_key(name))
        except keyring.errors.PasswordDeleteError:
            # Password wasn't in keyring (maybe legacy account), continue anyway
            pass
        except Exception as e:
            # Log the warning but don't fail the removal
            print(f"Warning: Failed to remove password from keyring: {e}")

        # Remove account from config
        del config["accounts"][name]

        # Remove the accounts section if it's empty
        if not config["accounts"]:
            del config["accounts"]

        self._write_config(config)
        return True

    def get_keyring_info(self) -> Dict[str, str]:
        """Get information about the keyring backend being used."""
        try:
            backend = keyring.get_keyring()
            return {
                "backend": f"{backend.__class__.__module__}.{backend.__class__.__name__}",
                "name": getattr(backend, "name", "Unknown"),
                "priority": str(getattr(backend, "priority", "Unknown")),
            }
        except Exception as e:
            return {"error": str(e)}


# Global credential manager instance
credential_manager = CredentialManager()
