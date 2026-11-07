"""Remove chart workbooks from a validated PowerPoint package before rendering."""

import posixpath
import re
from pathlib import Path
from shutil import copyfileobj
from typing import NoReturn
from urllib.parse import unquote
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from lxml import etree

from app.core.exceptions import ConversionError, ValidationError
from app.core.file_utils import private_binary_writer

CHART_WORKBOOK_PATH = re.compile(r"ppt/embeddings/[A-Za-z0-9_. -]+\.(?i:xlsx)")
_CHART_RELS_PATH = re.compile(r"ppt/charts/_rels/([A-Za-z0-9_.-]+\.xml)\.rels")
_CHART_NS = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
_OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_CONTENT_TYPES_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"
_REL_ID = f"{{{_OFFICE_REL_NS}}}id"
_CACHE_TAGS = {
    "numRef": "numCache",
    "strRef": "strCache",
    "multiLvlStrRef": "multiLvlStrCache",
}
_MAX_METADATA_PART_BYTES = 8 * 1024 * 1024
_MAX_REWRITTEN_CHART_BYTES = 32 * 1024 * 1024


def write_pptx_without_chart_workbooks(
    archive: ZipFile, entries: list[ZipInfo], workbooks: set[str], output_path: Path
) -> None:
    """Write a local copy using cached chart data and omitting workbook bytes."""
    rewritten: dict[str, bytes] = {}
    rewritten_chart_bytes = 0
    referenced: set[str] = set()
    workbook_names = {name.casefold(): name for name in workbooks}
    part_names = set(archive.namelist())

    for entry in entries:
        if entry.is_dir() or not entry.filename.casefold().endswith(".rels"):
            continue

        rels = _parse_part(archive, entry.filename)
        source_dir = posixpath.dirname(
            posixpath.dirname(entry.filename.replace("\\", "/"))
        )
        for relationship in list(rels):
            target = relationship.get("Target", "")
            part = _resolve_part(source_dir, target)
            relationship_type = relationship.get("Type", "")
            if part.casefold() not in workbook_names:
                if relationship_type.rsplit("/", 1)[-1].casefold() in {
                    "oleobject",
                    "package",
                }:
                    _reject_workbook()
                continue

            chart_match = _CHART_RELS_PATH.fullmatch(entry.filename)
            relationship_id = relationship.get("Id")
            if (
                not chart_match
                or relationship.tag != f"{_PACKAGE_REL_NS}Relationship"
                or relationship_type != f"{_OFFICE_REL_NS}/package"
                or relationship.get("TargetMode", "Internal").casefold() != "internal"
                or not relationship_id
                or sum(rel.get("Id") == relationship_id for rel in rels) != 1
            ):
                _reject_workbook()

            chart_path = f"ppt/charts/{chart_match[1]}"
            if chart_path not in part_names or chart_path in rewritten:
                _reject_workbook()

            chart = _parse_part(archive, chart_path)
            _remove_workbook_reference(chart, relationship_id)
            rewritten[chart_path] = etree.tostring(chart)
            referenced.add(workbook_names[part.casefold()])
            rels.remove(relationship)
            rewritten[entry.filename] = etree.tostring(rels)
            rewritten_chart_bytes += len(rewritten[chart_path]) + len(
                rewritten[entry.filename]
            )
            if rewritten_chart_bytes > _MAX_REWRITTEN_CHART_BYTES:
                _reject_oversized_metadata()

    if referenced != workbooks:
        _reject_workbook()

    content_types = _parse_part(archive, "[Content_Types].xml")
    removed_override = False
    for override in content_types.findall(f"{_CONTENT_TYPES_NS}Override"):
        if _resolve_part("", override.get("PartName", "")).casefold() in workbook_names:
            content_types.remove(override)
            removed_override = True
    if removed_override:
        rewritten["[Content_Types].xml"] = etree.tostring(content_types)

    try:
        with (
            private_binary_writer(output_path) as output,
            ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=1) as filtered,
        ):
            for entry in entries:
                if entry.is_dir() or entry.filename in workbooks:
                    continue
                if entry.filename in rewritten:
                    filtered.writestr(entry.filename, rewritten[entry.filename])
                else:
                    with (
                        archive.open(entry) as source,
                        filtered.open(entry.filename, "w") as target,
                    ):
                        copyfileobj(source, target, length=1024 * 1024)
    except OSError as exc:
        raise ConversionError(
            "file_processing_failed",
            "PrivCon could not prepare a temporary PowerPoint copy.",
        ) from exc


def _resolve_part(source_dir: str, target: str) -> str:
    path = unquote(target.split("#", 1)[0].split("?", 1)[0]).replace("\\", "/")
    return posixpath.normpath(posixpath.join("/", source_dir, path)).lstrip("/")


def _parse_part(archive: ZipFile, name: str) -> etree._Element:
    if archive.getinfo(name).file_size > _MAX_METADATA_PART_BYTES:
        _reject_oversized_metadata()
    # The package validator has already checked the bytes for DTDs and entities.
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    try:
        with archive.open(name) as part:
            return etree.parse(part, parser).getroot()
    except etree.XMLSyntaxError as exc:
        raise ValidationError(
            "corrupted_file", "The PowerPoint file contains malformed chart metadata."
        ) from exc


def _remove_workbook_reference(chart: etree._Element, relationship_id: str) -> None:
    external_data = chart.findall(f"{_CHART_NS}externalData")
    if (
        chart.tag != f"{_CHART_NS}chartSpace"
        or len(external_data) != 1
        or external_data[0].get(_REL_ID) != relationship_id
        or sum(node.get(_REL_ID) == relationship_id for node in chart.iter()) != 1
    ):
        _reject_workbook()

    plot_area = chart.find(f"{_CHART_NS}chart/{_CHART_NS}plotArea")
    if plot_area is None:
        _reject_workbook()

    auto_update = external_data[0].find(f"{_CHART_NS}autoUpdate")
    if auto_update is not None and auto_update.get("val") not in {"0", "false"}:
        _reject_workbook()

    for ref_tag, cache_tag in _CACHE_TAGS.items():
        for ref in chart.iter(f"{_CHART_NS}{ref_tag}"):
            points = ref.findall(f"{_CHART_NS}{cache_tag}//{_CHART_NS}pt")
            if not points or any(
                point.find(f"{_CHART_NS}v") is None for point in points
            ):
                _reject_workbook()

    if plot_area.find(f".//{_CHART_NS}pt/{_CHART_NS}v") is None:
        _reject_workbook()

    chart.remove(external_data[0])


def _reject_workbook() -> NoReturn:
    raise ValidationError(
        "unsafe_document_content",
        "PrivCon can only convert PowerPoint chart workbooks using saved chart values.",
    )


def _reject_oversized_metadata() -> NoReturn:
    raise ValidationError(
        "oversized_file", "The PowerPoint chart metadata is too large to process."
    )
