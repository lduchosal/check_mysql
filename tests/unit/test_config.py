"""Unit tests for configuration loading."""

import pytest

from check_mysql.core.config import (
    _find_config_file,
    get_mysql_config,
    get_security_admins,
    get_security_allowlist,
    get_ssh_config,
    load_config,
    render_config,
    write_default_config,
)
from check_mysql.core.exceptions import ConfigurationError
from check_mysql.core.models import MySQLConfig, SSHConfig

_INI = """[mysql]
host = db.example.com
port = 3307
user = monitoring
password = secret
database = appdb
timeout = 5
"""

_INI_WITH_SSH = (
    _INI
    + """
[ssh]
host = bastion.example.com
port = 2222
user = tunnel
private_key = ~/.ssh/id_test
"""
)


def _write_config(tmp_path, content):
    """Write a config file into tmp_path and return its path as str."""
    ini = tmp_path / "check_mysql.ini"
    ini.write_text(content)
    return str(ini)


class TestLoadConfig:
    """Tests for load_config."""

    def test_load_from_absolute_path(self, tmp_path):
        """Load a config file given its absolute path."""
        config = load_config(_write_config(tmp_path, _INI))
        assert config.has_section("mysql")
        assert config["mysql"]["host"] == "db.example.com"

    def test_missing_file_raises(self, tmp_path):
        """A path that does not exist raises FileNotFoundError."""
        missing = tmp_path / "nope.ini"
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(str(missing))


class TestFindConfigFile:
    """Tests for _find_config_file."""

    def test_absolute_path_returned_as_is(self, tmp_path):
        """An absolute path is returned unchanged."""
        absolute = str(tmp_path / "x.ini")
        assert _find_config_file(absolute) == absolute

    def test_found_in_current_directory(self, tmp_path, monkeypatch):
        """A relative path is resolved against the current directory."""
        ini = _write_config(tmp_path, _INI)
        monkeypatch.chdir(tmp_path)
        assert _find_config_file("check_mysql.ini") == ini

    def test_falls_back_to_original_path(self, tmp_path, monkeypatch):
        """When nowhere to be found, the original relative path is returned."""
        monkeypatch.chdir(tmp_path)
        assert _find_config_file("absent.ini") == "absent.ini"


class TestGetMySQLConfig:
    """Tests for get_mysql_config."""

    def test_reads_the_mysql_section(self, tmp_path):
        """All [mysql] fields land in the dataclass."""
        config = load_config(_write_config(tmp_path, _INI))
        mysql = get_mysql_config(config)
        assert mysql.host == "db.example.com"
        assert mysql.port == 3307
        assert mysql.user == "monitoring"
        assert mysql.password == "secret"
        assert mysql.database == "appdb"
        assert mysql.timeout == 5

    def test_defaults_without_section(self, tmp_path):
        """A config without [mysql] yields the documented defaults."""
        config = load_config(_write_config(tmp_path, "[other]\nkey = 1\n"))
        mysql = get_mysql_config(config)
        assert mysql.host == "localhost"
        assert mysql.port == 3306
        assert mysql.user == "root"
        assert mysql.password == ""
        assert mysql.database is None
        assert mysql.timeout == 10

    def test_cli_overrides_win(self, tmp_path):
        """Hostname and port from the CLI override the file values."""
        config = load_config(_write_config(tmp_path, _INI))
        mysql = get_mysql_config(config, hostname="override.example.com", port=3310)
        assert mysql.host == "override.example.com"
        assert mysql.port == 3310


class TestWriteDefaultConfig:
    """Tests for write_default_config."""

    def test_creates_the_file_mode_600(self, tmp_path):
        """The template is written with owner-only permissions."""
        target = tmp_path / "check_mysql.ini"
        path = write_default_config(str(target))
        assert path == target
        assert target.stat().st_mode & 0o777 == 0o600

    def test_generated_file_is_loadable(self, tmp_path):
        """The generated file loads: [mysql] defaults, no active [ssh]."""
        target = tmp_path / "check_mysql.ini"
        write_default_config(str(target))
        config = load_config(str(target))
        mysql = get_mysql_config(config)
        assert mysql.host == "localhost"
        assert mysql.port == 3306
        assert mysql.user == "nagios"
        assert mysql.timeout == 10
        assert get_ssh_config(config) is None

    def test_template_documents_the_ssh_tunnel(self, tmp_path):
        """The commented [ssh] section ships with the template."""
        target = tmp_path / "check_mysql.ini"
        content = write_default_config(str(target)).read_text()
        for needle in ("#[ssh]", "#private_key", "bastion", "#password"):
            assert needle in content

    def test_refuses_to_overwrite(self, tmp_path):
        """An existing file is never clobbered without force."""
        target = tmp_path / "check_mysql.ini"
        target.write_text("[mysql]\nhost = keep-me\n")
        with pytest.raises(ConfigurationError, match="already exists"):
            write_default_config(str(target))
        assert "keep-me" in target.read_text()

    def test_force_overwrites(self, tmp_path):
        """With force the existing file is replaced by the template."""
        target = tmp_path / "check_mysql.ini"
        target.write_text("[mysql]\nhost = old\n")
        write_default_config(str(target), force=True)
        assert "change-me" in target.read_text()


