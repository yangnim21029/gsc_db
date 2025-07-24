但問題就是如此，

本頁面由 Cloud Translation API 翻譯而成。
Switch to English
首頁
產品
Search Console API
指南
這對你有幫助嗎？

傳送批次要求

bookmark_border

本文說明如何批次處理 API 呼叫，以減少用戶端必須建立的 HTTP 連線數量。

本文專門說明如何透過傳送 HTTP 要求來提交批次要求。如果您是使用 Google 用戶端程式庫提交批次要求，請參閱用戶端程式庫的說明文件。

總覽
用戶端建立的每個 HTTP 連線都會造成一定程度的負擔。Google Search Console API 支援批次作業，可以讓用戶端在單一 HTTP 要求中加入數個 API 呼叫。

以下是您可能想要使用批次作業的狀況範例：

您剛開始使用 API，有許多資料需要上傳。
使用者在您的應用程式離線 (中斷與網際網路的連線) 時變更了資料，所以應用程式必須傳送許多更新和刪除資料，讓本機資料能夠與伺服器同步處理。
在任一案例中，都不需要個別傳送每一個呼叫，只需將這些呼叫分組後組成單一 HTTP 要求。所有內部要求都必須前往相同的 Google API。

單一批次要求最多能包含 1,000 個呼叫。如果您發出的呼叫數量超過這個上限，請使用多個批次要求。

注意：Google Search Console API 批次系統使用的語法與 OData 批次處理系統相同，但語意不同。

批次詳細資料
批次要求是由多個 API 呼叫合併成一個 HTTP 要求，系統會將這個要求傳送至 API 探索文件中指定的 batchPath。預設路徑為 /batch/api_name/api_version。本節詳細說明批次語法，並在後半段提供範例。

注意：組成批次的 n 個要求在用量限制中會算成 n 個要求，而不是一個要求。批次要求會先分解成一組要求再進行處理。

批次要求的格式
批次要求是單一標準 HTTP 要求，內含多個使用 multipart/mixed 內容類型的 Google Search Console API 呼叫。在主要 HTTP 要求中，每個分部都含有一個巢狀的 HTTP 要求。

每個部分都以專屬的 Content-Type: application/http HTTP 標頭開頭。也可以有選用的 Content-ID 標頭。不過，部分標頭只是用來標示部分開頭，與巢狀要求分開。伺服器將批次要求展開為個別要求後，就會忽略部分標頭。

每個部分的主體都是一個完整的 HTTP 要求，具有自己的動詞、網址、標頭和內文。HTTP 要求只能包含 URL 的路徑部分；批次要求禁止納入完整的 URL。

外部批次要求的 HTTP 標頭 (除了 Content- 標頭，例如 Content-Type) 會套用至批次中的每個要求。如果您在外部要求和個別呼叫中均指定所提供的 HTTP 標頭，則個別呼叫標頭的值會覆寫外部批次要求標頭的值。個別呼叫的標頭只會套用於該呼叫。

例如，如果您提供 Authorization 標頭用於特定呼叫，則該標頭只會套用於該呼叫。如果您提供 Authorization 標頭用於外部要求，則除非個別呼叫以自己的 Authorization 標頭覆寫所提供的標頭，否則所提供的 Authorization 標頭會套用於所有個別呼叫。

當伺服器收到批次要求時，即會將外部要求的查詢參數和標頭 (在適用情況下) 套用至每一個分部，然後將每個分部視為不同的 HTTP 要求。

回應批次要求
伺服器的回應是單一標準 HTTP 回應，內含 multipart/mixed 內容類型；每個部分都是對批次要求中某個要求的回應，並按照要求的順序排列。

就像要求中的分部一樣，每個回應分部都含有完整的 HTTP 回應，包括狀態碼、標頭和內文；就像要求中的部分一樣，每個回應部分前面都會加上 Content-Type 標頭，標示部分的開頭。

如果要求的特定部分含有 Content-ID 標頭，則回應的對應部分就會含有相符的 Content-ID 標頭，原始值前方會加上字串 response-，如以下範例所示。

注意：伺服器可能會以任意順序執行您的呼叫。不要期望呼叫會按您的指定順序執行。如果您想要確保兩個呼叫依指定順序執行，就不能以單一要求傳送它們，而要先傳送第一個呼叫，然後等到第一個呼叫的回應後才能傳送第二個呼叫。

