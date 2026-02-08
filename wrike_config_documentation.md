# Wrike Connector Configuration Documentation

## Overview

This document provides comprehensive documentation for the Wrike connector configuration file used in the SaaS Connector Framework. The configuration defines how data is extracted from Wrike's API and loaded into AWS Iceberg tables.

The configuration follows a JSON structure stored in DynamoDB and controls every aspect of the ETL pipeline including authentication, data extraction, transformation rules, destination settings, error handling, and monitoring.

## Configuration Structure

### Root Level Configuration

#### `configId`
- **Description**: Unique identifier for this connector configuration
- **Purpose**: Primary key for DynamoDB storage and pipeline identification
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: Alphanumeric with underscores (e.g., "Wrike_Contacts", "Wrike_Projects")
- **Source**: User-provided during configuration setup
- **Impact**: Changing this creates a new configuration; used in logging, history tracking, and notifications
- **Constraints**: Must be unique across all configurations in the same environment
- **Use Case**: 
  - **Input**: "Wrike_Contacts" 
  - **Output**: Used as primary key in DynamoDB, appears in CloudWatch logs as `[Wrike_Contacts]`, referenced in execution history

#### `platform`
- **Description**: Identifies the SaaS platform being connected
- **Purpose**: Routes to platform-specific handler and connector logic
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "wrike", "cvent", "eloqua", "medallia"
- **Source**: User-provided during configuration
- **Impact**: Determines which platform handler is instantiated (WrikeHandler, CventHandler)
- **Constraints**: Must match available platform implementations
- **Use Case**:
  - **Input**: "wrike"
  - **Output**: Framework loads WrikeHandler and WrikeConnector classes

#### `objectName`
- **Description**: Specific object/entity being extracted from the platform
- **Purpose**: Identifies the data type for logging, validation, and destination naming
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: Platform-specific objects (e.g., "contacts", "projects", "tasks", "folders")
- **Source**: User-provided based on available API endpoints
- **Impact**: Used in table naming, logging context, and validation rules
- **Constraints**: Must correspond to valid API endpoints for the platform
- **Use Case**:
  - **Input**: "contacts"
  - **Output**: Appears in logs as processing "contacts", validates against Wrike contacts schema

---

## Source Configuration (`source`)

### `apiType`
- **Description**: API protocol type (duplicated from root level for source-specific context)
- **Purpose**: Confirms API type at source level for validation
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "REST"
- **Source**: User-provided, should match root-level apiType
- **Impact**: Validation check to ensure consistency
- **Constraints**: Must match root-level apiType
- **Use Case**:
  - **Input**: "REST"
  - **Output**: Validates consistency with root apiType, enables REST-specific processing

### `defaultFetchMode`
- **Description**: Default data retrieval strategy for this configuration
- **Purpose**: Determines initial load behavior when no specific mode is provided
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "FULL", "INCREMENTAL"
- **Source**: User-provided based on data requirements
- **Impact**: Controls whether to fetch all data or only changes since last run
- **Constraints**: INCREMENTAL requires lastUpdatedColumn to be configured
- **Use Case**:
  - **Input**: "FULL"
  - **Output**: Initial run fetches all contacts; subsequent runs can override with INCREMENTAL

### Authentication (`auth`)

#### `type`
- **Description**: Authentication mechanism type
- **Purpose**: Specifies how to authenticate with the API
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "PERM" (Permanent Token), "OAUTH", "API_KEY", "BASIC"
- **Source**: User-provided based on API requirements
- **Impact**: Determines authentication flow and token handling
- **Constraints**: Must match API's supported authentication methods
- **Use Case**:
  - **Input**: "PERM"
  - **Output**: Uses permanent token from Secrets Manager, skips OAuth flow

#### `tokenSource`
- **Description**: Location where authentication credentials are stored
- **Purpose**: Specifies where to retrieve authentication tokens
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "SECRETS_MANAGER"
- **Source**: User-provided based on security requirements
- **Impact**: Determines which AWS service to query for credentials
- **Constraints**: Requires appropriate IAM permissions for the specified service
- **Use Case**:
  - **Input**: "SECRETS_MANAGER"
  - **Output**: Framework calls `secrets_manager.get_secret_value()` using tokenKey

