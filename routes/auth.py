#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify, session, redirect, url_for
import logging
from services.gsc_client import GSCClient

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

gsc_client = GSCClient()

@auth_bp.route('/login')
def login():
    """開始OAuth登入流程"""
    try:
        auth_url = gsc_client.get_auth_url()
        return jsonify({
            'auth_url': auth_url,
            'message': '請訪問此URL進行Google Search Console授權'
        })
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/callback')
def callback():
    """處理OAuth回調"""
    try:
        code = request.args.get('code')
        if not code:
            return redirect('/home?error=auth_code_missing')
        
        success = gsc_client.handle_oauth_callback(code)
        if success:
            session['authenticated'] = True
            return redirect('/?success=login')
        else:
            return redirect('/?error=auth_failed')
            
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return redirect('/?error=' + str(e)[:50])

@auth_bp.route('/status')
def status():
    """檢查認證狀態"""
    try:
        is_auth = gsc_client.is_authenticated()
        return jsonify({
            'authenticated': is_auth,
            'session_active': session.get('authenticated', False)
        })
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect('/?success=logout') 