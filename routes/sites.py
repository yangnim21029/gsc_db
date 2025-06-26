#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify, session, current_app
import logging
from services.database import Database

logger = logging.getLogger(__name__)
sites_bp = Blueprint('sites', __name__)

database = Database()

@sites_bp.route('/')
def list_sites():
    """獲取所有站點"""
    try:
        sites = database.get_sites()
        return jsonify({
            'sites': sites,
            'count': len(sites)
        })
    except Exception as e:
        logger.error(f"List sites failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/gsc')
def list_gsc_sites():
    """從GSC獲取站點列表"""
    try:
        from services.gsc_client import GSCClient
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            return jsonify({'error': 'Not authenticated with GSC'}), 401
        
        gsc_sites = gsc_client.get_sites()
        return jsonify({
            'gsc_sites': gsc_sites,
            'count': len(gsc_sites)
        })
    except Exception as e:
        logger.error(f"List GSC sites failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/import', methods=['POST'])
def import_gsc_sites():
    """從GSC導入站點到本地數據庫"""
    try:
        from services.gsc_client import GSCClient
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            return jsonify({'error': 'Not authenticated with GSC'}), 401
        
        # 獲取GSC站點
        gsc_sites = gsc_client.get_sites()
        imported_sites = []
        
        for site_url in gsc_sites:
            try:
                # 檢查是否已存在
                existing_site = database.get_site_by_domain(site_url)
                if not existing_site:
                    # 創建站點名稱
                    site_name = site_url.replace('sc-domain:', '').replace('https://', '').replace('http://', '')
                    site_id = database.add_site(site_url, site_name)
                    imported_sites.append({
                        'id': site_id,
                        'domain': site_url,
                        'name': site_name,
                        'status': 'imported'
                    })
                else:
                    imported_sites.append({
                        'id': existing_site['id'],
                        'domain': site_url,
                        'name': existing_site['name'],
                        'status': 'already_exists'
                    })
            except Exception as e:
                logger.error(f"Failed to import site {site_url}: {e}")
                imported_sites.append({
                    'domain': site_url,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return jsonify({
            'message': f'Imported {len(imported_sites)} sites from GSC',
            'sites': imported_sites,
            'count': len(imported_sites)
        })
        
    except Exception as e:
        logger.error(f"Import GSC sites failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/add', methods=['POST'])
def add_site():
    """添加新站點"""
    try:
        data = request.json
        domain = data.get('domain')
        name = data.get('name')
        category = data.get('category')
        
        if not domain or not name:
            return jsonify({'error': 'Domain and name required'}), 400
        
        site_id = database.add_site(domain, name, category)
        
        return jsonify({
            'site_id': site_id,
            'domain': domain,
            'name': name,
            'category': category,
            'message': 'Site added successfully'
        })
        
    except Exception as e:
        logger.error(f"Add site failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/<int:site_id>/sync', methods=['POST'])
def sync_site(site_id):
    """同步特定站點數據"""
    try:
        from services.gsc_client import GSCClient
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            return jsonify({'error': 'Not authenticated with GSC'}), 401
        
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 獲取站點信息
        sites = database.get_sites()
        site = next((s for s in sites if s['id'] == site_id), None)
        
        if not site:
            return jsonify({'error': 'Site not found'}), 404
        
        # 如果沒有指定日期，同步昨天的數據
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            start_date = end_date = yesterday.strftime('%Y-%m-%d')
        
        result = gsc_client.sync_site_data(site['domain'], start_date, end_date)
        
        return jsonify({
            'message': f'Site {site["name"]} synced successfully',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Sync site failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/sync/all', methods=['POST'])
def sync_all_sites():
    """同步所有站點數據"""
    try:
        from services.gsc_client import GSCClient
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            return jsonify({'error': 'Not authenticated with GSC'}), 401
        
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 如果沒有指定日期，同步昨天的數據
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            start_date = end_date = yesterday.strftime('%Y-%m-%d')
        
        # 獲取所有站點
        sites = database.get_sites()
        site_domains = [site['domain'] for site in sites]
        
        results = gsc_client.sync_multiple_sites(site_domains, start_date, end_date)
        
        total_records = sum(r.get('count', 0) for r in results)
        
        return jsonify({
            'message': f'Synced {len(results)} sites with {total_records} total records',
            'results': results,
            'period': f'{start_date} to {end_date}'
        })
        
    except Exception as e:
        logger.error(f"Sync all sites failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/<int:site_id>/sync/enhanced', methods=['POST'])
def sync_site_enhanced(site_id):
    """增強版同步特定站點數據 - 支援大量數據和多維度"""
    try:
        from services.gsc_client import GSCClient
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            return jsonify({'error': 'Not authenticated with GSC'}), 401
        
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 獲取站點信息
        sites = database.get_sites()
        site = next((s for s in sites if s['id'] == site_id), None)
        
        if not site:
            return jsonify({'error': 'Site not found'}), 404
        
        # 如果沒有指定日期，同步昨天的數據
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            start_date = end_date = yesterday.strftime('%Y-%m-%d')
        
        result = gsc_client.sync_site_data_enhanced(site['domain'], start_date, end_date)
        
        return jsonify({
            'message': f'Enhanced sync for {site["name"]} completed successfully',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Enhanced sync site failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/<int:site_id>/sync/range', methods=['POST'])
def sync_site_range(site_id):
    """按日期範圍同步站點數據"""
    try:
        from services.gsc_client import GSCClient
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            return jsonify({'error': 'Not authenticated with GSC'}), 401
        
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        # 獲取站點信息
        sites = database.get_sites()
        site = next((s for s in sites if s['id'] == site_id), None)
        
        if not site:
            return jsonify({'error': 'Site not found'}), 404
        
        results = gsc_client.sync_site_data_daily_range(site['domain'], start_date, end_date)
        
        total_keyword_data = sum(r.get('keyword_data', 0) for r in results)
        total_page_data = sum(r.get('page_data', 0) for r in results)
        
        return jsonify({
            'message': f'Range sync for {site["name"]} completed',
            'period': f'{start_date} to {end_date}',
            'summary': {
                'total_days': len(results),
                'total_keyword_records': total_keyword_data,
                'total_page_records': total_page_data,
                'total_records': total_keyword_data + total_page_data
            },
            'daily_results': results
        })
        
    except Exception as e:
        logger.error(f"Range sync site failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/sync/enhanced/all', methods=['POST'])
def sync_all_sites_enhanced():
    """增強版同步所有站點數據"""
    try:
        from services.gsc_client import GSCClient
        gsc_client = GSCClient()
        
        if not gsc_client.is_authenticated():
            return jsonify({'error': 'Not authenticated with GSC'}), 401
        
        data = request.json or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 如果沒有指定日期，同步昨天的數據
        if not start_date or not end_date:
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            start_date = end_date = yesterday.strftime('%Y-%m-%d')
        
        # 獲取所有站點
        sites = database.get_sites()
        all_results = []
        
        for site in sites:
            try:
                logger.info(f"Starting enhanced sync for {site['domain']}")
                result = gsc_client.sync_site_data_enhanced(site['domain'], start_date, end_date)
                all_results.append({
                    'site_id': site['id'],
                    'site_name': site['name'],
                    'status': 'success',
                    **result
                })
            except Exception as e:
                logger.error(f"Failed enhanced sync for {site['domain']}: {e}")
                all_results.append({
                    'site_id': site['id'],
                    'site_name': site['name'],
                    'status': 'error',
                    'error': str(e),
                    'keyword_data': 0,
                    'page_data': 0
                })
        
        total_keyword_records = sum(r.get('keyword_data', 0) for r in all_results)
        total_page_records = sum(r.get('page_data', 0) for r in all_results)
        successful_syncs = len([r for r in all_results if r['status'] == 'success'])
        
        return jsonify({
            'message': f'Enhanced sync completed for all sites',
            'period': f'{start_date} to {end_date}',
            'summary': {
                'total_sites': len(sites),
                'successful_syncs': successful_syncs,
                'total_keyword_records': total_keyword_records,
                'total_page_records': total_page_records,
                'total_records': total_keyword_records + total_page_records
            },
            'results': all_results
        })
        
    except Exception as e:
        logger.error(f"Enhanced sync all sites failed: {e}")
        return jsonify({'error': str(e)}), 500

@sites_bp.route('/<int:site_id>/data/pages', methods=['GET'])
def get_site_page_data(site_id):
    """獲取站點的頁面數據"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page_filter = request.args.get('page')
        
        page_data = database.get_page_data(
            site_id=site_id,
            page=page_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'site_id': site_id,
            'page_data': page_data,
            'count': len(page_data),
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'page_filter': page_filter
            }
        })
        
    except Exception as e:
        logger.error(f"Get page data failed: {e}")
        return jsonify({'error': str(e)}), 500 