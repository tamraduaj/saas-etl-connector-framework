import os
import sys
import zipfile

import boto3
from botocore.exceptions import ClientError

USAGE_MESSAGE = """Usage: python s3_loader.py <platform_name> <environment> <bucket_name> [aws_profile_name] [source_folder] [region]
Example:
    python s3_loader.py "wrike" "dev" "test-bucket" "cdo-edi-np" "../src" "us-east-1"

platform_name: name of the platform
environment: environment name
bucket_name: S3 bucket to use
[aws_profile_name]: if aws profile not provided, default profile will be used
[source_folder]: the source folder to zip, if not provided relative path will be used to src
[region]: aws region, if not provided us-east-1 will be the default
"""


def zip_folder(source_folder, output_zip_path):
    """Zips all files inside a folder."""
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_folder):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, start=source_folder)
                zipf.write(abs_path, rel_path)
    print(f"[INFO] Folder zipped to: {output_zip_path}")


def upload_file_to_s3(profile_name, region, file_path, bucket_name, s3_key):
    """Uploads a single file to S3."""
    session = boto3.Session(profile_name=profile_name, region_name=region)
    s3 = session.client("s3")

    try:
        print(f"[INFO] Uploading {file_path} → s3://{bucket_name}/{s3_key}")
        s3.upload_file(file_path, bucket_name, s3_key)
        print(f"[SUCCESS] Uploaded to s3://{bucket_name}/{s3_key}")
    except ClientError as e:
        print(f"[ERROR] Failed to upload {file_path}: {e.response['Error']['Message']}")


if __name__ == "__main__":

    # Usage validation
    if len(sys.argv) < 4:
        print(USAGE_MESSAGE)
        sys.exit(1)

    # variables definition from args
    platform_name = sys.argv[1]
    environment = sys.argv[2]
    bucket_name = sys.argv[3]
    aws_profile_name = sys.argv[4] if len(sys.argv) > 4 else "default"
    source_folder = sys.argv[5] if len(sys.argv) > 5 else "../src"
    region = sys.argv[6] if len(sys.argv) > 6 else "us-east-1"

    # Define paths
    zip_name = f"{platform_name}_code.zip"
    zip_output_path = os.path.join(os.path.curdir, zip_name)
    s3_code_key = f"{platform_name}/{environment}/scripts/{zip_name}"
    s3_script_prefix = f"{platform_name}/{environment}/scripts"

    # Step 1: Zip source folder
    zip_folder(source_folder, zip_output_path)

    # Step 2: Upload zipped code to S3
    upload_file_to_s3(
        bucket_name=bucket_name,
        s3_key=s3_code_key,
        file_path=zip_output_path,
        profile_name=aws_profile_name,
        region=region,
    )

    # Step 3: Upload main.py script to S3
    main_script_path = os.path.join(source_folder, "main.py")
    if not os.path.exists(main_script_path):
        print("[ERROR] main.py not found in source folder — skipping upload.")
        exit(1)

    upload_file_to_s3(
        bucket_name=bucket_name,
        s3_key=f"{s3_script_prefix}/main.py",
        file_path=main_script_path,
        profile_name=aws_profile_name,
        region=region,
    )

    print("[SUCCESS] All files uploaded successfully.")

    # Step 4: Clean up
    if os.path.exists(zip_output_path):
        print(f"[INFO] Cleaning up {zip_output_path}")
        os.remove(zip_output_path)

    print("[INFO] Done.")