#### `tokenKey`
- **Description**: Identifier for the stored authentication credentials
- **Purpose**: Key/name used to retrieve credentials from the token source
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: Secret name with environment variables (e.g., "essmdatalake-cc-wrike-apicredentials-sm-${environment_custom_var}")
- **Source**: User-provided, references existing secret
- **Impact**: Must exist in Secrets Manager or retrieval will fail
- **Constraints**: Secret must contain valid API credentials in expected format
- **Use Case**:
  - **Input**: "essmdatalake-cc-wrike-apicredentials-sm-dev"
  - **Output**: Retrieves `{"access_token": "abc123", "refresh_token": "xyz789"}` from Secrets Manager

#### `tokenUrl`
- **Description**: OAuth token endpoint URL for token refresh/validation
- **Purpose**: Endpoint for OAuth token operations (refresh, validate)
- **Mandatory**: No (required for OAuth flows)
- **Data Type**: String (URL)
- **Expected Values**: Valid HTTPS URL (e.g., "https://www.wrike.com/oauth2/token")
- **Source**: User-provided from API documentation
- **Impact**: Used for token refresh when access tokens expire
- **Constraints**: Must be accessible from AWS Glue environment
- **Use Case**:
  - **Input**: "https://www.wrike.com/oauth2/token"
  - **Output**: Framework calls this URL with refresh_token to get new access_token

### Request Configuration (`request`)

#### `method`
- **Description**: HTTP method for API requests
- **Purpose**: Specifies the HTTP verb for API calls
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "GET", "POST", "PUT", "PATCH"
- **Source**: User-provided from API documentation
- **Impact**: Determines how the HTTP request is constructed
- **Constraints**: Must match API endpoint requirements
- **Use Case**:
  - **Input**: "GET"
  - **Output**: Framework constructs `requests.get()` call

#### `url`
- **Description**: API endpoint URL for data retrieval
- **Purpose**: Target endpoint for fetching the specified object data
- **Mandatory**: Yes
- **Data Type**: String (URL)
- **Expected Values**: Valid HTTPS API URL (e.g., "https://www.wrike.com/api/v4/contacts")
- **Source**: User-provided from API documentation
- **Impact**: Primary endpoint for data extraction
- **Constraints**: Must be accessible and return expected data format
- **Use Case**:
  - **Input**: "https://www.wrike.com/api/v4/contacts"
  - **Output**: Framework makes HTTP request to this URL to fetch contacts data

#### `headers`
- **Description**: HTTP headers to include in API requests
- **Purpose**: Provides authentication, content type, and other request metadata
- **Mandatory**: Yes
- **Data Type**: Object (key-value pairs)
- **Expected Values**: Valid HTTP headers with variable substitution
- **Source**: User-provided from API requirements
- **Impact**: Headers are included in every API request
- **Constraints**: Authorization header must use valid token format
- **Use Case**:
  - **Input**: `{"Accept": "application/json", "Authorization": "Bearer ${accessToken}"}`
  - **Output**: Framework substitutes `${accessToken}` with actual token and sends headers

### Response Configuration (`response`)

#### `dataPath`
- **Description**: JSONPath expression to extract data records from API response
- **Purpose**: Locates the array of records within the API response structure
- **Mandatory**: Yes
- **Data Type**: String (JSONPath expression)
- **Expected Values**: Valid JSONPath (e.g., "$.data", "$.results", "$.items")
- **Source**: User-provided based on API response structure
- **Impact**: Determines which part of the response contains the actual data records
- **Constraints**: Must point to an array or object containing records
- **Use Case**:
  - **Input**: "$.data"
  - **Output**: From response `{"data": [{"id": 1, "name": "John"}], "meta": {...}}`, extracts `[{"id": 1, "name": "John"}]`

---

## Destination Configuration (`destination`)

### `glueDatabase`
- **Description**: AWS Glue catalog database name for the destination table
- **Purpose**: Organizes tables within the Glue catalog for the target environment
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: Valid database name with environment variables (e.g., "wrike_${environment_custom_var}")
- **Source**: User-provided, follows naming conventions
- **Impact**: Database must exist in Glue catalog or be created automatically
- **Constraints**: Must follow AWS Glue naming conventions (lowercase, underscores)
- **Use Case**:
  - **Input**: "wrike_dev"
  - **Output**: Table created as `wrike_dev.wrike_contacts` in Glue catalog

