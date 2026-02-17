"""Letta tool for invoking the AWS CLI via subprocess."""

import subprocess


def call_aws(
    command: str,
    region: str = "",
    profile: str = "",
    output_format: str = "json",
    timeout: int = 60,
) -> str:
    """Call the AWS CLI with a command and return the response.

    Args:
        command: The AWS CLI command (e.g. "s3 ls", "ec2 describe-instances").
        region: Optional AWS region override (e.g. "us-west-2").
        profile: Optional AWS CLI profile name.
        output_format: Output format - "json", "text", or "table". Defaults to "json".
        timeout: Subprocess timeout in seconds. Defaults to 60.

    Returns:
        The AWS CLI output, or an error message string on failure.
    """
    cmd = ["aws"] + command.split()

    if region:
        cmd.extend(["--region", region])

    if profile:
        cmd.extend(["--profile", profile])

    cmd.extend(["--output", output_format])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: AWS CLI timed out after {timeout} seconds."
    except FileNotFoundError:
        return "Error: aws binary not found. Ensure the AWS CLI is installed and on PATH."

    if result.returncode != 0:
        stderr = result.stderr.strip()
        return f"Error: AWS CLI exited with code {result.returncode}. stderr: {stderr}"

    return result.stdout
