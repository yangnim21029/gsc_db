#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
對 GSCClient 中認證邏輯的單元測試。

這些測試專門驗證 authenticate 方法在不同情境下的行為，
例如：處理已有的 token、刷新 token、以及啟動新的 OAuth 流程。
"""

from unittest.mock import MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials

from src.services.gsc_client import GSCClient


@pytest.fixture
def mock_db():
    """提供一個模擬的 Database 實例。"""
    db = MagicMock()
    db.get_api_usage.return_value = 0
    return db


@patch("src.services.gsc_client.build")
def test_auth_with_existing_valid_token(mock_build, mock_db):
    """測試當存在有效的 token.json 文件時的行為。"""
    mock_creds = MagicMock(spec=Credentials)
    mock_creds.valid = True

    with patch("src.services.gsc_client.os.path.exists", return_value=True):
        with patch(
            "src.services.gsc_client.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ) as mock_from_file:
            with patch("src.services.gsc_client.InstalledAppFlow") as mock_flow:
                client = GSCClient(mock_db)
                client.authenticate()

                mock_from_file.assert_called_once()
                mock_flow.from_client_secrets_file.assert_not_called()
                mock_build.assert_called_once_with("searchconsole", "v1", credentials=mock_creds)
                assert client.is_authenticated()


@patch("src.services.gsc_client.build")
def test_auth_with_expired_token_and_successful_refresh(mock_build, mock_db):
    """測試當 token.json 過期但可以成功刷新時的行為。"""
    mock_creds = MagicMock(spec=Credentials)
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "some_refresh_token"
    mock_creds.to_json.return_value = '{"token": "mock_token"}'  # Return valid JSON string

    # 設定 refresh 後 credentials 變為 valid
    def make_valid_after_refresh(*args, **kwargs):
        mock_creds.valid = True

    mock_creds.refresh.side_effect = make_valid_after_refresh

    with patch("src.services.gsc_client.os.path.exists", return_value=True):
        with patch(
            "src.services.gsc_client.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ):
            client = GSCClient(mock_db)
            client.authenticate()

            mock_creds.refresh.assert_called_once()
            mock_build.assert_called_once_with("searchconsole", "v1", credentials=mock_creds)
            assert client.is_authenticated()


@patch("src.services.gsc_client.build")
def test_auth_with_no_token_starts_new_flow(mock_build, mock_db):
    """測試當沒有 token.json 時，會啟動新的認證流程。"""
    mock_new_creds = MagicMock(spec=Credentials)
    mock_flow_instance = MagicMock()
    mock_flow_instance.run_local_server.return_value = mock_new_creds

    with patch("src.services.gsc_client.os.path.exists", return_value=False):
        with patch(
            "src.services.gsc_client.InstalledAppFlow.from_client_secrets_file",
            return_value=mock_flow_instance,
        ) as mock_from_secrets:
            # 模擬保存 token 的 open 函數
            with patch("builtins.open", MagicMock()):
                client = GSCClient(mock_db)
                client.authenticate()

                mock_from_secrets.assert_called_once()
                mock_flow_instance.run_local_server.assert_called_once()
                mock_build.assert_called_once_with(
                    "searchconsole", "v1", credentials=mock_new_creds
                )
                assert client.is_authenticated()


@patch("src.services.gsc_client.build")
def test_auth_raises_error_if_client_secret_is_missing(mock_build, mock_db):
    """測試當 client_secret.json 缺失時，會拋出 FileNotFoundError。"""
    with patch("src.services.gsc_client.os.path.exists", return_value=False):
        with patch(
            "src.services.gsc_client.InstalledAppFlow.from_client_secrets_file",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(FileNotFoundError):
                client = GSCClient(mock_db)
                client.authenticate()