範例
以下範例顯示批次作業的使用，其中的一般 (虛構) API 稱為 Farm API。不過，同樣的概念也適用於 Google Search Console API。

批次要求範例

POST /batch/farm/v1 HTTP/1.1
Authorization: Bearer your_auth_token
Host: www.googleapis.com
Content-Type: multipart/mixed; boundary=batch_foobarbaz
Content-Length: total_content_length

--batch_foobarbaz
Content-Type: application/http
Content-ID: <item1:12930812@barnyard.example.com>

GET /farm/v1/animals/pony

--batch_foobarbaz
Content-Type: application/http
Content-ID: <item2:12930812@barnyard.example.com>

PUT /farm/v1/animals/sheep
Content-Type: application/json
Content-Length: part_content_length
If-Match: "etag/sheep"

{
"animalName": "sheep",
"animalAge": "5"
"peltColor": "green",
}

--batch_foobarbaz
Content-Type: application/http
Content-ID: <item3:12930812@barnyard.example.com>

GET /farm/v1/animals
If-None-Match: "etag/animals"

--batch_foobarbaz--
批次回應範例
這是前一節中範例要求的回應。

HTTP/1.1 200
Content-Length: response_total_content_length
Content-Type: multipart/mixed; boundary=batch_foobarbaz

--batch_foobarbaz
Content-Type: application/http
Content-ID: <response-item1:12930812@barnyard.example.com>

HTTP/1.1 200 OK
Content-Type application/json
Content-Length: response_part_1_content_length
ETag: "etag/pony"

{
"kind": "farm#animal",
"etag": "etag/pony",
"selfLink": "/farm/v1/animals/pony",
"animalName": "pony",
"animalAge": 34,
"peltColor": "white"
}

--batch_foobarbaz
Content-Type: application/http
Content-ID: <response-item2:12930812@barnyard.example.com>

HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: response_part_2_content_length
ETag: "etag/sheep"

{
"kind": "farm#animal",
"etag": "etag/sheep",
"selfLink": "/farm/v1/animals/sheep",
"animalName": "sheep",
"animalAge": 5,
"peltColor": "green"
}

--batch_foobarbaz
Content-Type: application/http
Content-ID: <response-item3:12930812@barnyard.example.com>

HTTP/1.1 304 Not Modified
ETag: "etag/animals"

--batch_foobarbaz--
這對你有幫助嗎？

本頁面由 Cloud Translation API 翻譯而成。
Switch to English
首頁
產品
Search Console API
指南
這對你有幫助嗎？

API 使用提示

bookmark_border

本文說明提升應用程式成效的幾個技巧。在某些情況下，我們會使用其他 API 或通用 API 的範例來說明這些技巧背後的概念。然而，同樣的概念也適用於 Google Search Console API。

使用 gzip 壓縮
要減少每個要求占用的頻寬，最簡單的方法就是使用 gzip 壓縮檔。雖然此方法需要額外的 CPU 作業時間解壓縮，但相對可省下可觀的網路成本。

如果要接收以 gzip 編碼的回應，您必須執行下列兩項操作：設定 Accept-Encoding 標頭，並修改您的使用者代理程式來加入字串 gzip。以下是一個啟用 gzip 壓縮的正確 HTTP 標頭格式範例：

Accept-Encoding: gzip
User-Agent: my program (gzip)
使用部分資源
另一種提高 API 呼叫效能的方式，就是只要求您想要的部分資料。這麼做可避免讓您的應用程式傳輸、剖析及儲存不需要的欄位，進而更有效地使用網路、CPU 及記憶體等資源。

部分回應
根據預設，伺服器會在處理要求後傳回完整的資源表示法。為改善成效，您可以要求伺服器只傳送您真正需要的欄位，並改為取得「部分回應」。

如果要請求部分回應，請使用 fields 要求參數來指定您想要傳回的欄位。您可以將此參數搭配任何會傳回回應資料的要求使用。

範例
以下範例顯示 fields 參數與某個通用 (虛構) 的「Demo」API 的搭配用法。

簡易要求：此 HTTP GET 要求會省略 fields 參數，並傳回完整的資源。

https://www.googleapis.com/demo/v1
完整資源回應：完整資源資料包括下列欄位 (為節省篇幅，此處省略許多其他欄位)。

