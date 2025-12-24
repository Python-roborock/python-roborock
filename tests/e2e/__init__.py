"""End-to-end tests package."""

pytest_plugins = [
    "tests.fixtures.logging_fixtures",
    "tests.fixtures.local_async_fixtures",
    "tests.fixtures.pahomqtt_fixtures",
    "tests.fixtures.aiomqtt_fixtures",
    "tests.fixtures.web_api_fixtures",
]
