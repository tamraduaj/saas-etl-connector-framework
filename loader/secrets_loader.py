import json
import sys

import boto3
from botocore.exceptions import ClientError


def update_or_create_secret(
    secret_name: str,
    secret_dict: dict,
    profile: str,
    region_name: str = "us-east-1",
):
    """
    Creates or updates a secret in AWS Secrets Manager with the given dictionary.

    :param secret_name: Name of the AWS secret
    :param secret_dict: Dictionary to store as secret
    :param profile: AWS CLI profile name to use
    :param region_name: AWS region (default: us-east-1)
    """
    session = boto3.Session(profile_name=profile, region_name=region_name)
    client = session.client("secretsmanager")

    secret_string = json.dumps(secret_dict)

    try:
        # Try to update the secret if it exists
        response = client.update_secret(
            SecretId=secret_name,
            SecretString=secret_string,
        )
        print(f"✅ Secret '{secret_name}' updated.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            # Secret doesn't exist, create it
            response = {}
            try:
                response = client.create_secret(
                    Name=secret_name, SecretString=secret_string
                )
                print(f"✅ Secret '{secret_name}' created.")
            except ClientError as create_error:
                print(f"response: {response}")
                print(f"❌ Failed to create secret: {create_error}")
        else:
            print(f"❌ Failed to update secret: {e}")


# Example usage
if __name__ == "__main__":

    if len(sys.argv) < 3:
        print(
            "Usage: python secrets_loader.py <platform name> <environment> [profile] [region]"
        )
        sys.exit(1)

    platform_name = sys.argv[1]
    environment = sys.argv[2]
    profile_name = sys.argv[3] if len(sys.argv) > 3 else "default"
    region = sys.argv[4] if len(sys.argv) > 4 else "us-east-1"

    secret_name = f"essmdatalake-cc-{platform_name}-apicredentials-sm-{environment}"

    with open("secret.json", "r") as file:
        my_secret = json.load(file)

    update_or_create_secret(
        secret_name=secret_name,
        secret_dict=my_secret,
        profile=profile_name,
        region_name=region,
    )
