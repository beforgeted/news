from unittest.mock import patch, MagicMock
from src.mailer import send_email


@patch("src.mailer.smtplib.SMTP")
def test_send_email(mock_smtp_class):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    email_config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "sender@gmail.com",
        "smtp_pass": "secret",
        "recipient": "to@gmail.com"
    }

    result = send_email("<h1>Test</h1>", "Subject Line", email_config)

    assert result is True
    mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("sender@gmail.com", "secret")
    mock_server.sendmail.assert_called_once()

    call_args = mock_server.sendmail.call_args
    assert call_args[0][0] == "sender@gmail.com"
    assert call_args[0][1] == "to@gmail.com"
    assert "Subject Line" in call_args[0][2]


@patch("src.mailer.smtplib.SMTP")
def test_send_email_raises_on_auth_failure(mock_smtp_class):
    mock_server = MagicMock()
    mock_server.login.side_effect = Exception("Auth failed")
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    email_config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "bad@gmail.com",
        "smtp_pass": "wrong",
        "recipient": "to@gmail.com"
    }

    import pytest
    with pytest.raises(Exception):
        send_email("<h1>Test</h1>", "Subject", email_config)
