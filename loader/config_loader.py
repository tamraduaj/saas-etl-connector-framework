import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

USAGE_MESSAGE = """Usage: python config_loader.py <platform_name> <environment> [aws_profile_name] [partition_key] [folders] ...
            

Example:
python config_loader.py "wrike" "dev" "default" "configId" "rest"


folders should contain files like the following
<config name>.json

Example eloqua case:

rest/
    contacts.json
    bouncebacks.json
    emailclickthrough.json

Usage End
"""


def upsert_to_dynamodb(
    profile_name, table_name, partition_key, json_file, vars_files, environment
):
    # Create session with given profile
    session = boto3.Session(profile_name=profile_name)
    dynamodb = session.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(table_name)

    # Load Vars file
    vars_data = {}

    for file in vars_files:
        with open(file, "r") as f:
            vars_data.update(json.load(f))

    vars = vars_data.get("vars", {}).get(environment, {})

    # Load JSON file
    with open(json_file, "r") as f:
        data = f.read()

    for key, value in vars.items():
        if f"${{{key}}}" in data:
            data = data.replace(f"${{{key}}}", value)

    data = json.loads(data)

    # Ensure list of records
    if not isinstance(data, list):
        data = [data]

    for item in data:

        key_value = item.get(partition_key)

        if key_value is None:
            print(f"Skipping item without partition key '{partition_key}': {item}")
            continue

        try:
            # Check if item exists
            response = table.get_item(Key={partition_key: key_value})
            exists = "Item" in response

            if exists:
                print(f"Updating existing item: {key_value}")
                table.put_item(Item=item)  # Overwrites
            else:
                print(f"Inserting new item: {key_value}")
                table.put_item(Item=item)

        except ClientError as e:
            print(
                f"Error processing item {key_value}: {e.response['Error']['Message']}"
            )


if __name__ == "__main__":

    # print usage
    if len(sys.argv) < 3:
        print(USAGE_MESSAGE)
        sys.exit(1)

    # variables definition using args
    platform_name = sys.argv[1]
    environment = sys.argv[2]
    aws_profile_name = sys.argv[3] if len(sys.argv) >= 4 else "default"
    partition_key = sys.argv[4] if len(sys.argv) >= 5 else "configId"
    folders_to_load = sys.argv[5:] if len(sys.argv) >= 6 else ["rest"]

    table_name = f"essmdatalake-cc-{platform_name}-config-table-{environment}"
    CONFIG_FOLDER = "config"

    for folder in folders_to_load:
        for file in os.listdir(os.path.join(CONFIG_FOLDER, folder)):
            if not file.endswith(".json") and file.endswith(".vars.json"):
                continue

            json_file = os.path.join(CONFIG_FOLDER, folder, file)
            file_name_without_extension = os.path.splitext(file)[0]
            vars_files = [
                os.path.join(CONFIG_FOLDER, "vars", "default.vars.json"),
                os.path.join(
                    CONFIG_FOLDER, "vars", f"{file_name_without_extension}.vars.json"
                ),
            ]

            vars_files = [f for f in vars_files if os.path.exists(f)]

            upsert_to_dynamodb(
                table_name=table_name,
                partition_key=partition_key,
                json_file=json_file,
                vars_files=vars_files,
                profile_name=aws_profile_name,
                environment=environment,
            )