{
"kind": "demo",
...
"items": [
{
"title": "First title",
"comment": "First comment.",
"characteristics": {
"length": "short",
"accuracy": "high",
"followers": ["Jo", "Will"],
},
"status": "active",
...
},
{
"title": "Second title",
"comment": "Second comment.",
"characteristics": {
"length": "long",
"accuracy": "medium"
"followers": [ ],
},
"status": "pending",
...
},
...
]
}
要求部分回應：以下是對相同資源發出的要求，其中使用了 fields 參數，以大幅減少傳回的資料量。

https://www.googleapis.com/demo/v1?fields=kind,items(title,characteristics/length)
部分回應：在上方的要求回應中，伺服器傳回的回應只包含種類資訊，以及經過簡化的項目陣列 (只包含個別項目的 HTML 標題和長度特性資訊)。

200 OK

{
"kind": "demo",
"items": [{
"title": "First title",
"characteristics": {
"length": "short"
}
}, {
"title": "Second title",
"characteristics": {
"length": "long"
}
},
...
]
}
請注意，回應是一個 JSON 物件，且此物件只包含選定的欄位及其所含的父項物件。

以下將詳述如何設定 fields 參數的格式，接著再進一步說明回應中實際傳回的內容。

Fields 參數語法摘要
fields 要求參數值的格式約略以 XPath 語法為基礎。支援的語法簡述如下，其他範例如下節所示。

使用以逗號分隔的清單來選取多個欄位。
使用 a/b 在 a 欄位的巢狀結構內選取 b 欄位；使用 a/b/c 在 b 的巢狀結構內選取 c 欄位。
例外狀況：如果 API 回應使用「data」包裝函式，也就是在 data 物件中建立看起來像 data: { ... } 的巢狀回應，請勿在 fields 規格中加入「data」。將 data 物件加入類似 data/a/b 的 fields 規格會造成錯誤。請改為只使用 fields 規格，例如 a/b。

透過在括號「( )」中放入運算式，使用子選擇器來要求一組指定的陣列或物件子欄位。
例如：fields=items(id,author/email) 只會傳回項目陣列中各個元素的項目 ID 以及作者的電子郵件地址。您也可以指定單一子欄位，其中 fields=items(id) 等於 fields=items/id。

必要時，在欄位選取項目中使用萬用字元。
例如：fields=items/pagemap/\* 可選取網頁地圖中的所有物件。

使用 fields 參數的其他範例
以下範例包含 fields 參數值會如何影響回應的說明。

附註：和所有查詢參數值一樣，fields 參數值也必須使用網址編碼。為方便閱讀，本文中的範例會省略編碼。

找出您要傳回的欄位，或「選取欄位」。
fields 要求參數值是以逗號分隔的欄位清單，每個欄位是根據回應的根來指定。因此，如果您執行的是清單作業，回應會是一個集合，其中通常包含資源陣列。如果您執行的作業傳回單一資源，欄位會根據該資源來指定。如果您選取的欄位是一個陣列 (或陣列的一部分)，則伺服器會傳回該陣列中所有元素的選定部分。

以下提供幾個集合層級的範例：
範例 效果
items 傳回項目陣列中的所有元素，包括每個元素中的所有欄位，但不包含其他欄位。
etag,items 同時傳回 etag 欄位和項目陣列中的所有元素。
items/title 只傳回項目陣列中所有元素的 title 欄位。

每當傳回巢狀欄位時，回應會包含其所含父項物件。父欄位不會包含任何其他的子欄位 (除非已同時明確地選擇這些欄位)。
context/facets/label 只傳回 facets 陣列所有成員的 label 欄位，其本身是以巢狀結構嵌入 context 物件中。
items/pagemap/\*/title 針對項目陣列中的每個元素，只傳回屬於 pagemap 子項之所有物件的 title 欄位 (如果有的話)。

以下提供幾個資源層級的範例：
範例 效果
title 傳回所要求資源的 title 欄位。
author/uri 傳回所要求資源中 author 物件的 uri 子欄位。
links/\*/href
傳回屬於 links 子項之所有物件的 href 欄位。
使用「子選取項目」只請求指定欄位部分。
根據預設，如果您的要求指定特定的欄位，伺服器會傳回整個物件或陣列元素。您可以指定只包含特定子欄位的回應。方法很簡單，只要使用「( )」子選取項目語法即可，如下列範例所示。
範例 效果
items(title,author/uri) 只傳回項目陣列中每個元素的 title 值以及作者的 uri 值。
處理部分回應
伺服器處理包含 fields 查詢參數的有效要求後，會傳回一個 HTTP 200 OK 狀態碼，以及所要求的資料。如果 fields 查詢參數發生錯誤或無效，伺服器會傳回 HTTP 400 Bad Request 狀態碼和錯誤訊息，指出使用者選擇欄位時發生的錯誤 (例如 "Invalid field selection a/b")。

