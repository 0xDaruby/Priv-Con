"""Structural validators for Office, PDF, and image uploads."""

import warnings
import zipfile
from pathlib import Path, PurePosixPath
from stat import S_IFLNK, S_IFMT
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import settings
from app.core.exceptions import ValidationError

EXPECTED_EXTENSION = {
    "docx": ".docx",
    "pptx": ".pptx",
    "xlsx": ".xlsx",
}

EXPECTED_INTERNAL_PATH = {
    "docx": "word/document.xml",
    "pptx": "ppt/presentation.xml",
    "xlsx": "xl/workbook.xml",
}

EXPECTED_ROOT_ELEMENT = {
    "docx": "document",
    "pptx": "presentation",
    "xlsx": "workbook",
}

REQUIRED_PACKAGE_PATHS = {
    "[Content_Types].xml": "Types",
    "_rels/.rels": "Relationships",
}

IMAGE_EXTENSION_TO_FORMAT = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}

_ALLOWED_OFFICE_COMPRESSION = {
    zipfile.ZIP_STORED,
    zipfile.ZIP_DEFLATED,
}
_BLOCKED_OFFICE_PARTS = (
    "/vbaproject.bin",
    "/embeddings/",
    "/activex/",
)
_XML_DECLARATION_MARKERS = (b"<!doctype", b"<!entity")
_ARCHIVE_READ_CHUNK_SIZE = 1024 * 1024
_MAX_ARCHIVE_PATH_LENGTH = 512
_SAFE_EXTERNAL_RELATIONSHIP_TYPES = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink".casefold(),
}
_DANGEROUS_PDF_ACTIONS = {
    "/GoToR",
    "/ImportData",
    "/JavaScript",
    "/Launch",
    "/RichMediaExecute",
    "/Rendition",
    "/SubmitForm",
}
_DANGEROUS_PDF_ANNOTATIONS = {
    "/3D",
    "/FileAttachment",
    "/RichMedia",
    "/Screen",
}


def validate_extension(filename: str, tool_key: str) -> None:
    expected = EXPECTED_EXTENSION[tool_key]

    if not (filename or "").lower().endswith(expected):
        raise ValidationError(
            code="unsupported_file_type",
            message=f"Only {expected} files are accepted for this tool.",
        )


