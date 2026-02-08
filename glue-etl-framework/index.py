import os
import boto3
import json

glue_client = boto3.client("glue")


def lambda_handler(event, context):
    # Get job name from environment variables
    glue_job_name = os.environ.get("GLUE_JOB_NAME")
    if not glue_job_name:
        return {
            "statusCode": 500,
            "body": json.dumps("Environment variable GLUE_JOB_NAME is required."),
        }

    # Collect arguments from environment variables (optional)
    env_args = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("ARG_")  # All env vars prefixed with ARG_ will be passed
    }

    # Collect arguments from event payload (optional)
    payload_args = event.get("job_args", {}) if isinstance(event, dict) else {}

    # Merge arguments, payload overrides env
    job_args = {**env_args, **payload_args}

    # AWS Glue expects arguments with '--' prefix
    glue_args = {f"--{key}": str(value) for key, value in job_args.items()}

    try:
        response = glue_client.start_job_run(JobName=glue_job_name, Arguments=glue_args)
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Glue job triggered successfully",
                    "JobRunId": response["JobRunId"],
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Failed to start Glue job: {str(e)}"),
        }