class TestRenderConfig:
    """Tests for render_config."""

    def test_direct_config_round_trips(self, tmp_path):
        """Rendered direct settings reload identically; [ssh] stays commented."""
        mysql = MySQLConfig(host="db1", port=3307, user="mon", password="pw", timeout=5)
        content = render_config(mysql, None)
        assert "#[ssh]" in content

        config = load_config(_write_config(tmp_path, content))
        reloaded = get_mysql_config(config)
        assert reloaded == mysql
        assert get_ssh_config(config) is None

    def test_ssh_config_round_trips(self, tmp_path):
        """Rendered tunnel settings reload as an active [ssh] section."""
        mysql = MySQLConfig(host="10.0.0.12", user="mon", password="pw")
        ssh = SSHConfig(host="bastion", port=2222, user="tunnel", private_key="/k")
        config = load_config(_write_config(tmp_path, render_config(mysql, ssh)))

        reloaded = get_ssh_config(config)
        assert reloaded == ssh

    def test_database_and_ssh_password_lines_when_set(self):
        """Optional fields only appear when set."""
        mysql = MySQLConfig(database="appdb")
        ssh = SSHConfig(host="bastion", user="tunnel", password="pw")
        content = render_config(mysql, ssh)
        assert "database = appdb" in content
        assert "password = pw" in content
        assert "private_key" not in content


class TestGetSecurityAllowlist:
    """Tests for get_security_allowlist."""

    def test_no_section_returns_empty_set(self, tmp_path):
        """Without a [security] section nothing is exempted."""
        config = load_config(_write_config(tmp_path, _INI))
        assert not get_security_allowlist(config)

    def test_missing_allow_option_returns_empty_set(self, tmp_path):
        """An empty [security] section exempts nothing."""
        config = load_config(_write_config(tmp_path, _INI + "\n[security]\n"))
        assert not get_security_allowlist(config)

    def test_comma_separated_entries_are_split_and_stripped(self, tmp_path):
        """Entries split on commas, whitespace trimmed, % unescaped (raw read)."""
        content = _INI + "\n[security]\nallow = backup@10.0.0.5, dba@% ,\n"
        config = load_config(_write_config(tmp_path, content))
        assert get_security_allowlist(config) == frozenset({"backup@10.0.0.5", "dba@%"})

    def test_multiline_entries_are_accepted(self, tmp_path):
        """Indented continuation lines work like commas."""
        content = _INI + "\n[security]\nallow = backup@10.0.0.5\n\tdba@localhost\n"
        config = load_config(_write_config(tmp_path, content))
        assert get_security_allowlist(config) == frozenset(
            {"backup@10.0.0.5", "dba@localhost"}
        )


class TestGetSecurityAdmins:
    """Tests for get_security_admins."""

    def test_no_section_returns_empty_set(self, tmp_path):
        """Without a [security] section no admin is declared."""
        config = load_config(_write_config(tmp_path, _INI))
        assert not get_security_admins(config)

    def test_missing_admins_option_returns_empty_set(self, tmp_path):
        """An [security] section with only allow declares no admin."""
        config = load_config(
            _write_config(tmp_path, _INI + "\n[security]\nallow = x@y\n")
        )
        assert not get_security_admins(config)

    def test_entries_are_split_and_stripped(self, tmp_path):
        """Admin entries parse like the allowlist, % left unescaped."""
        content = _INI + "\n[security]\nadmins = dba@10.0.0.5, ops@% ,\n"
        config = load_config(_write_config(tmp_path, content))
        assert get_security_admins(config) == frozenset({"dba@10.0.0.5", "ops@%"})


class TestGetSSHConfig:
    """Tests for get_ssh_config."""

    def test_no_section_returns_none(self, tmp_path):
        """Without an [ssh] section the connection is direct."""
        config = load_config(_write_config(tmp_path, _INI))
        assert get_ssh_config(config) is None

    def test_reads_the_ssh_section(self, tmp_path):
        """All [ssh] fields land in the dataclass, key path expanded."""
        config = load_config(_write_config(tmp_path, _INI_WITH_SSH))
        ssh = get_ssh_config(config)
        assert ssh is not None
        assert ssh.host == "bastion.example.com"
        assert ssh.port == 2222
        assert ssh.user == "tunnel"
        assert ssh.password is None
        assert ssh.private_key is not None
        assert "~" not in ssh.private_key

    def test_missing_host_or_user_raises(self, tmp_path):
        """An [ssh] section without host or user is a configuration error."""
        config = load_config(
            _write_config(tmp_path, _INI + "\n[ssh]\nhost = bastion\n")
        )
        with pytest.raises(ConfigurationError, match="host and user"):
            get_ssh_config(config)

    def test_missing_credentials_raises(self, tmp_path):
        """An [ssh] section without password nor private_key is an error."""
        config = load_config(
            _write_config(tmp_path, _INI + "\n[ssh]\nhost = bastion\nuser = tunnel\n")
        )
        with pytest.raises(ConfigurationError, match="password or a private_key"):
            get_ssh_config(config)

    def test_password_only_is_accepted(self, tmp_path):
        """An [ssh] section with only a password is valid."""
        config = load_config(
            _write_config(
                tmp_path,
                _INI + "\n[ssh]\nhost = bastion\nuser = tunnel\npassword = pw\n",
            )
        )
        ssh = get_ssh_config(config)
        assert ssh is not None
        assert ssh.password == "pw"
        assert ssh.private_key is None
        assert ssh.port == 22
