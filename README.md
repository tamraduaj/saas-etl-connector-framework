# SaaS Connector Framework

A scalable, configuration-driven ETL framework for extracting data from SaaS platforms and loading it into AWS Iceberg tables. Currently supports Wrike with extensible architecture for additional connectors.

## Table of Contents
- [Introduction](#introduction)
- [Architecture Overview](#architecture-overview)
- [L2 Processing Layer](#l2-processing-layer)
- [Configuration](#configuration)
- [Code Flow](#code-flow)
- [Module Details](#module-details)
- [AWS Services Integration](#aws-services-integration)

---

## Introduction

This framework provides a robust, production-ready solution for:
- **L1 (Staging Layer)**: Data extraction from SaaS APIs with authentication and retry logic
- **L2 (Processing Layer)**: Advanced data transformation, business logic application, and refined data models
- **Data Loading**: Writing to AWS Iceberg tables with schema evolution on L1 table
- **Monitoring**: Enhanced CloudWatch logging and DynamoDB-based execution tracking
- **Configuration Management**: DynamoDB-stored configurations with validation for both L1 and L2 processes

---

## Architecture Overview

```
                    L1 (Staging Layer)
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   main.py   │───▶│ WrikeHandler │───▶│WrikeConnector│───▶│IcebergWriter │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   Logger    │    │  DynamoDB    │    │SecretsManager│    │    Spark     │
│ CloudWatch  │    │   Config     │    │    Auth     │    │   Session    │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                              │
                                              ▼
                    L2 (Processing Layer)
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   main.py   │───▶│L2WrikeHandler│───▶│ETLProcessor │───▶│IcebergWriter │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   Logger    │    │ L2 DynamoDB  │    │IcebergReader│    │    Spark     │
│ CloudWatch  │    │   Config     │    │   Parsers   │    │   Session    │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
```

### Key Components:
- **Entry Point**: `main.py` - AWS Glue job entry point with parameter validation and process type routing
- **L1 Handler Layer**: Platform-specific handlers (e.g., `WrikeHandler`) for data extraction orchestration
- **L1 Connector Layer**: Data extraction and basic transformation logic (`WrikeConnector`)
- **L2 Handler Layer**: Advanced processing handlers (e.g., `L2Handler`) for business logic orchestration
- **L2 Processor Layer**: Complex transformations and business rule applications (`ETLProcessor`)
- **Core Layer**: Shared utilities for Spark, Iceberg, and base connector functionality
- **Utils Layer**: AWS service integrations and enhanced logging

---

## L2 Processing Layer

The L2 layer extends the framework with advanced data processing capabilities, transforming raw L1 staging data into refined, business-ready datasets.

### Purpose
- **Business Logic Application**: Apply complex transformations and business rules
- **Data Enrichment**: Combine multiple L1 sources and add calculated fields
- **Data Quality**: Advanced validation, cleansing, and standardization
- **Refined Models**: Create analytics-ready data structures

### Workflow
1. **Input**: Reads from L1 Iceberg tables (staging layer)
2. **Processing**: Applies business transformations and data quality rules
3. **Output**: Writes refined data to L2 Iceberg tables (processing layer)
4. **Monitoring**: Enhanced logging and execution tracking

### Process Types
- `L1/staging`: Run only L1 data extraction
- `L2/processing`: Run only L2 data processing
- `both/None`: Run L1 followed by L2 in sequence

---

## Configuration

### Environment Variables
- `AWS_REGION`: AWS region for service clients
- `CUSTOMER_ENVIRONMENT`: Environment identifier for notifications (dev, prod, etc.)
- `CUSTOMER_NOTIFIER_LAMBDA`: Lambda function name for sending notifications
- `CUSTOMER_NOTIFICATION_TO`: Comma-separated list of email recipients

### Job Parameters

#### Core Parameters
- `SAAS_PLATFORM`: Platform identifier (wrike, cvent, eloqua, medallia)
- `CUSTOM_CONFIGS`: JSON string containing Spark warehouse configuration
- `PROCESS_TYPE`: Processing layer to execute (`L1/staging`, `L2/processing`, `both/None`)

#### L1 Parameters
- `CONFIG_TABLE`: DynamoDB table containing L1 connector configurations
- `LOG_GROUP`: CloudWatch log group name for L1 processes
- `CONFIG_ID`: (Optional) Specific configuration to process single object
- `LOAD_TYPE`: (Optional) Override for load type (FULL, INCREMENTAL)

#### L2 Parameters
- `L2_CONFIG_TABLE`: DynamoDB table containing L2 processing configurations
- `L2_HISTORY_TABLE`: DynamoDB table for L2 execution history tracking
- `L2_LOG_GROUP`: CloudWatch log group name for L2 processes

---

### DynamoDB Table Configuration

The SaaS Connector Framework uses **DynamoDB** tables to manage connector configurations.

Each configuration defines how data is fetched, transformed, and loaded for a specific SaaS object (e.g., Wrike Contacts, Wrike Projects).

#### 1. L1 Configuration Table

**Purpose:**  
Stores the configuration metadata for each SaaS object, including API source details, destination Iceberg configuration, authentication, and notification preferences.

**Key:**  
- **Primary Key:** `configId` (string) — Unique identifier for each configuration (e.g., `Wrike_Contacts`).

**Example Item Structure:**
```json
{
  "configId": "Wrike_Contacts",
  "platform": "wrike",
  "objectName": "contacts",
  "source": {
    "apiType": "REST",
    "auth": {
      "tokenKey": "essmdatalake-cc-wrike-apicredentials-sm-test",
      "tokenSource": "SECRETS_MANAGER",
      "tokenUrl": "https://www.wrike.com/oauth2/token",
      "type": "PERM"
    },
    "defaultFetchMode": "FULL",
    "request": {
      "method": "GET",
      "url": "https://www.wrike.com/api/v4/contacts",
      "headers": {
        "Accept": "application/json",
        "Authorization": "Bearer ${accessToken}"
      }
    },
    "response": {
      "dataPath": "$.data"
    }
  },
  "destination": {
    "glueDatabase": "wrike_test",
    "glueTable": "wrike_contacts",
    "s3Location": "s3://essmdatalake-customconnectors-test/wrike/test/iceberg-warehouse/contacts/",
    "primaryKey": ["id"],
    "loadType": "FULL",
    "defaultwriteMode": "APPEND",
    "lastUpdatedColumn": "fetchedOn",
    "lastSyncTime": "",
    "icebergOptimizations": {
   "schemaEvolution": true
  }
  },
  "history": {
    "dynamoTable": "essmdatalake-cc-wrike-ingestionhistory-table-test"
  },
  "notifications": {
    "onFailure": true,
    "onSuccess": false
  },
  "retryPolicy": {
    "backoff": "EXPONENTIAL",
    "maxAttempts": 3
  },
  "status": {
    "state": "running",
    "updatedAt": "timestamp"
  }
}
```

| Field                              | Type   | Description                                                 |
| ---------------------------------- | ------ | ----------------------------------------------------------- |
| `configId`                         | String | Unique identifier for the connector configuration           |
| `platform`                         | String | SaaS platform name (e.g., `wrike`, `cvent`, etc.)           |
| `objectName`                       | String | Target object being ingested (e.g., `contacts`, `projects`) |
| `source`                           | Object | Defines how to fetch data from the API                      |
| `source.auth`                      | Object | Authentication details for the API (token or OAuth)         |
| `source.request`                   | Object | HTTP request configuration (URL, headers, method)           |
| `source.response.dataPath`         | String | JSONPath to extract records from the API response           |
| `destination`                      | Object | Destination table and data lake settings                    |
| `destination.glueDatabase`         | String | AWS Glue database name                                      |
| `destination.glueTable`            | String | Iceberg table name                                          |
| `destination.s3Location`           | String | S3 path where Iceberg data is stored                        |
| `destination.primaryKey`           | Array  | List of columns that uniquely identify a record             |
| `destination.loadType`             | String | Load mode: `FULL` or `INCREMENTAL`                          |
| `destination.lastUpdatedColumn`    | String | Column name used for incremental fetches                    |
| `notifications`                    | Object | Defines notification behavior for success/failure           |
| `retryPolicy`                      | Object | Configurable retry policy for API calls                     |
| `history`                          | Object | DynamoDB table used for historical run tracking             |
| `destination.icebergOptimizations.schemaEvolution` | Array  | Dynamic handler of schema wheather to add extra cols or drop extra cols |

#### 2. L2 Configuration Table

**Purpose:**  
Stores configuration details for the L2 (Processing Layer), which reads data from the staging (L1) tables, performs transformations, and writes processed data to Iceberg destinations.

**Key:**  
- **Primary Key:** `configId` (string) — Unique identifier for each L2 configuration (e.g., `wrike_projects_l2`).

**Example Item Structure:**
```json
{
  "configId": { "S": "wrike_projects_l2" },
  "createdAt": { "S": "2025-11-13T00:00:00Z" },
  "destination": {
    "M": {
      "defaultwriteMode": { "S": "OVERWRITE" },
      "dropExtraColumns": { "BOOL": false },
      "glueDatabase": { "S": "wrike_test" },
      "glueTable": { "S": "projects" },
      "loadType": { "S": "FULL" },
      "primaryKey": { "L": [ { "S": "project_id" } ] },
      "s3Location": { "S": "s3://essmdatalake-customconnectors-test/wrike/test/iceberg-warehouse/l2/projects" }
    }
  },
  "lastSuccessfulRun": { "S": "2025-11-13T06:14:10.743884" },
  "loadType": { "S": "FULL" },
  "notifications": {
    "M": {
      "onFailure": { "BOOL": true },
      "onSuccess": { "BOOL": true }
    }
  },
  "parserName": { "S": "project_parser" },
  "source": {
    "M": {
      "contacts": {
        "M": {
          "fetchMode": { "S": "FULL" },
          "glueDatabase": { "S": "wrike_test" },
          "glueTable": { "S": "staging_contacts" },
          "incrementalColumn": { "S": "ingest_timestamp" },
          "lastSuccessfulFetchTime": { "S": "" }
        }
      },
      "customfields": {
        "M": {
          "fetchMode": { "S": "FULL" },
          "glueDatabase": { "S": "wrike_test" },
          "glueTable": { "S": "staging_customfields" },
          "incrementalColumn": { "S": "ingest_timestamp" },
          "lastSuccessfulFetchTime": { "S": "" }
        }
      },
      "folders": {
        "M": {
          "fetchMode": { "S": "FULL" },
          "glueDatabase": { "S": "wrike_test" },
          "glueTable": { "S": "staging_folders" },
          "incrementalColumn": { "S": "ingest_timestamp" },
          "lastSuccessfulFetchTime": { "S": "" }
        }
      },
      "projects": {
        "M": {
          "fetchMode": { "S": "FULL" },
          "glueDatabase": { "S": "wrike_test" },
          "glueTable": { "S": "staging_projectsdetails" },
          "incrementalColumn": { "S": "ingest_timestamp" },
          "lastSuccessfulFetchTime": { "S": "" }
        }
      }
    }
  },
  "status": { "S": "COMPLETED" },
  "updatedAt": { "S": "2025-11-13T06:14:10.743870Z" }
}
```

| Field                              | Type   | Description                                                 |
| ---------------------------------- | ------ | ----------------------------------------------------------- |
| `configId`                         | String | Unique identifier for each L2 configuration                |
| `parserName`                       | String | Name of the parser script responsible for transformation logic |
| `source`                           | Object | Defines the L1 tables (staging layer) from which data will be read |
| `destination`                      | Object | Defines the output Iceberg table and storage details       |
| `primaryKey`                       | Array  | Unique identifiers for deduplication in L2                 |
| `notifications`                    | Object | Notification settings for success/failure                   |
| `status`                           | String | Tracks the latest run status (e.g., COMPLETED, FAILED)     |

### Notes

- **Timestamps**: All timestamps now follow UTC format across both L1 and L2 layers
- **PROCESS_TYPE**: Determines which layer runs:
  - `L1` → Only staging layer runs
  - `L2` → Only processing layer runs  
  - `both` or not provided → Runs both sequentially


---

## Code Flow

### 1. Job Initialization (`main.py`)
```python
# Parameter validation and logger setup
required_args = ["CONFIG_TABLE", "SAAS_PLATFORM", "LOG_GROUP", "CUSTOM_CONFIGS"]
args = getResolvedOptions(sys.argv, required_args)

# Initialize CloudWatch logging with dynamic stream names
run_id = args.get("JOB_RUN_ID", "manual_run")
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_stream_name = f"{run_id}_{timestamp}"
logger = Logger("Main", LOG_LEVEL, args["LOG_GROUP"], log_stream_name)
cloudwatch = CloudWatchManager(AWS_REGION, args["LOG_GROUP"])
```

**Purpose**: Entry point for AWS Glue jobs with L1/L2 routing
- **Inputs**: Command-line arguments (PROCESS_TYPE, SAAS_PLATFORM, configuration tables, log groups, CUSTOM_CONFIGS, optional CONFIG_ID, optional LOAD_TYPE)
- **Outputs**: Instantiated platform handler(s) based on PROCESS_TYPE
- **Logic**: Validates parameters, parses custom configurations, sets up dynamic logging streams, routes to L1, L2, or both handlers based on PROCESS_TYPE

### 2. L1 Handler Orchestration (`connectors/wrike/handler.py`)
```python
class WrikeHandler:
    def run(self):
        self.load_configs()      # Load from DynamoDB
        self.process_configs()   # Process each configuration
```

**Purpose**: Orchestrates L1 data extraction for Wrike
- **Inputs**: Job arguments and L1 DynamoDB configurations
- **Outputs**: Raw data in L1 Iceberg tables
- **Logic**: 
  - Loads L1 configurations from DynamoDB
  - Creates Spark session with Iceberg settings
  - Processes each configuration independently
  - Updates sync timestamps and execution history

### 2b. L2 Handler Orchestration (`connectors/wrike/l2/l2_handler.py`)
```python
class L2WrikeHandler:
    def run(self):
        self.get_l2_configs()   # Load L2 configurations
        self.process_configs() # Process L2 transformations
```

**Purpose**: Orchestrates L2 data processing for Wrike
- **Inputs**: L2 configurations and L1 Iceberg table data
- **Outputs**: Refined data in L2 Iceberg tables
- **Logic**:
  - Loads L2 configurations from dedicated DynamoDB table
  - Reads from L1 staging tables
  - Applies business transformations
  - Writes to L2 processing tables with enhanced notifications

### 3. L1 Data Extraction (`connectors/wrike/connector.py`)
```python
class WrikeConnector(BaseConnector):
    def authenticate(self):     # Get API tokens from Secrets Manager
    def fetch_data(self):       # Call Wrike API with retry logic
    def transform_data(self):   # Convert to Spark DataFrame with ingest_date column
    def write_data(self):       # Write to L1 Iceberg table
```

**Purpose**: Handles Wrike-specific API interactions for L1
- **Inputs**: L1 configuration object, AWS utilities
- **Outputs**: Raw data in L1 Iceberg tables
- **Logic**:
  - Authenticates using Secrets Manager tokens
  - Fetches data with incremental/full load support
  - Handles rate limiting and retries
  - Validates API responses

### 3b. L2 Data Processing (`connectors/wrike/l2/etl_processor.py`)
```python
class ETLProcessor:
    def execute(self):                 # Executes full ETL flow (read → transform → validate → write)
    def read_source_data(self):        # Reads data from Iceberg source tables
    def apply_incremental_filtering(self):  # Filters data for incremental loads
    def transform_data(self):          # Transforms data using parser from ParserFactory
    def validate_primary_keys(self):   # Validates primary keys before merge
    def write_data(self):              # Writes transformed data to destination Iceberg table
```

**Purpose**: Handles Wrike-specific L2 ETL processing
- **Inputs**: L2 configuration object, Source Iceberg tables
- **Outputs**: Transformed and validated data written to destination Iceberg tables
- **Logic**:
  - Reads data from one or more source Iceberg tables using IcebergReader
  - Applies incremental filtering based on lastSuccessfulRun if load type is INCREMENTAL
  - Transforms data using dynamically loaded parser from ParserFactory
  - Adds L2-specific metadata columns (e.g., ingest_timestamp)
  - Validates primary keys for merge operations during incremental loads
  - Writes processed data to destination Iceberg table using IcebergWriter
  - Includes detailed logging and exception handling for fetch, transform, and write stages

### 4. Data Loading (`core/iceberg_writer.py`)
```python
class IcebergWriter:
    def merge(self, df, id_col):        # Upsert records
    def overwrite_table(self, df):      # Full table replacement
    def insert(self, df):               # Append new records
```

**Purpose**: Manages Iceberg table operations
- **Inputs**: Spark DataFrame, destination configuration
- **Outputs**: Snapshot ID of written data
- **Logic**:
  - Handles schema evolution automatically
  - Supports merge, append, and overwrite operations
  - Optimizes data with deduplication and partitioning

### 5. Data Reading (`core/iceberg_reader.py`)
```python
class IcebergReader:
    def read_table(self, database, table):     # Reads full Iceberg table
    def read_incremental(self, database, table, timestamp):  # Reads incremental data
    def get_table_schema(self, database, table):  # Gets table schema information
```

**Purpose**: Manages Iceberg table read operations for L2 processing
- **Inputs**: Database name, table name, optional timestamp for incremental reads
- **Outputs**: Spark DataFrame with requested data
- **Logic**:
  - Reads data from Iceberg tables using Spark SQL
  - Supports full and incremental data retrieval
  - Handles schema validation and type conversion
  - Optimizes read performance with predicate pushdown

---

## Module Details

### `/config/constants.py`
**Purpose**: Global configuration constants
- `AWS_REGION`: Default AWS region
- `LOG_LEVEL`: Application logging level

### `/connectors/wrike/`

#### `connector.py` - WrikeConnector Class
**Functions**:
- `authenticate()`: Retrieves API tokens from AWS Secrets Manager with OAuth2 support
- `fetch_data(incremental, last_updated)`: Enhanced API calls with configurable parameters and rate limiting
- `transform_data(data)`: Converts JSON to Spark DataFrame with JSONPath extraction and validation
- `write_data(data, load_type)`: Writes to Iceberg with enhanced configuration and optimization

#### `handler.py` - WrikeHandler Class  
**Functions**:
- `load_configs()`: Loads configurations from DynamoDB with support for specific config ID
- `create_spark()`: Initializes Spark session with custom configurations and Iceberg extensions
- `process_configs()`: Enhanced configuration processing with notification support
- `run()`: Main orchestration method with comprehensive error handling

### `/connectors/wrike/l2/`

#### `l2_handler.py` - L2WrikeHandler Class
**Functions**:
- `get_l2_configs()`: Loads L2 configurations from DynamoDB
- `create_spark()`: Initializes Spark session for L2 processing
- `process_configs()`: Orchestrates L2 data processing pipeline
- `run()`: Main L2 orchestration method

#### `etl_processor.py` - ETLProcessor Class
**Functions**:
- `execute()`: Main ETL execution method coordinating read, transform, validate, write operations
- `read_source_data()`: Reads data from L1 staging tables using IcebergReader
- `apply_incremental_filtering()`: Applies time-based filtering for incremental loads
- `transform_data()`: Transforms data using dynamically loaded parsers
- `validate_primary_keys()`: Validates primary keys before merge operations
- `write_data()`: Writes processed data to L2 Iceberg tables

### `/connectors/wrike/l2/parsers/`

#### `parsers.py` - ParserFactory Class
**Functions**:
- `get_parser(parser_name)`: Dynamically loads and returns parser instance based on name
- `list_available_parsers()`: Returns list of available parser modules
- `validate_parser(parser_class)`: Validates parser implements required interface

#### `project_parser.py` - ProjectParser Class
**Functions**:
- `parse(data)`: Transforms project data with business logic
- `validate_schema(df)`: Validates transformed data schema
- `add_calculated_fields(df)`: Adds derived columns and calculations

#### `object_parser1.py`, `object_parser2.py` - Custom Object Parsers
**Functions**:
- `parse(data)`: Object-specific transformation logic
- `validate_schema(df)`: Schema validation for specific objects
- `enrich_data(df)`: Object-specific data enrichment

### `/core/`

#### `base_connector.py` - BaseConnector Abstract Class
**Functions**:
- `authenticate()`: Abstract method for API authentication
- `fetch_data()`: Abstract method for data retrieval
- `transform_data()`: Abstract method for data transformation
- `write_data()`: Abstract method for data writing

#### `iceberg_writer.py` - IcebergWriter Class
**Functions**:
- `merge(df, id_col)`: Performs MERGE operations for incremental loads with conflict resolution
- `overwrite_table(df)`: Full table replacement for complete refreshes
- `insert(df)`: Appends new records without deduplication
- `write(df, load_type)`: Main write method with preprocessing and optimization

#### `iceberg_reader.py` - IcebergReader Class
**Functions**:
- `read_table(database, table)`: Reads complete Iceberg table data
- `read_incremental(database, table, timestamp)`: Reads data modified after specified timestamp
- `get_table_schema(database, table)`: Retrieves table schema metadata
- `validate_table_exists(database, table)`: Checks if table exists before read operations

#### `spark_session.py` - SparkSessionManager Class
**Functions**:
- `create_session(configs)`: Creates Spark session with Iceberg configurations
- `get_session()`: Gets existing session or creates new one
- `stop()`: Properly terminates Spark session

### `/utils/`

#### `logger.py` - Logger Class
**Functions**:
- `info/warning/error/debug(message)`: Logs to both console and CloudWatch
- `_setup_cloudwatch()`: Configures CloudWatch log groups and streams

#### `config.py` - ConfigLoader Class
**Functions**:
- `get_all_configs()`: Retrieves and validates all configurations from DynamoDB
- `get_config(config_id)`: Loads specific configuration with validation
- `update_last_fetch_time(config_id, timestamp)`: Updates sync timestamps

#### `notifications.py` - NotificationManager Class
**Functions**:
- `send_notification(platform_name)`: Sends HTML email notifications via Lambda
- `store_successful_config(config_id, record_count, snapshot_id)`: Tracks successful executions
- `store_failure_config(config_id, error_message)`: Tracks failed executions

---

## AWS Services Integration

### CloudWatch
**Role**: Centralized logging and monitoring
- **Log Groups**: Organized by job type and environment
- **Log Streams**: Separate streams for different components
- **Metrics**: Custom metrics for job success/failure rates

### DynamoDB
**Role**: Configuration management and execution tracking

#### History Table Structure for Both L1 and L2:
```json
{
  "configId": "wrike-projects-prod",
  "job-id": "",
  "load_type": "FULL",
  "loadTimestamp": "2024-01-15T10:30:00Z",
  "snapshot_id": "",
  "error": "Error message if lastRunStatus is Failed",
  "lastRunStatus": "SUCCESS",
  "totalRecordsProcessed": 1250
}
```

### Secrets Manager
**Role**: Secure credential storage
- **API Tokens**: Encrypted storage of SaaS platform credentials
- **OAuth Credentials**: Client IDs, secrets, and refresh tokens
- **Rotation Support**: Automatic credential rotation capabilities

### Iceberg Writer
**Role**: Data lake table management
- **Schema Evolution**: Handling of new columns via config
- **ACID Transactions**: Consistent data writes with rollback capability
- **Time Travel**: Snapshot-based versioning for data recovery


### Framework Benefits for New Connectors

1. **Inherited Functionality**: Automatic retry logic, error handling, and monitoring
2. **Consistent Data Loading**: Standardized Iceberg operations with schema evolution
3. **Configuration Management**: DynamoDB-based configuration with validation
4. **AWS Integration**: Built-in CloudWatch logging and Secrets Manager support
5. **Scalability**: Spark-based processing for large datasets

### AWS Permissions Required
- **DynamoDB**: Read/write access to configuration and history tables
- **Secrets Manager**: Read access to API credentials
- **CloudWatch Logs**: Create log groups/streams and write log events
- **S3**: Read/write access to Iceberg warehouse location
- **Glue Catalog**: Create/update table metadata

This framework provides a robust foundation for SaaS data integration with built-in best practices for error handling, monitoring, and scalability.

---
