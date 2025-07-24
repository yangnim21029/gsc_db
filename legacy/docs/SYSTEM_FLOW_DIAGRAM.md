# GSC Database System Flow Diagram

## Overview

This document describes the complete system architecture and data flow of the GSC Database Management System, including all components, services, and their interactions.

## System Architecture

```mermaid
graph TB
    subgraph "External Services"
        GSC[Google Search Console API]
    end

    subgraph "CLI Application"
        CLI[GSC-CLI Command Line]

        subgraph "Commands"
            AUTH[auth login]
            SITE[site add/list]
            SYNC[sync daily/hourly]
            ANALYZE[analyze report]
        end

        CLI --> AUTH
        CLI --> SITE
        CLI --> SYNC
        CLI --> ANALYZE
    end

    subgraph "Web API"
        API[FastAPI Server]

        subgraph "API Routers"
            HEALTH[/health]
            SITES[/api/v1/sites/]
            ANALYTICS[/api/v1/analytics/]
            QUERIES[/api/v1/sites/{id}/queries/]
            PERF[/api/v1/page-keyword-performance/]
            SYNC_API[/api/v1/sync/]
            DIAG[/api/v1/diagnostics/]
        end

        API --> HEALTH
        API --> SITES
        API --> ANALYTICS
        API --> QUERIES
        API --> PERF
        API --> SYNC_API
        API --> DIAG
    end

    subgraph "Core Services"
        DI[Dependency Injection Container]

        subgraph "Service Layer"
            GSC_CLIENT[GSC Client Service]
            SITE_SVC[Site Service]
            ANALYSIS_SVC[Analysis Service]
            AGG_SVC[Data Aggregation Service]
            HOURLY_DB[Hourly Database Service]
        end

        DI --> GSC_CLIENT
        DI --> SITE_SVC
        DI --> ANALYSIS_SVC
        DI --> AGG_SVC
        DI --> HOURLY_DB
    end

    subgraph "Data Layer"
        DB_WRAPPER[ProcessSafeDatabase]
        DB[SQLite Database]

        DB_WRAPPER --> DB

        subgraph "Tables"
            SITES_TBL[sites]
            DAILY_TBL[gsc_performance_data]
            HOURLY_TBL[gsc_hourly_data]
            SYNC_TBL[sync_status]
        end

        DB --> SITES_TBL
        DB --> DAILY_TBL
        DB --> HOURLY_TBL
        DB --> SYNC_TBL
    end

    %% Connections
    GSC_CLIENT --> GSC

    AUTH --> GSC_CLIENT
    SITE --> SITE_SVC
    SYNC --> GSC_CLIENT
    SYNC --> DB_WRAPPER
    ANALYZE --> ANALYSIS_SVC

    SITES --> SITE_SVC
    ANALYTICS --> ANALYSIS_SVC
    QUERIES --> DB_WRAPPER
    PERF --> ANALYSIS_SVC
    SYNC_API --> DB_WRAPPER
    DIAG --> DB_WRAPPER
    DIAG --> GSC_CLIENT

    SITE_SVC --> DB_WRAPPER
    ANALYSIS_SVC --> DB_WRAPPER
    AGG_SVC --> DB_WRAPPER
    HOURLY_DB --> DB_WRAPPER

    CLI --> DI
    API --> DI
```

## Data Synchronization Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant SyncService
    participant GSCClient
    participant GSC_API as Google Search Console
    participant Database

    User->>CLI: just sync-site 1 7
    CLI->>SyncService: sync_daily_data(site_id=1, days=7)

    loop For each day
        SyncService->>GSCClient: get_search_analytics(date)
        GSCClient->>GSC_API: searchanalytics.query()
        GSC_API-->>GSCClient: Performance data
        GSCClient-->>SyncService: Data rows

        SyncService->>Database: Check existing data
        Database-->>SyncService: Existing count

        alt Skip mode (default)
            SyncService->>Database: Insert new records only
        else Overwrite mode
            SyncService->>Database: Delete existing + Insert all
        end

        SyncService->>Database: Update sync_status
    end

    SyncService-->>CLI: Sync complete
    CLI-->>User: Success message
