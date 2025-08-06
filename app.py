#!/usr/bin/env python3
"""
Flask API for GSC Data
"""
from flask import Flask, request, jsonify, make_response, render_template
from flask_cors import CORS
import io
import os
import math
from pathlib import Path
from dotenv import load_dotenv
import openai
from urllib.parse import unquote
from gsc_mcp import (
    track_pages as track_pages_func,
    compare_periods as compare_periods_func,
    pages_queries as pages_queries_func,
    query as query_func,
)

load_dotenv()

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    """Serve the main web UI"""
    return render_template("query.html")


@app.route("/api/sites", methods=["GET"])
def get_sites():
    """Get list of available sites from data directory"""
    try:
        data_dir = Path("data")
        if not data_dir.exists():
            return jsonify({"sites": []})

        sites = []
        for site_folder in data_dir.iterdir():
            if site_folder.is_dir():
                # Convert folder name back to site URL
                site_url = site_folder.name
                if site_url.startswith("sc-domain_"):
                    site_url = site_url.replace("sc-domain_", "sc-domain:", 1)
                site_url = site_url.replace("_", "/")
                # Decode URL encoding
                site_url = unquote(site_url)
                sites.append(site_url)

        return jsonify({"sites": sorted(sites)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def api_query():
    """Execute SQL query on GSC data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Required parameters
        if not data.get("site") or not data.get("sql"):
            return jsonify({"error": "Missing required parameters: site and sql"}), 400

        # Execute query using the MCP function
        results = query_func(
            site=data["site"], sql=data["sql"], data_type=data.get("data_type", "daily")
        )

        # Handle NaN values in results
        for row in results:
            for key, value in row.items():
                if isinstance(value, float) and math.isnan(value):
                    row[key] = None

        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/nl2sql", methods=["POST"])
def nl2sql():
    """Convert natural language to SQL"""
    try:
        data = request.get_json()
        if not data or not data.get("text"):
            return jsonify({"error": "No text provided"}), 400

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = (
            """Convert this to SQL. Available tables:
- {site}: columns are date (YYYY-MM-DD stored as VARCHAR), query, page, clicks, impressions, ctr, position
- {site_hourly}: columns are date (YYYY-MM-DD stored as VARCHAR), hour (0-23), query, page, clicks, impressions, ctr, position

CRITICAL RULES - YOU MUST FOLLOW THESE EXACTLY:
1. ALWAYS use {site} or {site_hourly} as table names - NEVER use just "site" or "site_hourly"
2. The curly braces {} are MANDATORY - without them the query will fail
3. Examples of CORRECT usage:
   - SELECT * FROM {site} WHERE date = '2025-08-01'
   - SELECT hour, SUM(clicks) FROM {site_hourly} GROUP BY hour
   - SELECT * FROM {site_hourly} WHERE hour = 9
4. Examples of INCORRECT usage (NEVER do this):
   - SELECT * FROM site WHERE date = '2025-08-01'  ❌
   - SELECT * FROM site_hourly WHERE hour = 9  ❌

OTHER IMPORTANT RULES:
1. The date column is stored as VARCHAR, so cast it with date::DATE when using date functions.
2. Use date::DATE instead of just date when extracting year/month.
3. If no LIMIT is specified and the query selects multiple rows, add LIMIT 100.
4. For hourly data, hour column is 0-23 where 0=midnight, 9=9am, 13=1pm, etc.
5. For queries with date filters, if the date is within the last 30 days from today, prefer using {site_hourly} table with GROUP BY date for daily aggregations, as hourly data is more complete for recent dates.
6. If user mentions hourly/hour/time-of-day keywords, use {site_hourly} table.

User question: """
            + data["text"]
            + """

Return only the SQL query, nothing else. Remember: ALWAYS use {site} or {site_hourly} with curly braces!"""
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        content = response.choices[0].message.content
        if content is None:
            return jsonify({"error": "No SQL query generated"}), 500

        sql = content.strip()
        # Clean markdown blocks
        sql = sql.replace("```sql", "").replace("```", "").strip()
        # Fix table placeholders for both daily and hourly tables
        sql = sql.replace(" site_hourly ", " {site_hourly} ").replace(
            "FROM site_hourly", "FROM {site_hourly}"
        )
        sql = sql.replace(" site ", " {site} ").replace("FROM site", "FROM {site}")
        # Determine data type from SQL
        data_type = "hourly" if "{site_hourly}" in sql else "daily"
        return jsonify({"sql": sql, "data_type": data_type})

    except Exception as e:
        import traceback

        print(f"Error in nl2sql: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/track_pages", methods=["POST"])
def track_pages():
    """追蹤一組頁面和關鍵字"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # 必要參數檢查
        if not data.get("site") or not data.get("pages"):
            return (
                jsonify({"error": "Missing required parameters: site and pages"}),
                400,
            )

        # 呼叫查詢函數
        results = track_pages_func(
            site=data["site"],
            pages=data["pages"],
            keywords=data.get("keywords", []),
            days=data.get("days", 30),
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
            return (
                jsonify({"error": "Missing required parameters: site and pages"}),
                400,
            )

        # 呼叫查詢函數
        results = pages_queries_func(site=data["site"], pages=data["pages"])

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
            custom_periods=data.get("custom_periods", {}),  # 自訂時間段
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/intent_analysis_data", methods=["POST"])
def intent_analysis_data():
    """分析搜索意圖並返回CSV"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # 必要參數檢查
        if not data.get("site"):
            return jsonify({"error": "Missing required parameter: site"}), 400

        # TODO: Implement intent analysis query
        # For now, return a placeholder response
        return jsonify({"message": "Intent analysis endpoint - implementation pending"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, port=port)


if __name__ == "__main__":
    main()
