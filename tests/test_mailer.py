from unittest.mock import patch, MagicMock
from src.mailer import send_email


@patch("src.mailer.smtplib.SMTP_SSL")
def test_send_email_ssl(mock_smtp_class):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    email_config = {
        "smtp_host": "smtp.163.com",
        "smtp_port": 465,
        "smtp_user": "sender@163.com",
        "smtp_pass": "secret",
        "recipient": "to@163.com"
    }

    result = send_email("<h1>Test</h1>", "Subject Line", email_config)

    assert result is True
    mock_smtp_class.assert_called_once_with("smtp.163.com", 465, timeout=30)
    mock_server.login.assert_called_once_with("sender@163.com", "secret")
    mock_server.sendmail.assert_called_once()

    call_args = mock_server.sendmail.call_args
    assert call_args[0][0] == "sender@163.com"
    assert call_args[0][1] == "to@163.com"
    assert "Subject Line" in call_args[0][2]


@patch("src.mailer.smtplib.SMTP_SSL")
def test_send_email_ssl_auth_failure(mock_smtp_class):
    mock_server = MagicMock()
    mock_server.login.side_effect = Exception("Auth failed")
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    email_config = {
        "smtp_host": "smtp.163.com",
        "smtp_port": 465,
        "smtp_user": "bad@163.com",
        "smtp_pass": "wrong",
        "recipient": "to@163.com"
    }

    import pytest
    with pytest.raises(Exception):
        send_email("<h1>Test</h1>", "Subject", email_config)


@patch("src.mailer.smtplib.SMTP")
def test_send_email_tls(mock_smtp_class):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    email_config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "s@gmail.com",
        "smtp_pass": "p",
        "recipient": "r@gmail.com"
    }

    result = send_email("<h1>Test</h1>", "Subject", email_config)
    assert result is True
    mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
    mock_server.starttls.assert_called_once()
