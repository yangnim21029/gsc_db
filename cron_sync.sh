#!/bin/bash
# cron_sync.sh - 每小時同步所有 GSC 站點資料

cd /Users/rose/Downloads/01_工作相關/面試求職/PressLogic/gsc_db

python sync.py sc-domain:businessfocus.io
python sync.py sc-domain:girlstyle.com
python sync.py sc-domain:holidaysmart.io
python sync.py sc-domain:mamidaily.com
python sync.py sc-domain:poplady-mag.com
python sync.py sc-domain:pretty.presslogic.com
python sync.py sc-domain:thekdaily.com
python sync.py sc-domain:thepetcity.co
python sync.py sc-domain:topbeautyhk.com
python sync.py sc-domain:urbanlifehk.com