### `glueTable`
- **Description**: AWS Glue catalog table name for the destination
- **Purpose**: Specific table name within the database for storing extracted data
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: Valid table name (e.g., "wrike_contacts", "wrike_projects")
- **Source**: User-provided following naming conventions
- **Impact**: Table is created/updated in Glue catalog with this name
- **Constraints**: Must follow AWS Glue naming conventions
- **Use Case**:
  - **Input**: "wrike_contacts"
  - **Output**: Creates Iceberg table accessible as `SELECT * FROM wrike_dev.wrike_contacts`

### `s3Location`
- **Description**: S3 path where Iceberg table data files are stored
- **Purpose**: Physical storage location for the table's data and metadata
- **Mandatory**: Yes
- **Data Type**: String (S3 URI)
- **Expected Values**: Valid S3 URI with environment variables
- **Source**: User-provided following S3 bucket structure
- **Impact**: All table data and metadata files are stored at this location
- **Constraints**: S3 bucket must exist and be accessible with proper permissions
- **Use Case**:
  - **Input**: "s3://data-lake-dev/wrike/dev/iceberg-warehouse/contacts/"
  - **Output**: Iceberg files stored at this path, accessible via Glue catalog

### `primaryKey`
- **Description**: Column(s) that uniquely identify each record
- **Purpose**: Used for deduplication and merge operations during data loading
- **Mandatory**: Yes
- **Data Type**: Array of strings
- **Expected Values**: Column names that exist in the source data
- **Source**: User-provided based on data structure analysis
- **Impact**: Enables UPSERT operations and prevents duplicate records
- **Constraints**: Specified columns must exist in source data and be unique
- **Use Case**:
  - **Input**: ["id"]
  - **Output**: During merge, records with same "id" are updated rather than duplicated

### `loadType`
- **Description**: Data loading strategy for this configuration
- **Purpose**: Determines whether to perform full refresh or incremental updates
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "FULL", "INCREMENTAL"
- **Source**: User-provided based on data requirements and API capabilities
- **Impact**: Controls data loading behavior and performance
- **Constraints**: INCREMENTAL requires lastUpdatedColumn configuration
- **Use Case**:
  - **Input**: "FULL"
  - **Output**: Every run replaces entire table contents with fresh API data

### `defaultwriteMode`
- **Description**: Iceberg write operation mode
- **Purpose**: Specifies how data is written to the Iceberg table
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "APPEND", "OVERWRITE", "MERGE"
- **Source**: User-provided based on data requirements
- **Impact**: Determines Iceberg write behavior and performance characteristics
- **Constraints**: MERGE requires primaryKey configuration
- **Use Case**:
  - **Input**: "MERGE"
  - **Output**: New data is Merged to existing table without deduplication

### `lastUpdatedColumn`
- **Description**: Column name containing record modification timestamp
- **Purpose**: Enables incremental loading by identifying recently changed records
- **Mandatory**: No (required for INCREMENTAL loads only)
- **Data Type**: String
- **Expected Values**: Column name from source data containing timestamps
- **Source**: User-provided based on API response structure
- **Impact**: Used to filter records for incremental loads
- **Constraints**: Column must contain valid timestamp data
- **Use Case**:
  - **Input**: "fetchedOn"
  - **Output**: Incremental loads fetch only records where `fetchedOn > lastSyncTime`

### `lastSyncTime`
- **Description**: Timestamp of the last successful data synchronization
- **Purpose**: Watermark for incremental loading to avoid reprocessing data
- **Mandatory**: No
- **Data Type**: String (ISO date format)
- **Expected Values**: ISO 8601 date string (e.g., "2025-10-14", "2025-10-14T10:30:00Z")
- **Source**: System-generated and updated after successful runs
- **Impact**: Starting point for next incremental load
- **Constraints**: Must be valid date format, updated automatically by framework
- **Use Case**:
  - **Input**: "2025-10-14"
  - **Output**: Next incremental run fetches records modified after this date

