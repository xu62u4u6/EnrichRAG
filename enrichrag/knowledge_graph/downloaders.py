"""Unified download and decompression for all KG data sources."""

from __future__ import annotations

import gzip
import logging
import shutil
import time
import urllib.request
from pathlib import Path

from enrichrag.knowledge_graph.progress import NullProgressReporter, ProgressEvent, ProgressReporter

logger = logging.getLogger(__name__)

NCBI_GENE_INFO_URL = (
    "https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/"
    "Homo_sapiens.gene_info.gz"
)

STRING_LINKS_URL = (
    "https://stringdb-downloads.org/download/protein.links.v12.0/"
    "9606.protein.links.v12.0.txt.gz"
)
STRING_LINKS_DETAILED_URL = (
    "https://stringdb-downloads.org/download/protein.links.detailed.v12.0/"
    "9606.protein.links.detailed.v12.0.txt.gz"
)
STRING_ALIASES_URL = (
    "https://stringdb-downloads.org/download/protein.aliases.v12.0/"
    "9606.protein.aliases.v12.0.txt.gz"
)

KEGG_LIST_URL = "https://rest.kegg.jp/list/pathway/hsa"
KEGG_KGML_URL = "https://rest.kegg.jp/get/{pathway_id}/kgml"

PUBTATOR_RELATION_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/lu/PubTator3/relation2pubtator3.gz"
)

REACTOME_FI_URL = (
    "https://reactome.org/download/tools/ReactomeFIs/"
    "FIsInGene_04142025_with_annotations.txt.zip"
)
REACTOME_GRAPHDB_URL = (
    "https://download.reactome.org/95/reactome.graphdb.tgz"
)

# Block size for download progress reporting
_DOWNLOAD_BLOCK = 64 * 1024  # 64 KB


def _download_file(
    url: str,
    dest: Path,
    force: bool = False,
    progress: ProgressReporter | None = None,
    step: str = "download",
) -> Path:
    """Download a file with progress reporting."""
    if dest.exists() and not force:
        logger.info("Already exists: %s", dest)
        if progress:
            progress.report(ProgressEvent(
                step=step, message=f"Already exists: {dest.name}", done=True,
            ))
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading %s -> %s", url, dest)
    req = urllib.request.urlopen(url)
    total = int(req.headers.get("Content-Length", 0))
    downloaded = 0

    if progress:
        progress.report(ProgressEvent(
            step=step, message=f"Downloading {dest.name}",
            current=0, total=total, unit="bytes",
        ))

    with open(dest, "wb") as f:
        while True:
            chunk = req.read(_DOWNLOAD_BLOCK)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if progress:
                progress.report(ProgressEvent(
                    step=step, message=f"Downloading {dest.name}",
                    current=downloaded, total=total, unit="bytes",
                ))

    req.close()
    if progress:
        progress.report(ProgressEvent(
            step=step, message=f"Downloaded {dest.name}",
            current=downloaded, total=downloaded, unit="bytes", done=True,
        ))
    return dest


def _gunzip(
    gz_path: Path,
    force: bool = False,
    progress: ProgressReporter | None = None,
    step: str = "decompress",
) -> Path:
    """Decompress .gz file with progress reporting."""
    out_path = gz_path.with_suffix("")
    if out_path.exists() and not force:
        return out_path

    gz_size = gz_path.stat().st_size
    if progress:
        progress.report(ProgressEvent(
            step=step, message=f"Decompressing {gz_path.name}",
            current=0, total=gz_size, unit="bytes",
        ))

    decompressed = 0
    with gzip.open(gz_path, "rb") as f_in, open(out_path, "wb") as f_out:
        while True:
            chunk = f_in.read(_DOWNLOAD_BLOCK)
            if not chunk:
                break
            f_out.write(chunk)
            decompressed += len(chunk)
            if progress:
                progress.report(ProgressEvent(
                    step=step, message=f"Decompressing {gz_path.name}",
                    current=min(decompressed, gz_size), total=gz_size, unit="bytes",
                ))

    if progress:
        progress.report(ProgressEvent(
            step=step, message=f"Decompressed {out_path.name}",
            current=gz_size, total=gz_size, unit="bytes", done=True,
        ))
    logger.info("Decompressed %s", out_path)
    return out_path


def download_ncbi(
    data_dir: Path, force: bool = False, progress: ProgressReporter | None = None,
) -> Path:
    """Download and decompress NCBI Homo_sapiens.gene_info."""
    dl_dir = data_dir / "downloads"
    gz_path = _download_file(
        NCBI_GENE_INFO_URL, dl_dir / "Homo_sapiens.gene_info.gz",
        force, progress, step="download_ncbi",
    )
    return _gunzip(gz_path, force, progress, step="decompress_ncbi")


