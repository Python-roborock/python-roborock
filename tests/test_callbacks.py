"""Tests for the callbacks module."""

import logging
from unittest.mock import Mock

from roborock.callbacks import CallbackList, CallbackMap, safe_callback


def test_safe_callback_successful_execution():
    """Test that safe_callback executes callback successfully."""
    mock_callback = Mock()
    wrapped = safe_callback(mock_callback)

    wrapped("test_value")

    mock_callback.assert_called_once_with("test_value")


def test_safe_callback_catches_exception():
    """Test that safe_callback catches and logs exceptions."""

    def failing_callback(value):
        raise ValueError("Test exception")

    mock_logger = Mock(spec=logging.Logger)
    wrapped = safe_callback(failing_callback, mock_logger)

    # Should not raise exception
    wrapped("test_value")

    mock_logger.error.assert_called_once()
    assert "Uncaught error in callback" in mock_logger.error.call_args[0][0]


def test_safe_callback_uses_default_logger():
    """Test that safe_callback uses default logger when none provided."""

    def failing_callback(value):
        raise ValueError("Test exception")

    wrapped = safe_callback(failing_callback)

    # Should not raise exception
    wrapped("test_value")


# CallbackMap tests


def test_callback_map_add_callback_and_invoke():
    """Test adding callback and invoking it."""
    callback_map = CallbackMap[str, str]()
    mock_callback = Mock()

    remove_fn = callback_map.add_callback("key1", mock_callback)
    callback_map("key1", "test_value")

    mock_callback.assert_called_once_with("test_value")
    assert callable(remove_fn)


def test_callback_map_multiple_callbacks_same_key():
    """Test multiple callbacks for the same key."""
    callback_map = CallbackMap[str, str]()
    mock_callback1 = Mock()
    mock_callback2 = Mock()

    callback_map.add_callback("key1", mock_callback1)
    callback_map.add_callback("key1", mock_callback2)
    callback_map("key1", "test_value")

    mock_callback1.assert_called_once_with("test_value")
    mock_callback2.assert_called_once_with("test_value")


def test_callback_map_different_keys():
    """Test callbacks for different keys."""
    callback_map = CallbackMap[str, str]()
    mock_callback1 = Mock()
    mock_callback2 = Mock()

    callback_map.add_callback("key1", mock_callback1)
    callback_map.add_callback("key2", mock_callback2)

    callback_map("key1", "value1")
    callback_map("key2", "value2")

    mock_callback1.assert_called_once_with("value1")
    mock_callback2.assert_called_once_with("value2")


def test_callback_map_get_callbacks():
    """Test getting callbacks for a key."""
    callback_map = CallbackMap[str, str]()
    mock_callback = Mock()

    # No callbacks initially
    assert callback_map.get_callbacks("key1") == []

    # Add callback
    callback_map.add_callback("key1", mock_callback)
    callbacks = callback_map.get_callbacks("key1")

    assert len(callbacks) == 1
    assert callbacks[0] == mock_callback


def test_callback_map_remove_callback():
    """Test removing callback."""
    callback_map = CallbackMap[str, str]()
    mock_callback = Mock()

    remove_fn = callback_map.add_callback("key1", mock_callback)

    # Callback should be there
    assert len(callback_map.get_callbacks("key1")) == 1

    # Remove callback
    remove_fn()

    # Callback should be gone
    assert callback_map.get_callbacks("key1") == []


def test_callback_map_remove_callback_cleans_up_key():
    """Test that removing last callback for a key removes the key."""
    callback_map = CallbackMap[str, str]()
    mock_callback = Mock()

    remove_fn = callback_map.add_callback("key1", mock_callback)

    # Key should exist
    assert "key1" in callback_map._callbacks

    # Remove callback
    remove_fn()

    # Key should be removed
    assert "key1" not in callback_map._callbacks


def test_callback_map_exception_handling(caplog):
    """Test that exceptions in callbacks are handled gracefully."""
    callback_map = CallbackMap[str, str]()

    def failing_callback(value):
        raise ValueError("Test exception")

    callback_map.add_callback("key1", failing_callback)

    with caplog.at_level(logging.ERROR):
        callback_map("key1", "test_value")

    assert "Uncaught error in callback" in caplog.text


def test_callback_map_custom_logger():
    """Test using custom logger."""
    mock_logger = Mock(spec=logging.Logger)
    callback_map = CallbackMap[str, str](logger=mock_logger)

    def failing_callback(value):
        raise ValueError("Test exception")

    callback_map.add_callback("key1", failing_callback)
    callback_map("key1", "test_value")

    mock_logger.error.assert_called_once()


# CallbackList tests


def test_callback_list_add_callback_and_invoke():
    """Test adding callback and invoking it."""
    callback_list = CallbackList[str]()
    mock_callback = Mock()

    remove_fn = callback_list.add_callback(mock_callback)
    callback_list("test_value")

    mock_callback.assert_called_once_with("test_value")
    assert callable(remove_fn)


def test_callback_list_multiple_callbacks():
    """Test multiple callbacks in the list."""
    callback_list = CallbackList[str]()
    mock_callback1 = Mock()
    mock_callback2 = Mock()

    callback_list.add_callback(mock_callback1)
    callback_list.add_callback(mock_callback2)
    callback_list("test_value")

    mock_callback1.assert_called_once_with("test_value")
    mock_callback2.assert_called_once_with("test_value")


def test_callback_list_remove_callback():
    """Test removing callback from list."""
    callback_list = CallbackList[str]()
    mock_callback1 = Mock()
    mock_callback2 = Mock()

    remove_fn1 = callback_list.add_callback(mock_callback1)
    callback_list.add_callback(mock_callback2)

    # Both should be called
    callback_list("test_value")
    assert mock_callback1.call_count == 1
    assert mock_callback2.call_count == 1

    # Remove first callback
    remove_fn1()

    # Only second should be called
    callback_list("test_value2")
    assert mock_callback1.call_count == 1  # Still 1
    assert mock_callback2.call_count == 2  # Now 2


def test_callback_list_exception_handling(caplog):
    """Test that exceptions in callbacks are handled gracefully."""
    callback_list = CallbackList[str]()

    def failing_callback(value):
        raise ValueError("Test exception")

    callback_list.add_callback(failing_callback)

    with caplog.at_level(logging.ERROR):
        callback_list("test_value")

    assert "Uncaught error in callback" in caplog.text


def test_callback_list_custom_logger():
    """Test using custom logger."""
    mock_logger = Mock(spec=logging.Logger)
    callback_list = CallbackList[str](logger=mock_logger)

    def failing_callback(value):
        raise ValueError("Test exception")

    callback_list.add_callback(failing_callback)
    callback_list("test_value")

    mock_logger.error.assert_called_once()
