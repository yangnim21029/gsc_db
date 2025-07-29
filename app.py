#!/usr/bin/env python3
"""
Flask API for GSC Data
"""
from flask import Flask, request, jsonify, make_response
import io
from gsc_mcp import track_pages as track_pages_func, compare_periods as compare_periods_func, pages_queries as pages_queries_func

app = Flask(__name__)

@app.route("/track_pages", methods=["POST"])
def track_pages():
    """追蹤一組頁面和關鍵字"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # 必要參數檢查
        if not data.get("site") or not data.get("pages"):
            return jsonify({"error": "Missing required parameters: site and pages"}), 400
        
        # 呼叫查詢函數
        results = track_pages_func(
            site=data["site"],
            pages=data["pages"],
            keywords=data.get("keywords", []),
            days=data.get("days", 30)
        )
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pages_queries", methods=["POST"])
def pages_queries_api():
    """查詢頁面實際排名的關鍵字"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # 必要參數檢查
        if not data.get("site") or not data.get("pages"):
            return jsonify({"error": "Missing required parameters: site and pages"}), 400
        
        # 呼叫查詢函數
        results = pages_queries_func(
            site=data["site"],
            pages=data["pages"]
        )
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/compare_periods", methods=["POST"])
def api_compare_periods():
    """比較兩個時間段的效能"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # 必要參數檢查
        if not data.get("site"):
            return jsonify({"error": "Missing required parameter: site"}), 400
        
        # 呼叫查詢函數
        result = compare_periods_func(
            site=data["site"],
            period_type=data.get("period_type", "week"),  # week, month, custom
            custom_periods=data.get("custom_periods", {})  # 自訂時間段
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, port=port)


if __name__ == "__main__":
    main()