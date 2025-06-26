#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from services.database import Database
from services.gsc_client import GSCClient
from services.build_progress import BuildProgress
import uuid

logger = logging.getLogger(__name__)

class DataBuilder:
    """數據庫建置和維護服務"""
    
    def __init__(self):
        self.database = Database()
        self.gsc_client = GSCClient()
        self.progress = BuildProgress()
    
    def get_data_coverage(self, site_id: int = None) -> Dict[str, Any]:
        """獲取數據覆蓋情況"""
        try:
            with self.database.get_connection() as conn:
                if site_id:
                    # 特定站點的數據覆蓋
                    query = '''
                        SELECT 
                            s.id as site_id,
                            s.name as site_name,
                            s.domain,
                            MIN(dr.date) as earliest_date,
                            MAX(dr.date) as latest_date,
                            COUNT(DISTINCT dr.date) as total_days,
                            COUNT(DISTINCT dr.keyword_id) as total_keywords,
                            COUNT(dr.id) as total_ranking_records
                        FROM sites s
                        LEFT JOIN daily_rankings dr ON s.id = dr.site_id
                        WHERE s.id = ?
                        GROUP BY s.id
                    '''
                    params = (site_id,)
                else:
                    # 所有站點的數據覆蓋
                    query = '''
                        SELECT 
                            s.id as site_id,
                            s.name as site_name,
                            s.domain,
                            MIN(dr.date) as earliest_date,
                            MAX(dr.date) as latest_date,
                            COUNT(DISTINCT dr.date) as total_days,
                            COUNT(DISTINCT dr.keyword_id) as total_keywords,
                            COUNT(dr.id) as total_ranking_records
                        FROM sites s
                        LEFT JOIN daily_rankings dr ON s.id = dr.site_id
                        GROUP BY s.id
                        ORDER BY s.name
                    '''
                    params = ()
                
                sites_coverage = [dict(row) for row in conn.execute(query, params).fetchall()]
                
                # 獲取頁面數據覆蓋
                for site in sites_coverage:
                    page_query = '''
                        SELECT 
                            MIN(pd.date) as page_earliest_date,
                            MAX(pd.date) as page_latest_date,
                            COUNT(DISTINCT pd.date) as page_total_days,
                            COUNT(DISTINCT pd.page) as total_pages,
                            COUNT(pd.id) as total_page_records
                        FROM page_data pd
                        WHERE pd.site_id = ?
                    '''
                    page_data = conn.execute(page_query, (site['site_id'],)).fetchone()
                    if page_data:
                        site.update(dict(page_data))
                
                return {
                    'sites_coverage': sites_coverage,
                    'total_sites': len(sites_coverage),
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get data coverage: {e}")
            return {'error': str(e)}
    
    def get_missing_dates(self, site_id: int, start_date: str, end_date: str) -> List[str]:
        """獲取指定期間內缺失的日期"""
        try:
            with self.database.get_connection() as conn:
                # 獲取已有數據的日期
                existing_dates = set()
                query = '''
                    SELECT DISTINCT date 
                    FROM daily_rankings 
                    WHERE site_id = ? AND date BETWEEN ? AND ?
                '''
                for row in conn.execute(query, (site_id, start_date, end_date)):
                    existing_dates.add(row[0])
                
                # 生成期間內所有日期
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                all_dates = []
                current_date = start_dt
                while current_date <= end_dt:
                    all_dates.append(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=1)
                
                # 找出缺失的日期
                missing_dates = [d for d in all_dates if d not in existing_dates]
                
                return missing_dates
                
        except Exception as e:
            logger.error(f"Failed to get missing dates: {e}")
            return []
    
    def build_data_range(self, site_id: int, start_date: str, end_date: str, 
                        force_rebuild: bool = False, task_id: str = None) -> Dict[str, Any]:
        """建置指定站點和日期範圍的數據"""
        try:
            if not self.gsc_client.is_authenticated():
                return {'error': 'GSC client not authenticated'}
            
            # 獲取站點信息
            sites = self.database.get_sites()
            site = next((s for s in sites if s['id'] == site_id), None)
            if not site:
                return {'error': f'Site with id {site_id} not found'}
            
            # 創建任務 ID
            if not task_id:
                task_id = f"build_{site_id}_{start_date}_{end_date}_{uuid.uuid4().hex[:8]}"
            
            # 獲取需要建置的日期
            if force_rebuild:
                # 強制重建：建置所有日期
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                dates_to_build = []
                current_date = start_dt
                while current_date <= end_dt:
                    dates_to_build.append(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=1)
            else:
                # 增量建置：只建置缺失的日期
                dates_to_build = self.get_missing_dates(site_id, start_date, end_date)
            
            if not dates_to_build:
                return {
                    'message': f'No missing data for {site["name"]} in period {start_date} to {end_date}',
                    'site_id': site_id,
                    'site_name': site['name'],
                    'period': f'{start_date} to {end_date}',
                    'dates_processed': 0,
                    'total_records': 0,
                    'task_id': task_id
                }
            
            # 開始進度追蹤
            task_type = 'force_rebuild' if force_rebuild else 'incremental_build'
            self.progress.start_task(
                task_id=task_id,
                task_type=task_type,
                site_id=site_id,
                site_name=site['name'],
                start_date=start_date,
                end_date=end_date,
                total_dates=len(dates_to_build)
            )
            
            # 開始建置數據
            results = []
            total_keyword_records = 0
            total_page_records = 0
            completed_dates = 0
            
            logger.info(f"Building data for {site['name']}: {len(dates_to_build)} dates (Task: {task_id})")
            
            try:
                for i, date_str in enumerate(dates_to_build):
                    # 檢查任務是否被取消
                    if self.progress.is_task_cancelled(task_id):
                        logger.info(f"Task {task_id} was cancelled, stopping build process")
                        return {
                            'message': f'Data building cancelled for {site["name"]}',
                            'site_id': site_id,
                            'site_name': site['name'],
                            'period': f'{start_date} to {end_date}',
                            'task_id': task_id,
                            'status': 'cancelled',
                            'summary': {
                                'total_dates_requested': len(dates_to_build),
                                'successful_dates': len([r for r in results if r['status'] == 'success']),
                                'cancelled_at_date': completed_dates,
                                'total_keyword_records': total_keyword_records,
                                'total_page_records': total_page_records,
                                'total_records': total_keyword_records + total_page_records
                            },
                            'daily_results': results,
                            'force_rebuild': force_rebuild
                        }
                    
                    try:
                        logger.info(f"Building data for {site['name']} on {date_str} ({i+1}/{len(dates_to_build)})")
                        
                        # 更新進度
                        self.progress.update_progress(
                            task_id=task_id,
                            current_date=date_str,
                            completed_dates=completed_dates
                        )
                        
                        result = self.gsc_client.sync_site_data_enhanced(
                            site['domain'], date_str, date_str
                        )
                        
                        results.append({
                            'date': date_str,
                            'status': 'success',
                            **result
                        })
                        
                        total_keyword_records += result.get('keyword_data', 0)
                        total_page_records += result.get('page_data', 0)
                        completed_dates += 1
                        
                        # 更新總記錄數
                        self.progress.update_progress(
                            task_id=task_id,
                            completed_dates=completed_dates,
                            total_records=total_keyword_records + total_page_records
                        )
                        
                    except Exception as e:
                        logger.error(f"Failed to build data for {date_str}: {e}")
                        results.append({
                            'date': date_str,
                            'status': 'error',
                            'error': str(e),
                            'keyword_data': 0,
                            'page_data': 0
                        })
                        # 即使失敗也算完成一個日期
                        completed_dates += 1
                        self.progress.update_progress(
                            task_id=task_id,
                            completed_dates=completed_dates
                        )
                
                # 完成任務
                successful_dates = len([r for r in results if r['status'] == 'success'])
                total_records = total_keyword_records + total_page_records
                
                self.progress.complete_task(
                    task_id=task_id,
                    total_records=total_records
                )
                
                return {
                    'message': f'Data building completed for {site["name"]}',
                    'site_id': site_id,
                    'site_name': site['name'],
                    'period': f'{start_date} to {end_date}',
                    'task_id': task_id,
                    'summary': {
                        'total_dates_requested': len(dates_to_build),
                        'successful_dates': successful_dates,
                        'failed_dates': len(dates_to_build) - successful_dates,
                        'total_keyword_records': total_keyword_records,
                        'total_page_records': total_page_records,
                        'total_records': total_keyword_records + total_page_records
                    },
                    'daily_results': results,
                    'force_rebuild': force_rebuild
                }
                
            except Exception as e:
                # 如果建置過程中出現錯誤，標記任務為失敗
                logger.error(f"Build process failed for task {task_id}: {e}")
                self.progress.complete_task(task_id, 0, str(e))
                raise e
            
        except Exception as e:
            logger.error(f"Failed to build data range: {e}")
            return {'error': str(e)}
    
    def build_all_sites_range(self, start_date: str, end_date: str, 
                             force_rebuild: bool = False) -> Dict[str, Any]:
        """為所有站點建置指定日期範圍的數據"""
        try:
            sites = self.database.get_sites()
            all_results = []
            
            total_keyword_records = 0
            total_page_records = 0
            total_successful_sites = 0
            
            for site in sites:
                try:
                    logger.info(f"Building data for all sites: {site['name']}")
                    
                    result = self.build_data_range(
                        site['id'], start_date, end_date, force_rebuild
                    )
                    
                    if 'error' not in result:
                        all_results.append({
                            'site_id': site['id'],
                            'site_name': site['name'],
                            'status': 'success',
                            **result
                        })
                        
                        summary = result.get('summary', {})
                        total_keyword_records += summary.get('total_keyword_records', 0)
                        total_page_records += summary.get('total_page_records', 0)
                        
                        if summary.get('successful_dates', 0) > 0:
                            total_successful_sites += 1
                    else:
                        all_results.append({
                            'site_id': site['id'],
                            'site_name': site['name'],
                            'status': 'error',
                            'error': result['error']
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to build data for {site['name']}: {e}")
                    all_results.append({
                        'site_id': site['id'],
                        'site_name': site['name'],
                        'status': 'error',
                        'error': str(e)
                    })
            
            return {
                'message': f'Bulk data building completed for all sites',
                'period': f'{start_date} to {end_date}',
                'summary': {
                    'total_sites': len(sites),
                    'successful_sites': total_successful_sites,
                    'total_keyword_records': total_keyword_records,
                    'total_page_records': total_page_records,
                    'total_records': total_keyword_records + total_page_records
                },
                'results': all_results,
                'force_rebuild': force_rebuild
            }
            
        except Exception as e:
            logger.error(f"Failed to build all sites range: {e}")
            return {'error': str(e)}
    
    def get_build_status(self) -> Dict[str, Any]:
        """獲取整體建置狀態"""
        try:
            coverage = self.get_data_coverage()
            
            # 計算總體統計
            total_records = 0
            total_days = 0
            earliest_date = None
            latest_date = None
            
            for site in coverage.get('sites_coverage', []):
                total_records += site.get('total_ranking_records', 0) + site.get('total_page_records', 0)
                total_days += site.get('total_days', 0)
                
                if site.get('earliest_date'):
                    if not earliest_date or site['earliest_date'] < earliest_date:
                        earliest_date = site['earliest_date']
                
                if site.get('latest_date'):
                    if not latest_date or site['latest_date'] > latest_date:
                        latest_date = site['latest_date']
            
            return {
                'overall_status': {
                    'total_sites': coverage.get('total_sites', 0),
                    'total_records': total_records,
                    'total_days_coverage': total_days,
                    'earliest_date': earliest_date,
                    'latest_date': latest_date,
                    'data_freshness_days': (date.today() - datetime.strptime(latest_date, '%Y-%m-%d').date()).days if latest_date else None
                },
                'sites_detail': coverage.get('sites_coverage', []),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get build status: {e}")
            return {'error': str(e)} 