#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from flask_cors import CORS
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 導入自定義模組
from services.gsc_client import GSCClient
from services.database import Database
from services.semantic_search import SemanticSearch
from routes.auth import auth_bp
from routes.sites import sites_bp
from routes.keywords import keywords_bp
from routes.analytics import analytics_bp
from routes.data_builder import data_builder_bp

# 設置日誌 - 同時輸出到檔案和控制台
import logging.handlers

# 創建自定義日誌設定
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 檔案處理器
file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# 控制台處理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# 根日誌設定
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)
logger = logging.getLogger(__name__)

# 創建Flask應用
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# 啟用CORS
CORS(app, origins=['http://localhost:3003', 'http://localhost:3000'])

# 初始化服務
database = Database()
gsc_client = GSCClient()
semantic_search = SemanticSearch()

# 註冊路由
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(sites_bp, url_prefix='/sites')
app.register_blueprint(keywords_bp, url_prefix='/keywords')
app.register_blueprint(analytics_bp, url_prefix='/analytics')
app.register_blueprint(data_builder_bp, url_prefix='/data-builder')

@app.route('/')
def index():
    """前端首頁 - 顯示登入頁面"""
    try:
        # 創建新的 GSCClient 實例來檢查認證狀態
        from services.gsc_client import GSCClient
        current_gsc_client = GSCClient()
        
        # 檢查認證狀態 - 只要有任一條件滿足就算認證成功
        authenticated = current_gsc_client.is_authenticated() or session.get('authenticated', False)
        
        if authenticated:
            # 確保 session 已設置
            session['authenticated'] = True
            
            # 獲取資料庫進度
            summary, sites = get_database_progress()
            return render_template('home.html', 
                                 authenticated=True, 
                                 summary=summary, 
                                 sites=sites)
        else:
            return render_template('home.html', authenticated=False)
            
    except Exception as e:
        logger.error(f"Home page error: {e}")
        return render_template('home.html', 
                             authenticated=False, 
                             error=str(e))

@app.route('/home')
def home():
    """前端首頁別名 (重定向到根路徑)"""
    return redirect('/')

@app.route('/api')
def api_info():
    """API 資訊"""
    return jsonify({
        'service': 'GSC Daily Database',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'auth': '/auth',
            'sites': '/sites',
            'keywords': '/keywords',
            'analytics': '/analytics',
            'health': '/health',
            'home': '/home'
        },
        'timestamp': datetime.now().isoformat()
    })



def get_database_progress():
    """獲取資料庫進度資訊"""
    try:
        # 獲取所有站點
        sites = database.get_sites()
        
        # 計算總覽統計
        with database.get_connection() as conn:
            # 總關鍵字數
            total_keywords = conn.execute('SELECT COUNT(*) FROM keywords').fetchone()[0]
            
            # 最新和最早數據日期
            date_range = conn.execute('''
                SELECT MIN(date) as oldest, MAX(date) as latest 
                FROM daily_rankings
            ''').fetchone()
            
            summary = {
                'total_sites': len(sites),
                'total_keywords': total_keywords,
                'latest_date': date_range['latest'] if date_range['latest'] else None,
                'oldest_date': date_range['oldest'] if date_range['oldest'] else None
            }
            
            # 為每個站點添加詳細資訊
            for site in sites:
                # 該站點的關鍵字數量
                keyword_count = conn.execute(
                    'SELECT COUNT(*) FROM keywords WHERE site_id = ?', 
                    (site['id'],)
                ).fetchone()[0]
                
                # 該站點的數據日期範圍
                site_dates = conn.execute('''
                    SELECT MIN(date) as oldest, MAX(date) as latest 
                    FROM daily_rankings WHERE site_id = ?
                ''', (site['id'],)).fetchone()
                
                site['keyword_count'] = keyword_count
                site['latest_data_date'] = site_dates['latest'] if site_dates['latest'] else None
                site['oldest_data_date'] = site_dates['oldest'] if site_dates['oldest'] else None
                
                # 計算距今天數
                if site['latest_data_date']:
                    from datetime import datetime, date
                    if isinstance(site['latest_data_date'], str):
                        latest_date = datetime.strptime(site['latest_data_date'], '%Y-%m-%d').date()
                    else:
                        latest_date = site['latest_data_date']
                    site['days_since_latest'] = (date.today() - latest_date).days
                else:
                    site['days_since_latest'] = None
        
        return summary, sites
        
    except Exception as e:
        logger.error(f"Failed to get database progress: {e}")
        return {
            'total_sites': 0,
            'total_keywords': 0,
            'latest_date': None,
            'oldest_date': None
        }, []

@app.route('/api/logs')
def get_logs():
    """獲取應用程式 log"""
    try:
        lines = request.args.get('lines', '50', type=int)
        since = request.args.get('since')
        
        log_file = 'app.log'
        logs = []
        latest_timestamp = None
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
            # 如果指定了 since 時間戳，只返回之後的 log
            if since:
                filtered_lines = []
                for line in all_lines:
                    try:
                        # 提取時間戳 (假設格式: 2025-06-08 22:59:04,108)
                        timestamp_str = line.split(' - ')[0] if ' - ' in line else line[:23]
                        log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                        since_time = datetime.fromisoformat(since.replace('Z', ''))
                        
                        if log_time > since_time:
                            filtered_lines.append(line.strip())
                            latest_timestamp = log_time.isoformat()
                    except:
                        # 如果無法解析時間，就包含這行
                        filtered_lines.append(line.strip())
                        
                logs = filtered_lines
            else:
                # 返回最後 N 行
                logs = [line.strip() for line in all_lines[-lines:]]
                if logs:
                    try:
                        # 嘗試從最後一行提取時間戳
                        last_line = logs[-1]
                        timestamp_str = last_line.split(' - ')[0] if ' - ' in last_line else last_line[:23]
                        latest_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f').isoformat()
                    except:
                        latest_timestamp = datetime.now().isoformat()
        
        return jsonify({
            'logs': logs,
            'latest_timestamp': latest_timestamp,
            'total_lines': len(logs)
        })
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        return jsonify({
            'error': str(e),
            'logs': [],
            'latest_timestamp': None
        }), 500

@app.route('/health')
def health():
    """健康檢查"""
    try:
        # 檢查數據庫連接
        db_status = database.check_connection()
        
        return jsonify({
            'status': 'healthy' if db_status else 'unhealthy',
            'database': 'connected' if db_status else 'disconnected',
            'timestamp': datetime.now().isoformat(),
            'uptime': 'running'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/sync/daily')
def sync_daily():
    """每日數據同步"""
    try:
        if 'credentials' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # 獲取所有站點
        sites = database.get_sites()
        results = []
        
        for site in sites:
            try:
                # 同步昨天的數據
                yesterday = datetime.now() - timedelta(days=1)
                result = gsc_client.sync_site_data(
                    site['domain'],
                    yesterday.strftime('%Y-%m-%d'),
                    yesterday.strftime('%Y-%m-%d')
                )
                results.append({
                    'site': site['domain'],
                    'status': 'success',
                    'records': result.get('count', 0)
                })
            except Exception as e:
                logger.error(f"Failed to sync {site['domain']}: {e}")
                results.append({
                    'site': site['domain'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'message': 'Daily sync completed',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Daily sync failed: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 初始化數據庫
    database.init_db()
    
    # 啟動服務
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8000)),  # 預設改為 8000
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    ) 