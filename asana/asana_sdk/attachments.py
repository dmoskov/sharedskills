#!/usr/bin/env python3
"""
Asana Attachment Operations

Functions for managing file attachments on Asana tasks.
Supports upload, download, list, get, and delete operations.
"""

import logging
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import infrastructure
from .infrastructure import (
    get_client,
    with_api_error_handling,
    ASANA_SDK_AVAILABLE,
    asana,
)

# Import error classes
from .errors import AsanaClientError

# Configure logging
logger = logging.getLogger(__name__)


def upload_attachment_to_task(
    task_gid: str,
    file_path: Optional[str] = None,
    file_content: Optional[bytes] = None,
    file_name: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upload a file attachment to an Asana task.

    Can upload either from a file path or from raw bytes content.
    Supports images (PNG, JPG, GIF), PDFs, and other file types.

    Args:
        task_gid: Asana task GID to attach the file to
        file_path: Path to the file to upload (use this OR file_content)
        file_content: Raw bytes content to upload (use this OR file_path)
        file_name: Name for the file (required if using file_content,
                   defaults to basename if using file_path)
        content_type: MIME type (auto-detected from extension if not provided)

    Returns:
        Attachment data dictionary with gid, name, download_url, etc.

    Raises:
        AsanaClientError: If the upload fails
        ValueError: If inputs are invalid

    Example:
        # Upload from file path
        attachment = upload_attachment_to_task(
            task_gid='1234567890',
            file_path='/path/to/screenshot.png'
        )

        # Upload from bytes
        attachment = upload_attachment_to_task(
            task_gid='1234567890',
            file_content=image_bytes,
            file_name='chart.png',
            content_type='image/png'
        )
    """
    import mimetypes

    if not task_gid:
        raise ValueError("task_gid is required")

    if not file_path and not file_content:
        raise ValueError("Either file_path or file_content is required")

    if file_path and file_content:
        raise ValueError("Provide either file_path or file_content, not both")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    # Get file content and metadata
    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"File not found: {file_path}")

        file_name = file_name or path.name
        with open(path, "rb") as f:
            file_content = f.read()

        # Auto-detect content type from extension
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(path))
            content_type = content_type or "application/octet-stream"
    else:
        if not file_name:
            raise ValueError("file_name is required when using file_content")
        if not content_type:
            content_type, _ = mimetypes.guess_type(file_name)
            content_type = content_type or "application/octet-stream"

    logger.info(
        f"Uploading attachment '{file_name}' ({content_type}, {len(file_content)} bytes) to task {task_gid}"
    )

    client = get_client()
    attachments_api = asana.AttachmentsApi(client)

    # The Asana SDK v5 expects a file path for the 'file' parameter
    # We need to write content to a temp file first
    # The filename in Asana comes from the file path, so we use the actual name

    # Create a temp directory and write file with the actual desired name
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, file_name)
    with open(tmp_path, "wb") as tmp_file:
        tmp_file.write(file_content)

    try:
        # SDK v5 signature: create_attachment_for_object(opts, **kwargs)
        # All form parameters go in the opts dict
        opts = {
            "parent": task_gid,
            "file": tmp_path,
            "name": file_name,
            "opt_fields": "gid,name,download_url,view_url,permanent_url,created_at,size",
        }
        result = attachments_api.create_attachment_for_object(opts)

        attachment_data = (
            result.to_dict() if hasattr(result, "to_dict") else dict(result)
        )
        logger.info(
            f"Uploaded attachment '{file_name}' with gid {attachment_data.get('gid')}"
        )
        return attachment_data
    finally:
        # Clean up temp file and directory
        import shutil

        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


@with_api_error_handling("getting attachments for task {task_gid}")
def get_task_attachments(
    task_gid: str, opt_fields: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all attachments for an Asana task.

    Args:
        task_gid: Asana task GID
        opt_fields: Comma-separated list of optional fields to include

    Returns:
        List of attachment dictionaries with gid, name, download_url, etc.

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        attachments = get_task_attachments('1234567890')
        for att in attachments:
            print(f"{att['name']}: {att['download_url']}")
    """
    if not task_gid:
        raise ValueError("task_gid is required")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Fetching attachments for task {task_gid}")

    client = get_client()
    attachments_api = asana.AttachmentsApi(client)

    # Default fields to include
    if opt_fields is None:
        opt_fields = "gid,name,resource_subtype,download_url,view_url,permanent_url,created_at,size"

    opts = {"opt_fields": opt_fields, "limit": 100}

    # Get attachments for the task (parent parameter)
    result = attachments_api.get_attachments_for_object(task_gid, opts)

    # Convert to list of dicts
    attachments = []
    for attachment in result:
        att_dict = (
            attachment.to_dict() if hasattr(attachment, "to_dict") else dict(attachment)
        )
        attachments.append(att_dict)

    logger.info(f"Found {len(attachments)} attachments for task {task_gid}")
    return attachments


@with_api_error_handling("getting attachment {attachment_gid}")
def get_attachment(
    attachment_gid: str, opt_fields: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get details about a specific attachment.

    Note: download_url is only valid for ~2 minutes after retrieval.
    Refresh on demand rather than storing.

    Args:
        attachment_gid: Asana attachment GID
        opt_fields: Comma-separated list of optional fields to include

    Returns:
        Attachment dictionary with full details including download_url

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        attachment = get_attachment('9876543210')
        download_url = attachment['download_url']  # Valid for ~2 minutes
    """
    if not attachment_gid:
        raise ValueError("attachment_gid is required")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Fetching attachment {attachment_gid}")

    client = get_client()
    attachments_api = asana.AttachmentsApi(client)

    # Default fields to include
    if opt_fields is None:
        opt_fields = "gid,name,resource_subtype,download_url,view_url,permanent_url,created_at,size,parent"

    opts = {"opt_fields": opt_fields}

    result = attachments_api.get_attachment(attachment_gid, opts)
    attachment_data = result.to_dict() if hasattr(result, "to_dict") else dict(result)

    logger.info(f"Retrieved attachment '{attachment_data.get('name')}'")
    return attachment_data


def download_attachment(
    attachment_gid: str, output_path: Optional[str] = None
) -> bytes:
    """
    Download an attachment's content.

    If output_path is provided, saves to file. Otherwise returns bytes.

    Args:
        attachment_gid: Asana attachment GID
        output_path: Optional path to save the file to

    Returns:
        File content as bytes

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid
        IOError: If file cannot be written

    Example:
        # Get bytes
        content = download_attachment('9876543210')

        # Save to file
        download_attachment('9876543210', '/tmp/image.png')
    """
    if not attachment_gid:
        raise ValueError("attachment_gid is required")

    # Get fresh download URL (they expire after ~2 minutes)
    attachment = get_attachment(attachment_gid)
    download_url = attachment.get("download_url")

    if not download_url:
        raise AsanaClientError(
            f"No download_url available for attachment {attachment_gid}"
        )

    logger.info(f"Downloading attachment from {download_url[:50]}...")

    try:
        req = urllib.request.Request(download_url)
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()

        logger.info(f"Downloaded {len(content)} bytes")

        if output_path:
            with open(output_path, "wb") as f:
                f.write(content)
            logger.info(f"Saved to {output_path}")

        return content

    except urllib.error.URLError as e:
        raise AsanaClientError(f"Failed to download attachment: {e}")


@with_api_error_handling("deleting attachment {attachment_gid}")
def delete_attachment(attachment_gid: str) -> bool:
    """
    Delete an attachment from Asana.

    Args:
        attachment_gid: Asana attachment GID to delete

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid
    """
    if not attachment_gid:
        raise ValueError("attachment_gid is required")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Deleting attachment {attachment_gid}")

    client = get_client()
    attachments_api = asana.AttachmentsApi(client)

    attachments_api.delete_attachment(attachment_gid)
    logger.info(f"Deleted attachment {attachment_gid}")
    return True
