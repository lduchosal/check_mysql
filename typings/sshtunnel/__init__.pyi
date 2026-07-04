"""Type stubs for sshtunnel (only the surface used by check_mysql)."""

from typing import Optional, Tuple

class BaseSSHTunnelForwarderError(Exception): ...
class HandlerSSHTunnelForwarderError(BaseSSHTunnelForwarderError): ...

class SSHTunnelForwarder:
    local_bind_port: int
    local_bind_host: str
    def __init__(
        self,
        ssh_address_or_host: Tuple[str, int] | str,
        *,
        ssh_username: Optional[str] = ...,
        ssh_password: Optional[str] = ...,
        ssh_pkey: Optional[str] = ...,
        ssh_private_key_password: Optional[str] = ...,
        remote_bind_address: Tuple[str, int] = ...,
        local_bind_address: Tuple[str, int] = ...,
    ) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def __enter__(self) -> "SSHTunnelForwarder": ...
    def __exit__(self, *args: object) -> None: ...