```

## API Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Router
    participant Service
    participant Database

    Client->>API: POST /api/v1/analytics/ranking-data
    API->>Router: Route to analytics.py
    Router->>Service: get_performance_data()

    alt Exact Match Mode
        Service->>Database: SELECT WHERE query = ?
    else Partial Match Mode
        Service->>Database: SELECT all data
        Service->>Service: Filter in memory (LIKE)
    end

    Database-->>Service: Raw data

    alt Daily Aggregation
        Service->>Service: Group by date/query
        Service->>Service: Calculate averages
    else Raw Mode
        Service->>Service: Return as-is
    end

    Service-->>Router: Processed data
    Router->>Router: Convert to response model
    Router-->>API: JSON response
    API-->>Client: HTTP 200 + data
```

## Multi-Process Database Access

```mermaid
graph LR
    subgraph "Process 1 (Worker 1)"
        W1[FastAPI Worker]
        PS1[ProcessSafeDatabase]
        C1[SQLite Connection 1]
    end

    subgraph "Process 2 (Worker 2)"
        W2[FastAPI Worker]
        PS2[ProcessSafeDatabase]
        C2[SQLite Connection 2]
    end

    subgraph "Process 3 (CLI)"
        CLI[CLI Process]
        PS3[ProcessSafeDatabase]
        C3[SQLite Connection 3]
    end

    subgraph "Database"
        WAL[WAL Mode]
        DB[(SQLite Database)]
    end

    W1 --> PS1
    PS1 --> C1
    C1 --> WAL

    W2 --> PS2
    PS2 --> C2
    C2 --> WAL

    CLI --> PS3
    PS3 --> C3
    C3 --> WAL

    WAL --> DB

    style WAL fill:#f9f,stroke:#333,stroke-width:2px
```

## Query Search Feature Flow

```mermaid
graph TD
    A[User Request] -->|Search "理髮"| B{Search Type?}

    B -->|Simple Search| C[GET /queries/search]
    B -->|Complex Filter| D[POST /analytics/ranking-data]

    C --> E[Direct SQL LIKE Query]
    E --> F[SELECT WHERE query LIKE '%理髮%']

    D --> G{Matching Mode?}
    G -->|exact| H[Query Each Term]
    G -->|partial| I[Get All + Filter]

    H --> J[SELECT WHERE query = '理髮']
    I --> K[SELECT all queries]
    K --> L[Filter: if '理髮' in query]

    F --> M[Return Results]
    J --> M
    L --> M

    M --> N[Format Response]
    N --> O[JSON to Client]
```

## Hourly Data Synchronization

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant HourlyDB as Hourly Database Service
    participant GSCClient
    participant GSC_API as Google Search Console
    participant Database

    User->>CLI: just sync-hourly-multiple "4 5 11" 2
    CLI->>HourlyDB: sync_hourly_data(site_id, days=2)

    Note over HourlyDB: Check last 3 days only<br/>(GSC limitation)

    loop For each hour (24 hours x 2 days)
        HourlyDB->>GSCClient: get_search_analytics(hour_range)
        GSCClient->>GSC_API: searchanalytics.query()
        GSC_API-->>GSCClient: Hourly data
        GSCClient-->>HourlyDB: Data rows

        HourlyDB->>Database: Batch insert
        Database-->>HourlyDB: Success
    end

    HourlyDB->>Database: Update hourly sync status
    HourlyDB-->>CLI: Sync complete
    CLI-->>User: Progress report
```

## Data Aggregation Pipeline

```mermaid
graph TD
    A[Hourly Data] --> B[Aggregation Service]

    B --> C{Aggregation Type}

    C -->|By Page| D[Group by URL]
    C -->|By Query| E[Group by Keyword]
    C -->|By Date| F[Group by Day]

    D --> G[Calculate Metrics]
    E --> G
    F --> G

    G --> H[Sum Clicks/Impressions]
    G --> I[Average CTR/Position]
    G --> J[Count Occurrences]

    H --> K[Store in daily_data table]
    I --> K
    J --> K

    K --> L[Available for API]
```

## Error Handling and Recovery

```mermaid
stateDiagram-v2
    [*] --> Idle

    Idle --> Syncing: Start sync

    Syncing --> CheckQuota: API call
    CheckQuota --> RateLimited: Quota exceeded
    CheckQuota --> Processing: Quota OK

    RateLimited --> Waiting: Exponential backoff
    Waiting --> CheckQuota: Retry

    Processing --> Success: Data saved
    Processing --> NetworkError: Connection failed
    Processing --> DBLocked: Database busy

    NetworkError --> Retrying: Automatic retry
    Retrying --> Processing: Retry attempt
    Retrying --> Failed: Max retries

    DBLocked --> WaitingDB: Wait 30s
    WaitingDB --> Processing: Retry

    Success --> UpdateStatus: Update sync_status
    Failed --> UpdateStatus: Mark as failed

    UpdateStatus --> Idle: Complete