def validate_office_structure(file_path: Path, tool_key: str) -> None:
    """Confirm that an Office upload is a coherent ZIP/XML package."""
    if not zipfile.is_zipfile(file_path):
        _raise_invalid_office_document()

    expected_path = EXPECTED_INTERNAL_PATH[tool_key]

    try:
        with zipfile.ZipFile(file_path) as archive:
            entries = archive.infolist()
            names = [entry.filename.replace("\\", "/") for entry in entries]

            if len(entries) > settings.max_office_archive_entries:
                raise ValidationError(
                    code="oversized_file",
                    message="The Office document contains too many package entries.",
                )

            normalized_names = [name.casefold() for name in names]

            if len(normalized_names) != len(set(normalized_names)):
                _raise_corrupted_office(
                    "This Office document contains duplicate package entries."
                )

            _validate_archive_metadata(entries)

            required_parts = {
                **REQUIRED_PACKAGE_PATHS,
                expected_path: EXPECTED_ROOT_ELEMENT[tool_key],
            }
            missing_parts = set(required_parts).difference(names)

            if missing_parts:
                _raise_corrupted_office(
                    "This file doesn't match the expected Office document structure."
                )

            # Read every member without extracting it. This verifies CRCs and
            # ensures hidden media cannot bypass archive resource limits.
            for entry in entries:
                if not entry.is_dir():
                    _drain_archive_entry(archive, entry)

            for part_name, expected_root in required_parts.items():
                root = _read_office_xml_part(archive, part_name)

                if _local_xml_name(root.tag) != expected_root:
                    _raise_corrupted_office(
                        "This Office document contains an invalid XML structure."
                    )

            _validate_office_relationships(archive, entries)
            _validate_content_types(archive)
    except ValidationError:
        raise
    except (
        zipfile.BadZipFile,
        NotImplementedError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        _raise_invalid_office_document(exc)


def validate_office_file(file_path: Path, filename: str, tool_key: str) -> None:
    """Validate an Office upload's extension and package structure."""
    validate_extension(filename, tool_key)
    validate_office_structure(file_path, tool_key)


def validate_pdf_extension(filename: str) -> None:
    """Reject files that are not presented as PDFs before saving them."""
    if not (filename or "").lower().endswith(".pdf"):
        raise ValidationError(
            code="unsupported_file_type",
            message="Only .pdf files are accepted for this tool.",
        )


def validate_pdf_structure(file_path: Path) -> int:
    """Confirm that an uploaded PDF is readable, unencrypted, and non-empty."""
    try:
        with file_path.open("rb") as uploaded_file:
            if b"%PDF-" not in uploaded_file.read(1024):
                raise ValidationError(
                    code="corrupted_file",
                    message="This file isn't a valid or readable PDF.",
                )

        reader = PdfReader(str(file_path), strict=True)

        try:
            if reader.is_encrypted:
                raise ValidationError(
                    code="password_protected",
                    message="Password-protected PDFs are not supported.",
                )

            page_count = len(reader.pages)

            if page_count == 0:
                raise ValidationError(
                    code="empty_pdf",
                    message="PDF files must contain at least one page.",
                )

            if page_count > settings.max_pdf_pages_per_job:
                raise ValidationError(
                    code="too_many_pages",
                    message=(
                        "The PDF exceeds the safe page-count limit of "
                        f"{settings.max_pdf_pages_per_job} pages."
                    ),
                )

            for page in reader.pages:
                _ = page.mediabox.width
                _ = page.mediabox.height

            _validate_pdf_active_content(reader)

            return page_count
        finally:
            reader.close()
    except ValidationError:
        raise
    except (
        OSError,
        PdfReadError,
        EOFError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid or readable PDF.",
        ) from exc


def validate_pdf_file(file_path: Path, filename: str) -> int:
    """Validate a PDF upload's extension and content structure."""
    validate_pdf_extension(filename)
    return validate_pdf_structure(file_path)


def validate_image_extension(filename: str) -> str:
    """Validate an image filename and return its normalized extension."""
    extension = Path(filename or "").suffix.lower()

    if extension not in IMAGE_EXTENSION_TO_FORMAT:
        raise ValidationError(
            code="unsupported_file_type",
            message="Only .jpg, .jpeg, .png, and .webp files are accepted.",
        )

    return extension


def validate_image_structure(file_path: Path, filename: str) -> int:
    """Verify image content and return its decoded pixel count."""
    extension = validate_image_extension(filename)
    expected_format = IMAGE_EXTENSION_TO_FORMAT[extension]

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            allowed_formats = sorted(set(IMAGE_EXTENSION_TO_FORMAT.values()))

            with Image.open(file_path, formats=allowed_formats) as image:
                actual_format = image.format
                pixel_count = image.width * image.height

                if pixel_count > settings.max_image_pixels:
                    raise ValidationError(
                        code="oversized_file",
                        message="The image dimensions exceed safe processing limits.",
                    )

                image.verify()

            with Image.open(file_path, formats=allowed_formats) as image:
                image.seek(0)
                image.load()
    except ValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError(
            code="oversized_file",
            message="The image dimensions exceed safe processing limits.",
        ) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid or readable image.",
        ) from exc

    if actual_format != expected_format:
        raise ValidationError(
            code="file_type_mismatch",
            message="The image content does not match its file extension.",
        )

    return pixel_count


def validate_image_file(file_path: Path, filename: str) -> int:
    """Validate an image upload's extension and content structure."""
    validate_image_extension(filename)
    return validate_image_structure(file_path, filename)


def _validate_archive_metadata(entries: list[zipfile.ZipInfo]) -> None:
    max_uncompressed = settings.max_office_uncompressed_size_mb * 1024 * 1024
    total_uncompressed = 0

    for entry in entries:
        normalized_name = entry.filename.replace("\\", "/")

        if _is_unsafe_archive_path(normalized_name):
            _raise_corrupted_office(
                "This Office document contains an invalid package path."
            )

        if entry.flag_bits & 0x1:
            _raise_corrupted_office("Encrypted Office documents are not supported.")

        if entry.compress_type not in _ALLOWED_OFFICE_COMPRESSION:
            _raise_corrupted_office(
                "This Office document uses an unsupported compression method."
            )

        unix_file_type = S_IFMT(entry.external_attr >> 16)

        if unix_file_type == S_IFLNK:
            _raise_corrupted_office(
                "This Office document contains an invalid symbolic link."
            )

        lower_name = f"/{normalized_name.casefold().strip('/')}"

        if any(marker in lower_name for marker in _BLOCKED_OFFICE_PARTS):
            raise ValidationError(
                code="unsafe_document_content",
                message=(
                    "Office documents containing macros, ActiveX, or embedded "
                    "objects are not supported."
                ),
            )

        if entry.is_dir():
            continue

        total_uncompressed += entry.file_size

        if total_uncompressed > max_uncompressed:
            raise ValidationError(
                code="oversized_file",
                message=(
                    "The Office document expands beyond the safe processing limit."
                ),
            )

        if entry.file_size > max_uncompressed:
            raise ValidationError(
                code="oversized_file",
                message="The Office document contains an oversized internal component.",
            )

        if entry.file_size > 0 and entry.compress_size == 0:
            raise ValidationError(
                code="oversized_file",
                message="The Office document has an unsafe compression ratio.",
            )

        if entry.compress_size > 0:
            compression_ratio = entry.file_size / entry.compress_size

            if compression_ratio > settings.max_office_compression_ratio:
                raise ValidationError(
                    code="oversized_file",
                    message="The Office document has an unsafe compression ratio.",
                )