以下是上方簡介一節中的部分回應範例。此要求使用 fields 參數來指定要傳回的欄位。

https://www.googleapis.com/demo/v1?fields=kind,items(title,characteristics/length)
部分回應的樣式如下所示：

200 OK

{
"kind": "demo",
"items": [{
"title": "First title",
"characteristics": {
"length": "short"
}
}, {
"title": "Second title",
"characteristics": {
"length": "long"
}
},
...
]
}

取得超過 25,000 列
如果查詢的資料列超過 25,000 列，您可以傳送多個查詢並每次遞增 startRow 值，以 25,000 列為單位分批要求資料。計算擷取的資料列數；如果擷取的資料列數少於要求的資料列數，就表示已擷取所有資料。 如果要求的資料範圍剛好是資料邊界 (例如，資料有 25,000 列，而您要求的 startRow=0 和 rowLimit=25000)，則在下一次呼叫時，您會收到空白回應。

指定日期範圍內的前 1 到 25,000 項熱門行動查詢，按點擊次數遞減排序
代碼

request = {
'startDate': flags.start_date,
'endDate': flags.end_date,
'dimensions': ['query'],
'dimensionFilterGroups': [{
'filters': [{
'dimension': 'device',
'expression': 'mobile'
}]
}],
'rowLimit': 25000,
'startRow': 0
}
指定日期範圍內的熱門行動查詢 (25,001 到 50,000 筆)，按點擊次數遞減排序
代碼

request = {
'startDate': flags.start_date,
'endDate': flags.end_date,
'dimensions': ['query'],
'dimensionFilterGroups': [{
'filters': [{
'dimension': 'device',
'expression': 'mobile'
}]
}],
'rowLimit': 25000,
'startRow': 25000
}
取得所有資料
請參閱「查詢所有搜尋流量」一文。

正在取得成效資料

bookmark_border

查詢每日的資料量，即可快速查詢效能資料，而且不會超過配額。

您必須選擇要納入資料中的資訊：哪些搜尋類型 (網頁、圖片、影片等) 以及指定維度 (網頁、查詢、國家/地區或裝置)，以及是否要依網頁或資源將結果分組。查詢網頁和/或查詢字串時，某些資料可能會遭到捨棄 (瞭解原因)。

總覽
建議您使用下方所述的查詢樣式，每天執行查詢，涵蓋一天的資料。每日查詢一天的資料不應超過每日配額。系統通常需 2 到 3 天後才能取得資料；您可以查看過去 10 天內依日期分組的簡單查詢，瞭解最新資料。編寫查詢時：
選擇是否要依網頁或資源分類結果。
選擇要在查詢中納入更完整的計數或維度。注意：您必須使用兩步驟程序查詢搜尋外觀資料 (AMP、藍色連結、複合式搜尋結果等)。
重新執行相同查詢，將要求中的 startRow 值調高 25,000，直到抵達最後一頁 (傳回 0 列的回應)，以頁面瀏覽結果。
您可以選擇使用其他 type 參數執行相同查詢。
以下是單一查詢的虛擬程式碼範例。針對您想要的資料，您可以每天 為每個 type 值執行一次此測試。

int maxRows = 25000; // Current max response size
int i = 0;
do {
response = Request(startDate = 3_days_ago,
endDate = 3_days_ago,
... add dimensions, type ...
rowLimit = maxRows,
startRow = i \* maxRows);
i++;
… // Do something with the response data.
} while (response.rows.count() != 0); // Page through all result rows
數據用量上限
除了 API 用量配額之外，Search Analytics 方法每天最多能為每種搜尋類型 (網頁、圖片等) 顯示 5 萬列資料 (按點擊次數排序)。

查詢詳細資料
您可以查詢依網頁或資源分組的資料。

已依網頁分組
如要獲得準確的計數，您必須略過網頁和查詢維度，如下所示：