def download_string(
    data_dir: Path, force: bool = False, detailed: bool = False,
    progress: ProgressReporter | None = None,
) -> dict[str, Path]:
    """Download STRING links and aliases, decompress."""
    dl_dir = data_dir / "downloads"
    links_url = STRING_LINKS_DETAILED_URL if detailed else STRING_LINKS_URL
    links_name = Path(links_url).name

    links_gz = _download_file(links_url, dl_dir / links_name, force, progress, step="download_string_links")
    aliases_gz = _download_file(STRING_ALIASES_URL, dl_dir / Path(STRING_ALIASES_URL).name, force, progress, step="download_string_aliases")

    return {
        "links": _gunzip(links_gz, force, progress, step="decompress_string_links"),
        "aliases": _gunzip(aliases_gz, force, progress, step="decompress_string_aliases"),
    }


def download_kegg(
    data_dir: Path, force: bool = False, delay_seconds: float = 0.3,
    progress: ProgressReporter | None = None,
) -> list[Path]:
    """Download KEGG pathway KGML files."""
    dl_dir = data_dir / "downloads" / "kegg"
    dl_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching KEGG pathway list...")
    with urllib.request.urlopen(KEGG_LIST_URL) as response:
        content = response.read().decode("utf-8")

    pathway_ids = []
    for line in content.splitlines():
        if not line.strip():
            continue
        pathway_id, _ = line.split("\t", 1)
        pathway_ids.append(pathway_id.replace("path:", ""))

    total = len(pathway_ids)
    logger.info("Found %d KEGG pathways", total)

    kgml_paths = []
    for i, pid in enumerate(pathway_ids):
        out = dl_dir / f"{pid}.kgml"
        if out.exists() and not force:
            kgml_paths.append(out)
            if progress:
                progress.report(ProgressEvent(
                    step="download_kegg", message=f"KEGG {pid} (cached)",
                    current=i + 1, total=total, unit="pathways",
                ))
            continue
        try:
            url = KEGG_KGML_URL.format(pathway_id=pid)
            with urllib.request.urlopen(url) as response:
                out.write_text(response.read().decode("utf-8"), encoding="utf-8")
            kgml_paths.append(out)
            if progress:
                progress.report(ProgressEvent(
                    step="download_kegg", message=f"KEGG {pid}",
                    current=i + 1, total=total, unit="pathways",
                ))
            time.sleep(delay_seconds)
        except Exception as e:
            logger.warning("Failed to download %s: %s", pid, e)
            if progress:
                progress.report(ProgressEvent(
                    step="download_kegg", message=f"KEGG {pid} failed: {e}",
                    current=i + 1, total=total, unit="pathways",
                ))

    if progress:
        progress.report(ProgressEvent(
            step="download_kegg", message=f"Downloaded {len(kgml_paths)}/{total} pathways",
            current=total, total=total, unit="pathways", done=True,
        ))
    return kgml_paths


def download_pubtator(
    data_dir: Path, force: bool = False, progress: ProgressReporter | None = None,
) -> Path:
    """Download and decompress PubTator relation2pubtator3."""
    dl_dir = data_dir / "downloads"
    gz_path = _download_file(
        PUBTATOR_RELATION_URL, dl_dir / "relation2pubtator3.gz",
        force, progress, step="download_pubtator",
    )
    return _gunzip(gz_path, force, progress, step="decompress_pubtator")


def download_reactome(
    data_dir: Path, force: bool = False, progress: ProgressReporter | None = None,
) -> Path:
    """Download and extract Reactome FIsInGene zip."""
    import zipfile

    dl_dir = data_dir / "downloads"
    zip_name = Path(REACTOME_FI_URL).name
    zip_path = _download_file(
        REACTOME_FI_URL, dl_dir / zip_name,
        force, progress, step="download_reactome",
    )

    # Extract the .txt from the zip
    txt_path = dl_dir / "FIsInGene_with_annotations.txt"
    if txt_path.exists() and not force:
        return txt_path

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Find the txt file inside
        txt_names = [n for n in zf.namelist() if n.endswith(".txt")]
        if not txt_names:
            raise FileNotFoundError(f"No .txt file found in {zip_path}")
        zf.extract(txt_names[0], dl_dir)
        extracted = dl_dir / txt_names[0]
        if extracted != txt_path:
            extracted.rename(txt_path)

    logger.info("Extracted %s", txt_path)
    if progress:
        progress.report(ProgressEvent(
            step="extract_reactome", message=f"Extracted {txt_path.name}",
            done=True,
        ))
    return txt_path
