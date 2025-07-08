"""IMAP credential management using secure keyring storage."""

import keyring
import tomllib
import tomli_w
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
import os


@dataclass
class AccountCredentials:
    """IMAP account credentials."""

    username: str
    password: str
    server: str


class CredentialManager:
    """Manages IMAP credentials with secure keyring storage."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or str(
            Path.home() / ".config" / "mcp-imap-server" / "config.toml"
        )
        self.keyring_service = "mcp-imap-server"

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists."""
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_config(self) -> Dict:
        """Read configuration from TOML file."""
        if not os.path.exists(self.config_file):
            return {}

        try:
            with open(self.config_file, "rb") as f:
                return tomllib.load(f)
        except Exception:
            return {}

    def _write_config(self, config: Dict) -> None:
        """Write configuration to TOML file."""
        self._ensure_config_dir()
        with open(self.config_file, "wb") as f:
            tomli_w.dump(config, f)

    def _get_keyring_key(self, account_name: str) -> str:
        """Get the keyring key for an account."""
        return f"account:{account_name}"

    def _migrate_plaintext_password(self, name: str, password: str) -> None:
        """Migrate a plaintext password to keyring storage."""
        try:
            keyring.set_password(
                self.keyring_service, self._get_keyring_key(name), password
            )
        except Exception as e:
            raise RuntimeError(f"Failed to store password in keyring: {e}")

    def add_account(self, name: str, username: str, password: str, server: str) -> None:
        """Add or update an IMAP account."""
        # Store password in keyring
        try:
            keyring.set_password(
                self.keyring_service, self._get_keyring_key(name), password
            )
        except Exception as e:
            raise RuntimeError(f"Failed to store password in keyring: {e}")

        # Store account metadata in config file (without password)
        config = self._read_config()

        if "accounts" not in config:
            config["accounts"] = {}

        config["accounts"][name] = {
            "username": username,
            "server": server,
        }

        try:
            self._write_config(config)
        except Exception as e:
            # Try to clean up keyring entry if config write fails
            try:
                keyring.delete_password(
                    self.keyring_service, self._get_keyring_key(name)
                )
            except Exception:
                pass
            raise RuntimeError(f"Failed to save account config: {e}")

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


# Global instance
credential_manager = CredentialManager()
