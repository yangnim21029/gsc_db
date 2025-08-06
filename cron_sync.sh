#!/bin/bash
# cron_sync.sh - 每小時同步所有 GSC 站點資料

poetry run python sync.py sc-domain:businessfocus.io
poetry run python sync.py sc-domain:girlstyle.com
poetry run python sync.py sc-domain:holidaysmart.io
poetry run python sync.py sc-domain:mamidaily.com
poetry run python sync.py sc-domain:poplady-mag.com
poetry run python sync.py sc-domain:pretty.presslogic.com
poetry run python sync.py sc-domain:thekdaily.com
poetry run python sync.py sc-domain:thepetcity.co
poetry run python sync.py sc-domain:topbeautyhk.com
poetry run python sync.py sc-domain:urbanlifehk.com