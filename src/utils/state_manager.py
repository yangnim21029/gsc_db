#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .. import config

logger = logging.getLogger(__name__)

STATE_FILE_PATH = Path(config.CONFIG_DIR) / 'sync_state.json'


class StateManager:
    @staticmethod
    def save_sync_state(state: Dict[str, Any]):
        """將給定的狀態字典保存到 JSON 文件中"""
        try:
            STATE_FILE_PATH.write_text(json.dumps(state, indent=4), encoding='utf-8')
            logger.debug(f"Sync state saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    @staticmethod
    def load_sync_state() -> Optional[Dict[str, Any]]:
        """從 JSON 文件加載同步狀態"""
        if not STATE_FILE_PATH.exists():
            return None
        try:
            state = json.loads(STATE_FILE_PATH.read_text(encoding='utf-8'))
            logger.debug(f"Sync state loaded successfully.")
            return state
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load or parse sync state file, starting fresh: {e}")
            # 如果文件損壞，將其清除
            StateManager.clear_sync_state()
            return None

    @staticmethod
    def clear_sync_state():
        """清除（刪除）同步狀態文件"""
        try:
            if STATE_FILE_PATH.exists():
                STATE_FILE_PATH.unlink()
                logger.debug("Sync state file cleared.")
        except OSError as e:
            logger.error(f"Error clearing sync state file: {e}")