```

## Component Dependencies

```mermaid
graph BT
    subgraph "Infrastructure"
        CONFIG[Config/Settings]
        LOGGER[Logging]
    end

    subgraph "Database Layer"
        DB[Database Service]
        PS_DB[ProcessSafeDatabase]
    end

    subgraph "External Services"
        GSC[GSC Client]
    end

    subgraph "Business Services"
        SITE[Site Service]
        ANALYSIS[Analysis Service]
        HOURLY[Hourly DB Service]
        AGG[Aggregation Service]
    end

    subgraph "Application Layer"
        CLI[CLI Commands]
        API[API Endpoints]
    end

    subgraph "Entry Points"
        APP[app.py]
        WEB[web/api/main.py]
    end

    DB --> CONFIG
    DB --> LOGGER
    PS_DB --> DB

    GSC --> CONFIG
    GSC --> LOGGER

    SITE --> PS_DB
    ANALYSIS --> PS_DB
    HOURLY --> PS_DB
    HOURLY --> GSC
    AGG --> PS_DB

    CLI --> SITE
    CLI --> ANALYSIS
    CLI --> HOURLY
    CLI --> AGG

    API --> SITE
    API --> ANALYSIS
    API --> AGG

    APP --> CLI
    WEB --> API
```

## Key Features and Flows

### 1. **Authentication Flow**
- User runs `just auth` or `gsc-cli auth login`
- Opens browser for Google OAuth
- Stores credentials locally
- All subsequent API calls use stored credentials

### 2. **Site Management**
- Add sites with domain verification
- List active sites
- Store site metadata in database
- Support multiple domain formats

### 3. **Data Synchronization**
- **Daily sync**: Historical data with 2-3 day delay
- **Hourly sync**: Recent 3 days with hourly precision
- **Batch sync**: Multiple sites sequentially
- **Progress tracking**: Real-time status updates

### 4. **API Endpoints**
- **Health check**: Process and connection status
- **Site listing**: All configured sites
- **Analytics**: Flexible data queries with filters
- **Query search**: Partial matching for keywords
- **Performance**: Page-keyword combinations
- **CSV export**: Direct data download

### 5. **Data Processing**
- **Aggregation modes**: Raw vs daily summarized
- **Matching modes**: Exact vs partial for queries
- **Time ranges**: Flexible date filtering
- **Grouping**: By query, page, or date

### 6. **Concurrency & Safety**
- Process-safe database connections
- WAL mode for concurrent access
- Automatic retry with backoff
- Connection pooling per process

## Deployment Architecture

```mermaid
graph TD
    subgraph "Production Deployment"
        LB[Load Balancer]

        subgraph "Web Workers"
            W1[Gunicorn Worker 1]
            W2[Gunicorn Worker 2]
            W3[Gunicorn Worker 3]
        end

        subgraph "Background Jobs"
            CRON[Cron Scheduler]
            SYNC_JOB[Daily Sync Job]
        end

        subgraph "Storage"
            DB[(SQLite Database)]
            BACKUP[Backup Storage]
        end
    end

    LB --> W1
    LB --> W2
    LB --> W3

    W1 --> DB
    W2 --> DB
    W3 --> DB

    CRON --> SYNC_JOB
    SYNC_JOB --> DB

    DB --> BACKUP
```

## Performance Considerations

1. **Sequential Processing**: GSC API calls are sequential to avoid rate limits
2. **Batch Operations**: Database inserts use batch operations
3. **Connection Reuse**: Per-process connection pooling
4. **Data Pagination**: API responses limited to prevent memory issues
5. **Index Optimization**: Database indexes on common query patterns

## Security Features

1. **OAuth 2.0**: Secure Google authentication
2. **Local Credentials**: Encrypted credential storage
3. **Process Isolation**: Each process has isolated connections
4. **Input Validation**: Pydantic models validate all inputs
5. **SQL Injection Prevention**: Parameterized queries throughout

## Monitoring Points

- API response times
- Sync job success/failure rates
- Database connection pool status
- GSC API quota usage
- Error rates by endpoint
- Data freshness metrics
