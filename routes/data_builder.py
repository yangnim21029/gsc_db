#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify
import logging
from services.data_builder import DataBuilder
from services.build_progress import BuildProgress

logger = logging.getLogger(__name__)
data_builder_bp = Blueprint('data_builder', __name__)

data_builder = DataBuilder()
build_progress = BuildProgress()

@data_builder_bp.route('/status')
def get_build_status():
    """獲取數據建置狀態"""
    try:
        status = data_builder.get_build_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Get build status failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/coverage')
def get_data_coverage():
    """獲取數據覆蓋情況"""
    try:
        site_id = request.args.get('site_id', type=int)
        coverage = data_builder.get_data_coverage(site_id)
        return jsonify(coverage)
    except Exception as e:
        logger.error(f"Get data coverage failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/missing-dates/<int:site_id>')
def get_missing_dates(site_id):
    """獲取站點缺失的日期"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        missing_dates = data_builder.get_missing_dates(site_id, start_date, end_date)
        
        return jsonify({
            'site_id': site_id,
            'period': f'{start_date} to {end_date}',
            'missing_dates': missing_dates,
            'missing_count': len(missing_dates)
        })
        
    except Exception as e:
        logger.error(f"Get missing dates failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/build/site/<int:site_id>', methods=['POST'])
def build_site_data(site_id):
    """建置特定站點的數據"""
    try:
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        force_rebuild = data.get('force_rebuild', False)
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        result = data_builder.build_data_range(site_id, start_date, end_date, force_rebuild)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Build site data failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/build/all', methods=['POST'])
def build_all_sites_data():
    """建置所有站點的數據"""
    try:
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        force_rebuild = data.get('force_rebuild', False)
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        result = data_builder.build_all_sites_range(start_date, end_date, force_rebuild)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Build all sites data failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/build/incremental', methods=['POST'])
def build_incremental():
    """增量建置數據 - 自動檢測並填補缺失的日期"""
    try:
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        site_ids = data.get('site_ids')  # 可選：指定特定站點
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        if site_ids:
            # 建置指定站點
            results = []
            for site_id in site_ids:
                result = data_builder.build_data_range(site_id, start_date, end_date, False)
                results.append(result)
            
            return jsonify({
                'message': 'Incremental build completed for specified sites',
                'results': results
            })
        else:
            # 建置所有站點
            result = data_builder.build_all_sites_range(start_date, end_date, False)
            return jsonify(result)
        
    except Exception as e:
        logger.error(f"Incremental build failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/build/recent', methods=['POST'])
def build_recent_data():
    """建置最近幾天的數據"""
    try:
        data = request.json or {}
        days_back = data.get('days_back', 7)  # 預設最近7天
        site_ids = data.get('site_ids')  # 可選：指定特定站點
        
        from datetime import datetime, timedelta
        
        # 計算日期範圍（GSC 數據通常有2-3天延遲）
        end_date = datetime.now() - timedelta(days=3)
        start_date = end_date - timedelta(days=days_back)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        if site_ids:
            # 建置指定站點
            results = []
            for site_id in site_ids:
                result = data_builder.build_data_range(site_id, start_date_str, end_date_str, False)
                results.append(result)
            
            return jsonify({
                'message': f'Recent data build completed for specified sites',
                'period': f'{start_date_str} to {end_date_str}',
                'days_back': days_back,
                'results': results
            })
        else:
            # 建置所有站點
            result = data_builder.build_all_sites_range(start_date_str, end_date_str, False)
            result['days_back'] = days_back
            return jsonify(result)
        
    except Exception as e:
        logger.error(f"Build recent data failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/progress/<task_id>')
def get_task_progress(task_id):
    """獲取特定任務的進度"""
    try:
        progress = build_progress.get_task_progress(task_id)
        
        if not progress:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(progress)
        
    except Exception as e:
        logger.error(f"Get task progress failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/progress/running')
def get_running_tasks():
    """獲取所有運行中的任務"""
    try:
        tasks = build_progress.get_running_tasks()
        return jsonify({
            'running_tasks': tasks,
            'count': len(tasks)
        })
        
    except Exception as e:
        logger.error(f"Get running tasks failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/progress/recent')
def get_recent_tasks():
    """獲取最近的任務"""
    try:
        limit = request.args.get('limit', 10, type=int)
        tasks = build_progress.get_recent_tasks(limit)
        
        return jsonify({
            'recent_tasks': tasks,
            'count': len(tasks)
        })
        
    except Exception as e:
        logger.error(f"Get recent tasks failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/progress/resume', methods=['POST'])
def resume_interrupted_tasks():
    """恢復中斷的任務"""
    try:
        resumed_tasks = build_progress.resume_interrupted_tasks()
        
        return jsonify({
            'message': f'Found and marked {len(resumed_tasks)} interrupted tasks',
            'resumed_task_ids': resumed_tasks
        })
        
    except Exception as e:
        logger.error(f"Resume interrupted tasks failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/progress/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """清理舊的任務記錄"""
    try:
        data = request.json or {}
        days = data.get('days', 30)
        
        deleted_count = build_progress.cleanup_old_tasks(days)
        
        return jsonify({
            'message': f'Cleaned up {deleted_count} old task records',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Cleanup old tasks failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/progress/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """取消特定任務"""
    try:
        data = request.json or {}
        reason = data.get('reason', 'User cancelled')
        
        success = build_progress.cancel_task(task_id, reason)
        
        if success:
            return jsonify({
                'message': f'Task {task_id} has been cancelled',
                'task_id': task_id,
                'reason': reason
            })
        else:
            return jsonify({
                'error': f'Failed to cancel task {task_id}. Task may not exist or already completed.'
            }), 400
        
    except Exception as e:
        logger.error(f"Cancel task failed: {e}")
        return jsonify({'error': str(e)}), 500

@data_builder_bp.route('/progress/cancel-all', methods=['POST'])
def cancel_all_running_tasks():
    """取消所有運行中的任務"""
    try:
        data = request.json or {}
        reason = data.get('reason', 'User cancelled all tasks')
        
        running_tasks = build_progress.get_running_tasks()
        cancelled_count = 0
        
        for task in running_tasks:
            if build_progress.cancel_task(task['task_id'], reason):
                cancelled_count += 1
        
        return jsonify({
            'message': f'Cancelled {cancelled_count} running tasks',
            'cancelled_count': cancelled_count,
            'total_running': len(running_tasks)
        })
        
    except Exception as e:
        logger.error(f"Cancel all tasks failed: {e}")
        return jsonify({'error': str(e)}), 500 