#!/usr/bin/env python3
"""
列出所有可存取的 GSC 網站
"""
from sync import get_gsc_client

def list_sites():
    client = get_gsc_client()
    
    print("列出所有可存取的網站...")
    try:
        response = client.sites().list().execute()
        sites = response.get('siteEntry', [])
        
        if sites:
            print(f"\n找到 {len(sites)} 個網站：")
            for site in sites:
                print(f"  - {site['siteUrl']} ({site['permissionLevel']})")
        else:
            print("沒有找到任何網站")
            
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    list_sites()