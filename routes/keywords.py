#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify, session
import logging
from datetime import datetime, timedelta
from services.database import Database
from services.semantic_search import SemanticSearch

logger = logging.getLogger(__name__)
keywords_bp = Blueprint('keywords', __name__)

database = Database()
semantic_search = SemanticSearch()

@keywords_bp.route('/search')
def search_keywords():
    """語義搜索關鍵字"""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 50))
        
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        # 執行語義搜索
        results = database.search_keywords_by_semantic(query, limit)
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return jsonify({'error': str(e)}), 500

@keywords_bp.route('/monthly')
def monthly_keywords():
    """獲取月度關鍵字排名匯總"""
    try:
        keyword_pattern = request.args.get('keyword', '')
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        limit = int(request.args.get('limit', 30))
        
        if not keyword_pattern:
            return jsonify({'error': 'Keyword parameter required'}), 400
        
        results = database.get_monthly_keyword_summary(keyword_pattern, month, limit)
        
        return jsonify({
            'keyword_pattern': keyword_pattern,
            'month': month,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Monthly keywords failed: {e}")
        return jsonify({'error': str(e)}), 500

@keywords_bp.route('/rankings')
def get_rankings():
    """獲取關鍵字排名數據"""
    try:
        site_id = request.args.get('site_id', type=int)
        keyword_id = request.args.get('keyword_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        rankings = database.get_rankings(
            site_id=site_id,
            keyword_id=keyword_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # 限制結果數量
        if limit:
            rankings = rankings[:limit]
        
        return jsonify({
            'rankings': rankings,
            'count': len(rankings),
            'filters': {
                'site_id': site_id,
                'keyword_id': keyword_id,
                'start_date': start_date,
                'end_date': end_date
            }
        })
        
    except Exception as e:
        logger.error(f"Get rankings failed: {e}")
        return jsonify({'error': str(e)}), 500

@keywords_bp.route('/trending')
def trending_keywords():
    """獲取趨勢關鍵字"""
    try:
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 20))
        
        # 計算日期範圍
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 獲取最近的排名數據
        rankings = database.get_rankings(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        # 簡單統計 - 按點擊量排序
        keyword_stats = {}
        for ranking in rankings:
            keyword = ranking['keyword']
            if keyword not in keyword_stats:
                keyword_stats[keyword] = {
                    'keyword': keyword,
                    'total_clicks': 0,
                    'total_impressions': 0,
                    'avg_position': 0,
                    'sites': set()
                }
            
            stats = keyword_stats[keyword]
            stats['total_clicks'] += ranking.get('clicks', 0)
            stats['total_impressions'] += ranking.get('impressions', 0)
            stats['sites'].add(ranking['domain'])
        
        # 轉換為列表並排序
        trending = []
        for keyword, stats in keyword_stats.items():
            stats['sites_count'] = len(stats['sites'])
            stats['sites'] = list(stats['sites'])
            trending.append(stats)
        
        # 按點擊量排序
        trending.sort(key=lambda x: x['total_clicks'], reverse=True)
        
        return jsonify({
            'trending_keywords': trending[:limit],
            'period': f'{start_date} to {end_date}',
            'days': days
        })
        
    except Exception as e:
        logger.error(f"Trending keywords failed: {e}")
        return jsonify({'error': str(e)}), 500

@keywords_bp.route('/add', methods=['POST'])
def add_keyword():
    """手動添加關鍵字"""
    try:
        data = request.json
        keyword = data.get('keyword')
        site_id = data.get('site_id')
        category = data.get('category')
        priority = data.get('priority', 0)
        
        if not keyword or not site_id:
            return jsonify({'error': 'Keyword and site_id required'}), 400
        
        keyword_id = database.add_keyword(keyword, site_id, category, priority)
        
        return jsonify({
            'keyword_id': keyword_id,
            'keyword': keyword,
            'site_id': site_id,
            'message': 'Keyword added successfully'
        })
        
    except Exception as e:
        logger.error(f"Add keyword failed: {e}")
        return jsonify({'error': str(e)}), 500 