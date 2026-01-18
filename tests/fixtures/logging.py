"""Logging utilities for tests."""


class CapturedRequestLog:
    """Log of requests and responses for snapshot assertions.

    The log captures the raw bytes of each request and response along with
    a label indicating the direction of the message.
    """

    def __init__(self) -> None:
        """Initialize the request log."""
        self.entries: list[tuple[str, bytes]] = []

    def add_log_entry(self, label: str, data: bytes) -> None:
        """Add a request entry."""
        self.entries.append((label, data))

    def __repr__(self):
        """Return a string representation of the log entries.

        This assumes that the client will behave in a request-response manner,
        so each request is followed by a response. If a test uses non-deterministic
        message order, this may not be accurate and the test would need to decode
        the raw messages and remove any ordering assumptions.
        """
        lines = []
        for label, data in self.entries:
            lines.append(label)
            lines.extend(self._hexdump(data))
        return "\n".join(lines)

    def _hexdump(self, data: bytes, bytes_per_line: int = 16) -> list[str]:
        """Print a hexdump of the given bytes object in a tcpdump/hexdump -C style.

        This makes the packets easier to read and compare in test snapshots.

        Args:
            data: The bytes object to print.
            bytes_per_line: The number of bytes to display per line (default is 16).
        """

        # Use '.' for non-printable characters (ASCII < 32 or > 126)
        def to_printable_ascii(byte_val):
            return chr(byte_val) if 32 <= byte_val <= 126 else "."

        offset = 0
        lines = []
        while offset < len(data):
            chunk = data[offset : offset + bytes_per_line]
            # Format the hex values, space-padded to ensure alignment
            hex_values = " ".join(f"{byte:02x}" for byte in chunk)
            # Pad hex string to a fixed width so ASCII column lines up
            # 3 chars per byte ('xx ') for a full line of 16 bytes
            padded_hex = f"{hex_values:<{bytes_per_line * 3}}"
            # Format the ASCII values
            ascii_values = "".join(to_printable_ascii(byte) for byte in chunk)
            lines.append(f"{offset:08x}  {padded_hex} |{ascii_values}|")
            offset += bytes_per_line
        return lines