def _drain_archive_entry(
    archive: zipfile.ZipFile,
    entry: zipfile.ZipInfo,
) -> None:
    bytes_read = 0
    xml_tail = b""
    is_xml = entry.filename.casefold().endswith((".xml", ".rels"))

    with archive.open(entry, "r") as member:
        while chunk := member.read(_ARCHIVE_READ_CHUNK_SIZE):
            bytes_read += len(chunk)

            if bytes_read > entry.file_size:
                _raise_corrupted_office(
                    "This Office document contains an invalid package entry."
                )

            if is_xml:
                normalized_xml = (xml_tail + chunk).replace(b"\x00", b"").lower()

                if any(marker in normalized_xml for marker in _XML_DECLARATION_MARKERS):
                    raise ValidationError(
                        code="unsafe_document_content",
                        message=(
                            "Office XML containing DTD or entity declarations "
                            "is not supported."
                        ),
                    )

                xml_tail = normalized_xml[-32:]

    if bytes_read != entry.file_size:
        _raise_corrupted_office(
            "This Office document contains a truncated package entry."
        )


def _validate_office_relationships(
    archive: zipfile.ZipFile,
    entries: list[zipfile.ZipInfo],
) -> None:
    for entry in entries:
        normalized_name = entry.filename.replace("\\", "/")

        if entry.is_dir() or not normalized_name.casefold().endswith(".rels"):
            continue

        root = _read_office_xml_part(archive, entry.filename)

        if _local_xml_name(root.tag) != "Relationships":
            _raise_corrupted_office(
                "This Office document contains invalid relationship metadata."
            )

        for relationship in root:
            is_external = (
                _local_xml_name(relationship.tag) == "Relationship"
                and relationship.attrib.get("TargetMode", "").casefold() == "external"
            )
            relationship_type = relationship.attrib.get("Type", "").casefold()

            if (
                is_external
                and relationship_type not in _SAFE_EXTERNAL_RELATIONSHIP_TYPES
            ):
                raise ValidationError(
                    code="unsafe_document_content",
                    message=(
                        "Office documents with external relationships are not "
                        "supported for private local conversion."
                    ),
                )


def _validate_content_types(archive: zipfile.ZipFile) -> None:
    content = _read_archive_entry(archive, "[Content_Types].xml").lower()

    if b"macroenabled" in content or b"vbaproject" in content:
        raise ValidationError(
            code="unsafe_document_content",
            message="Macro-enabled Office documents are not supported.",
        )


def _read_office_xml_part(
    archive: zipfile.ZipFile,
    part_name: str,
) -> ElementTree.Element:
    entry = archive.getinfo(part_name)
    max_uncompressed_size = settings.max_upload_size_mb * 1024 * 1024

    if entry.file_size > max_uncompressed_size:
        raise ValidationError(
            code="oversized_file",
            message="The Office document contains an oversized internal component.",
        )

    try:
        content = _read_archive_entry(archive, part_name)

        lowered_content = content.lstrip().lower()

        if any(marker in lowered_content for marker in _XML_DECLARATION_MARKERS):
            raise ValidationError(
                code="unsafe_document_content",
                message="Office XML containing DTD or entity declarations is not supported.",
            )

        return ElementTree.fromstring(content)
    except (zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="The Office document contains damaged or malformed XML.",
        ) from exc