### Iceberg Optimizations (`icebergOptimizations`)

#### `schemaEvolution`
- **Description**: Enables automatic schema evolution for the Iceberg table
- **Purpose**: Allows table schema to adapt when API response structure changes
- **Mandatory**: No
- **Data Type**: Boolean
- **Expected Values**: true, false
- **Source**: User-provided based on schema stability requirements
- **Impact**: New columns are automatically added; missing columns can be handled gracefully
- **Constraints**: Schema changes must be compatible (additive changes work best)
- **Use Case**:
  - **Input**: true
  - **Output**: When API adds "phoneNumber" field, table schema automatically includes new column

#### `compaction`
- **Description**: Enables automatic file compaction for the Iceberg table
- **Purpose**: Optimizes query performance by consolidating small files
- **Mandatory**: No
- **Data Type**: Boolean
- **Expected Values**: true, false
- **Source**: User-provided based on performance requirements
- **Impact**: Reduces number of files, improves query performance, increases write time
- **Constraints**: May increase processing time for write operations
- **Use Case**:
  - **Input**: true
  - **Output**: After data load, small files are merged into larger, optimized files

#### `vacuumRetentionDays`
- **Description**: Number of days to retain old Iceberg snapshots before cleanup
- **Purpose**: Manages storage costs while maintaining time-travel capabilities
- **Mandatory**: No
- **Data Type**: Integer
- **Expected Values**: Positive integers (typically 1-30 days)
- **Source**: User-provided based on recovery and compliance requirements
- **Impact**: Balances storage costs with data recovery capabilities
- **Constraints**: Must be positive integer; shorter retention reduces storage costs
- **Use Case**:
  - **Input**: 2
  - **Output**: Snapshots older than 2 days are automatically deleted during vacuum operations

---

## History Configuration (`history`)

### `configId`
- **Description**: Configuration identifier for history tracking (duplicate of root configId)
- **Purpose**: Links history records to their corresponding configuration
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: Must match root-level configId
- **Source**: User-provided, should match root configId
- **Impact**: Used as partition key in history table
- **Constraints**: Must match root configId exactly
- **Use Case**:
  - **Input**: "Wrike_Contacts"
  - **Output**: History records stored with this configId for tracking and reporting

### `dynamoTable`
- **Description**: DynamoDB table name for storing execution history
- **Purpose**: Tracks job execution results, timing, and error information
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: Valid DynamoDB table name with environment variables
- **Source**: User-provided following naming conventions
- **Impact**: All execution history is stored in this table
- **Constraints**: Table must exist and be accessible with proper permissions
- **Use Case**:
  - **Input**: "essmdatalake-cc-wrike-ingestionhistory-table-dev"
  - **Output**: Execution records stored as `{configId: "Wrike_Contacts", timestamp: "...", status: "SUCCESS"}`

---

## Notification Configuration (`notifications`)

### `onFailure`
- **Description**: Enable notifications when job execution fails
- **Purpose**: Alerts stakeholders about pipeline failures for immediate attention
- **Mandatory**: Yes
- **Data Type**: Boolean
- **Expected Values**: true, false
- **Source**: User-provided based on monitoring requirements
- **Impact**: Failure notifications are sent when enabled
- **Constraints**: Requires notification infrastructure (Lambda function) to be configured
- **Use Case**:
  - **Input**: true
  - **Output**: Email sent to configured recipients when API call fails or data validation errors occur

### `onSuccess`
- **Description**: Enable notifications when job execution succeeds
- **Purpose**: Confirms successful data processing for monitoring and compliance
- **Mandatory**: Yes
- **Data Type**: Boolean
- **Expected Values**: true, false
- **Source**: User-provided based on monitoring requirements
- **Impact**: Success notifications are sent when enabled
- **Constraints**: May generate high volume of notifications for frequent jobs
- **Use Case**:
  - **Input**: false
  - **Output**: No notification sent after successful contact data extraction and loading

---

## Retry Policy Configuration (`retryPolicy`)