"startDate": "2018-06-01",
"endDate": "2018-06-01",
"dimensions": ["country", "device"],
"type": "web",
"aggregationType": "byPage"
startDate / endDate：選取同一日期，即可選用一天的回溯期。
dimensions：視需要加入 country 和/或 device。
type：在獨立查詢中視需要以 每個 type 值進行列舉。
aggregationType：必須為 byPage。
如需網頁和/或查詢資訊等詳細資訊，請執行以下查詢，但您可能會遺失部分資料：

"startDate": "2018-06-01",
"endDate": "2018-06-01",
"dimensions": ["page", "query", "country", "device"],
"type": "web"
startDate / endDate：選取同一日期，即可選用一天的回溯期。
dimensions：包含 page。視需要納入 query、country 或 device 的任意組合。
type：在獨立查詢中視需要以 每個 type 值進行列舉。
已依資源分組
如要獲得準確的計數，您必須略過網頁和查詢維度，如下所示：

"startDate": "2018-06-01",
"endDate": "2018-06-01",
"dimensions": ["country", "device"],
"type": "web"
startDate / endDate：選取同一日期，即可選用一天的回溯期。
dimensions：視需要加入 country 和/或 device。
type：視需要在獨立查詢中，逐一列舉 每個 type 值。
如需查詢、國家/地區和/或裝置資訊等更詳細的資訊，系統可能會遺失部分資料，但您必須執行下列查詢：

"startDate": "2018-06-01",
"endDate": "2018-06-01",
"dimensions": ["query", "country", "device"],
"type": "web"
startDate / endDate：選取同一日期，即可選用一天的回溯期。
dimensions：視需要納入 query、country 或 device 的任意組合。
type：在獨立查詢中視需要以 每個 type 值進行列舉。
依網頁或資源將結果分組
依網頁 (而非資源) 分組結果時，曝光次數、點擊次數、排名和點閱率的計算方式會有所不同。瞭解詳情。

為什麼在要求詳細資訊時遺失資料？
依網頁和/或查詢分組時，系統可能會捨棄部分資料，以便在合理的運算資源內計算出結果。

取得搜尋外觀資料
搜尋外觀無法與其他維度一併提供。因此，如要查看網站的搜尋外觀資訊，請按照下列程序操作：

指定「searchAppearance」做為唯一的維度，這會依搜尋外觀類型將所有資料分組，而且沒有其他維度。
視需要執行第二次查詢，依照步驟 1 列出的其中一個搜尋外觀類型進行篩選，在查詢中加入任何所需維度 (網頁、國家/地區、查詢等)。
如要擷取多種搜尋外觀類型的資料，您必須針對步驟 1 列出的每個搜尋外觀類型執行第二個步驟。

第一個查詢：

取得網站上搜尋外觀類型的清單。

{
"startDate": "2018-05-01",
"endDate": "2018-05-31",
"type": "web",
"dimensions": [
"searchAppearance"
]
}
結果：

您的網站類型為 INSTANT_APP、AMP_BLUE_LINK 等。

"rows": [
{
"keys": [
"INSTANT_APP"
],
"clicks": 443024.0,
"impressions": 4109826.0,
"ctr": 0.10779629113251997,
"position": 1.088168452873674
},
{
"keys": [
"AMP_BLUE_LINK"
],
"clicks": 429887.0,
"impressions": 1.7090884E7,
"ctr": 0.025152999692701676,
"position": 7.313451603790653
},...
第二項查詢：

您可以按照步驟 1 提供的其中一種搜尋外觀類型進行篩選，並視需要篩選任何維度 (網頁、裝置等)。我們是根據 AMP_BLUE_LINK 進行篩選。

{
"startDate": "2018-05-01",
"endDate": "2018-05-31",
"type": "web",
"dimensions": [
"device" // and/or page, country, ...
],
"dimensionFilterGroups": [
{
"filters": [
{
"dimension": "searchAppearance",
"operator": "equals",
"expression": "AMP_BLUE_LINK"
}
]
}
]
}
結果：

AMP_BLUE_LINK 細目，依裝置類型顯示。

"rows": [
{
"keys": [
"MOBILE"
],
"clicks": 429887.0,
"impressions": 1.7090783E7,
"ctr": 0.025153148337323107,
"position": 7.31339517914422
},
{
"keys": [
"DESKTOP"
],
"clicks": 0.0,
"impressions": 66.0,
"ctr": 0.0,
"position": 12.257575757575758
},
...