def _is_unsafe_archive_path(filename: str) -> bool:
    path = PurePosixPath(filename.replace("\\", "/"))
    return (
        not filename
        or len(filename) > _MAX_ARCHIVE_PATH_LENGTH
        or "\x00" in filename
        or path.is_absolute()
        or ".." in path.parts
        or (path.parts and ":" in path.parts[0])
    )


def _read_archive_entry(archive: zipfile.ZipFile, part_name: str) -> bytes:
    entry = archive.getinfo(part_name)
    max_uncompressed_size = settings.max_upload_size_mb * 1024 * 1024

    if entry.file_size > max_uncompressed_size:
        raise ValidationError(
            code="oversized_file",
            message="The Office document contains an oversized internal component.",
        )

    content = bytearray()

    with archive.open(entry, "r") as member:
        while chunk := member.read(_ARCHIVE_READ_CHUNK_SIZE):
            content.extend(chunk)

            if len(content) > max_uncompressed_size:
                raise ValidationError(
                    code="oversized_file",
                    message=(
                        "The Office document contains an oversized internal component."
                    ),
                )

    return bytes(content)


def _validate_pdf_active_content(reader: PdfReader) -> None:
    """Reject PDF features that can execute code or carry embedded payloads."""
    root = _resolve_pdf_object(reader.trailer.get("/Root"))

    if not hasattr(root, "get"):
        _raise_unsafe_pdf()

    names = _resolve_pdf_object(root.get("/Names"))

    if hasattr(names, "get") and (
        names.get("/JavaScript") is not None or names.get("/EmbeddedFiles") is not None
    ):
        _raise_unsafe_pdf()

    if _contains_dangerous_pdf_action(root.get("/OpenAction")):
        _raise_unsafe_pdf()

    if _contains_dangerous_pdf_action(root.get("/AA")):
        _raise_unsafe_pdf()

    acro_form = _resolve_pdf_object(root.get("/AcroForm"))

    if _contains_dangerous_pdf_action(acro_form, max_nodes=10_000):
        _raise_unsafe_pdf()

    for page in reader.pages:
        if _contains_dangerous_pdf_action(page.get("/AA")):
            _raise_unsafe_pdf()

        annotations = _resolve_pdf_object(page.get("/Annots"))

        if not isinstance(annotations, (list, tuple)):
            continue

        for annotation_reference in annotations:
            annotation = _resolve_pdf_object(annotation_reference)

            if not hasattr(annotation, "get"):
                continue

            if str(annotation.get("/Subtype", "")) in _DANGEROUS_PDF_ANNOTATIONS:
                _raise_unsafe_pdf()

            if _contains_dangerous_pdf_action(annotation.get("/A")):
                _raise_unsafe_pdf()

            if _contains_dangerous_pdf_action(annotation.get("/AA")):
                _raise_unsafe_pdf()


def _contains_dangerous_pdf_action(
    value: object,
    *,
    max_nodes: int = 1_000,
) -> bool:
    pending = [value]
    visited: set[int] = set()

    while pending:
        current = _resolve_pdf_object(pending.pop())

        if current is None:
            continue

        object_id = id(current)

        if object_id in visited:
            continue

        visited.add(object_id)

        if len(visited) > max_nodes:
            return True

        if hasattr(current, "items"):
            items = list(current.items())

            if any(str(key) == "/JS" for key, _ in items):
                return True

            action_type = str(current.get("/S", ""))

            if action_type in _DANGEROUS_PDF_ACTIONS:
                return True

            for key, child in items:
                if str(key) in {"/A", "/AA", "/Fields", "/Kids", "/Next"}:
                    pending.append(child)
        elif isinstance(current, (list, tuple)):
            pending.extend(current)

    return False


def _resolve_pdf_object(value: object) -> object:
    try:
        get_object = getattr(value, "get_object", None)
        return get_object() if callable(get_object) else value
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(
            code="corrupted_file",
            message="This file isn't a valid or readable PDF.",
        ) from exc


def _raise_unsafe_pdf() -> None:
    raise ValidationError(
        code="unsafe_document_content",
        message=(
            "PDFs containing scripts, launch actions, rich media, or embedded "
            "files are not supported."
        ),
    )


def _local_xml_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _raise_corrupted_office(message: str) -> None:
    raise ValidationError(code="corrupted_file", message=message)


def _raise_invalid_office_document(exc: Exception | None = None) -> None:
    error = ValidationError(
        code="corrupted_file",
        message=(
            "This file isn't a valid Office document. It may be renamed, "
            "corrupted, or truncated."
        ),
    )

    if exc is None:
        raise error

    raise error from exc
