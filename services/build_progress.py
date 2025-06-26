#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3

logger = logging.getLogger(__name__)

class BuildProgress:
    """建置進度管理器"""
    
    def __init__(self, db_path='gsc_data.db'):
        self.db_path = db_path
        self.progress_file = 'build_progress.json'
        self.init_progress_table()
    
    def init_progress_table(self):
        """初始化進度追蹤表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS build_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT UNIQUE NOT NULL,
                        task_type TEXT NOT NULL,
                        site_id INTEGER,
                        site_name TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        status TEXT NOT NULL,
                        current_date TEXT,
                        total_dates INTEGER,
                        completed_dates INTEGER,
                        total_records INTEGER DEFAULT 0,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                ''')
                
                # 創建索引
                conn.execute('CREATE INDEX IF NOT EXISTS idx_task_id ON build_progress(task_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON build_progress(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_site_id ON build_progress(site_id)')
                
                conn.commit()
                logger.info("Build progress table initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize progress table: {e}")
    
    def start_task(self, task_id: str, task_type: str, site_id: Optional[int] = None, 
                   site_name: Optional[str] = None, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, total_dates: int = 0) -> bool:
        """開始新的建置任務"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO build_progress 
                    (task_id, task_type, site_id, site_name, start_date, end_date, 
                     status, total_dates, completed_dates, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'running', ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (task_id, task_type, site_id, site_name, start_date, end_date, total_dates))
                
                conn.commit()
                logger.info(f"Started task {task_id}: {task_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start task {task_id}: {e}")
            return False
    
    def update_progress(self, task_id: str, current_date: Optional[str] = None, 
                       completed_dates: Optional[int] = None, 
                       total_records: Optional[int] = None) -> bool:
        """更新任務進度"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                updates = []
                params = []
                
                if current_date is not None:
                    updates.append("current_date = ?")
                    params.append(current_date)
                
                if completed_dates is not None:
                    updates.append("completed_dates = ?")
                    params.append(completed_dates)
                
                if total_records is not None:
                    updates.append("total_records = ?")
                    params.append(total_records)
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(task_id)
                
                if updates:
                    query = f"UPDATE build_progress SET {', '.join(updates)} WHERE task_id = ?"
                    conn.execute(query, params)
                    conn.commit()
                    
                return True
                
        except Exception as e:
            logger.error(f"Failed to update progress for {task_id}: {e}")
            return False
    
    def complete_task(self, task_id: str, total_records: int = 0, 
                     error_message: Optional[str] = None) -> bool:
        """完成任務"""
        try:
            status = 'failed' if error_message else 'completed'
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE build_progress 
                    SET status = ?, total_records = ?, error_message = ?, 
                        completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (status, total_records, error_message, task_id))
                
                conn.commit()
                logger.info(f"Task {task_id} completed with status: {status}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False
    
    def cancel_task(self, task_id: str, reason: str = "User cancelled") -> bool:
        """取消任務"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE build_progress 
                    SET status = 'cancelled', error_message = ?, 
                        completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ? AND status = 'running'
                ''', (reason, task_id))
                
                conn.commit()
                logger.info(f"Task {task_id} cancelled: {reason}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def is_task_cancelled(self, task_id: str) -> bool:
        """檢查任務是否被取消"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT status FROM build_progress WHERE task_id = ?
                ''', (task_id,))
                
                row = cursor.fetchone()
                if row:
                    return row[0] == 'cancelled'
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to check if task {task_id} is cancelled: {e}")
            return False
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """獲取任務進度"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM build_progress WHERE task_id = ?
                ''', (task_id,))
                
                row = cursor.fetchone()
                if row:
                    progress = dict(row)
                    # 計算進度百分比
                    if progress['total_dates'] > 0:
                        progress['progress_percentage'] = (progress['completed_dates'] / progress['total_dates']) * 100
                    else:
                        progress['progress_percentage'] = 0
                    
                    return progress
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get progress for {task_id}: {e}")
            return None
    
    def get_running_tasks(self) -> List[Dict[str, Any]]:
        """獲取所有運行中的任務"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM build_progress 
                    WHERE status = 'running' 
                    ORDER BY created_at DESC
                ''')
                
                tasks = []
                for row in cursor.fetchall():
                    progress = dict(row)
                    if progress['total_dates'] > 0:
                        progress['progress_percentage'] = (progress['completed_dates'] / progress['total_dates']) * 100
                    else:
                        progress['progress_percentage'] = 0
                    tasks.append(progress)
                
                return tasks
                
        except Exception as e:
            logger.error(f"Failed to get running tasks: {e}")
            return []
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的任務"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM build_progress 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                tasks = []
                for row in cursor.fetchall():
                    progress = dict(row)
                    if progress['total_dates'] > 0:
                        progress['progress_percentage'] = (progress['completed_dates'] / progress['total_dates']) * 100
                    else:
                        progress['progress_percentage'] = 0
                    tasks.append(progress)
                
                return tasks
                
        except Exception as e:
            logger.error(f"Failed to get recent tasks: {e}")
            return []
    
    def resume_interrupted_tasks(self) -> List[str]:
        """恢復中斷的任務"""
        try:
            running_tasks = self.get_running_tasks()
            resumed_tasks = []
            
            for task in running_tasks:
                # 檢查任務是否真的中斷了（超過5分鐘沒更新）
                updated_at = datetime.fromisoformat(task['updated_at'])
                if datetime.now() - updated_at > timedelta(minutes=5):
                    logger.warning(f"Found interrupted task: {task['task_id']}")
                    
                    # 標記為中斷
                    self.complete_task(task['task_id'], 
                                     task['total_records'], 
                                     "Task was interrupted")
                    
                    # 創建恢復任務的 ID
                    resume_task_id = f"{task['task_id']}_resume_{int(datetime.now().timestamp())}"
                    resumed_tasks.append(resume_task_id)
                    
                    # 這裡可以添加自動恢復邏輯
                    logger.info(f"Task {task['task_id']} marked as interrupted, resume ID: {resume_task_id}")
            
            return resumed_tasks
            
        except Exception as e:
            logger.error(f"Failed to resume interrupted tasks: {e}")
            return []
    
    def get_missing_dates_for_task(self, task_id: str) -> List[str]:
        """獲取任務中缺失的日期"""
        try:
            task = self.get_task_progress(task_id)
            if not task or not task['start_date'] or not task['end_date']:
                return []
            
            # 生成日期範圍
            start_date = datetime.strptime(task['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(task['end_date'], '%Y-%m-%d')
            
            all_dates = []
            current = start_date
            while current <= end_date:
                all_dates.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
            
            # 檢查哪些日期已經完成
            # 這裡需要根據實際的數據庫結構來實現
            # 暫時返回所有日期，實際使用時需要查詢已完成的日期
            
            return all_dates
            
        except Exception as e:
            logger.error(f"Failed to get missing dates for {task_id}: {e}")
            return []
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """清理舊的任務記錄"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM build_progress 
                    WHERE status IN ('completed', 'failed') 
                    AND created_at < ?
                ''', (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old task records")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0 