### `maxAttempts`
- **Description**: Maximum number of retry attempts for failed operations
- **Purpose**: Provides resilience against transient failures while preventing infinite loops
- **Mandatory**: Yes
- **Data Type**: Integer
- **Expected Values**: Positive integers (typically 1-5)
- **Source**: User-provided based on API reliability and time constraints
- **Impact**: Failed operations are retried up to this limit before final failure
- **Constraints**: Higher values increase job duration for persistent failures
- **Use Case**:
  - **Input**: 3
  - **Output**: API call fails → wait → retry → fail → wait → retry → fail → wait → retry → final failure

### `backoff`
- **Description**: Retry delay strategy for failed operations
- **Purpose**: Determines how long to wait between retry attempts
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "EXPONENTIAL", "LINEAR", "FIXED"
- **Source**: User-provided based on API rate limiting and failure patterns
- **Impact**: Controls timing between retry attempts
- **Constraints**: EXPONENTIAL is recommended for rate-limited APIs
- **Use Case**:
  - **Input**: "EXPONENTIAL"
  - **Output**: Retry delays: 1s → 2s → 4s → 8s (doubles each time)

---

## Status Configuration (`status`)

### `state`
- **Description**: Current operational state of the configuration
- **Purpose**: Indicates whether the configuration is active and available for processing
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "running", "paused", "disabled", "error"
- **Source**: User-provided or system-updated based on operational needs
- **Impact**: Only "running" configurations are processed during job execution
- **Constraints**: Non-running states skip processing entirely
- **Use Case**:
  - **Input**: "running"
  - **Output**: Configuration is included in job execution cycle

### `updatedAt`
- **Description**: Timestamp of last configuration modification
- **Purpose**: Tracks when configuration was last changed for audit and troubleshooting
- **Mandatory**: Yes
- **Data Type**: String
- **Expected Values**: "timestamp" (placeholder) or ISO 8601 timestamp
- **Source**: System-generated when configuration is modified
- **Impact**: Used for audit trails and change tracking
- **Constraints**: Automatically updated by configuration management system
- **Use Case**:
  - **Input**: "timestamp"
  - **Output**: Replaced with actual timestamp like "2025-01-15T10:30:00Z" when configuration is saved

---

## Runtime Configuration (`lastFetchTime`)

### `lastFetchTime`
- **Description**: Timestamp of the most recent successful data fetch
- **Purpose**: Runtime tracking of execution progress, separate from configuration sync time
- **Mandatory**: No
- **Data Type**: String
- **Expected Values**: Empty string or ISO 8601 timestamp
- **Source**: System-generated and updated after successful API calls
- **Impact**: Used for monitoring and debugging execution timing
- **Constraints**: Updated automatically by framework during execution
- **Use Case**:
  - **Input**: ""
  - **Output**: Updated to "2025-01-15T14:22:33Z" after successful API call completion

---

## Environment Variables and Substitution

The configuration supports environment variable substitution using the `${variable_name}` syntax:

- `${environment_custom_var}`: Replaced with environment identifier (dev, test, prod)
- `${bucket_name_custom_var}`: Replaced with environment-specific S3 bucket name
- `${accessToken}`: Replaced with actual API access token during runtime

## Configuration Validation Rules

1. **Required Fields**: All mandatory fields must be present and non-empty
2. **Data Types**: All fields must match expected data types
3. **URL Validation**: All URLs must be valid and accessible
4. **Dependency Checks**: 
   - INCREMENTAL loadType requires lastUpdatedColumn
   - MERGE writeMode requires primaryKey
5. **AWS Resource Validation**: Referenced AWS resources (S3 buckets, DynamoDB tables, Secrets) must exist
6. **Environment Consistency**: Environment variables must resolve to valid values

## Notes and Remarks

- **Security**: All sensitive credentials are stored in AWS Secrets Manager, never in configuration
- **Scalability**: Configuration supports both small-scale and enterprise-level data volumes
- **Monitoring**: Comprehensive logging and notification system ensures operational visibility
- **Flexibility**: Modular design allows easy customization for different data sources and requirements
- **Reliability**: Built-in retry mechanisms and error handling provide robust operation
- **Performance**: Iceberg optimizations ensure efficient storage and query performance
- **Compliance**: Audit trails and history tracking support compliance requirements

This configuration provides a complete, production-ready setup for extracting Wrike contacts data with enterprise-grade reliability, monitoring, and performance optimization.