#  Copyright © 2025 Dr.-Ing. Paul Wilhelm <paul@wilhelm.dev>
#  This file is part of Archive Agent. See LICENSE for details.

import logging
import os
from typing import Set, List, Callable, Optional

import spacy
import pypandoc
from charset_normalizer import from_path

# noinspection PyPackageRequirements
import fitz  # PyMuPDF
import pymupdf4llm
from PIL import Image
import io

import re
import urllib.parse

from archive_agent.util.format import format_file

logger = logging.getLogger(__name__)


def is_text(file_path: str) -> bool:
    """
    Checks if the given file path has a valid text extension.
    :param file_path: File path.
    :return: True if the file path has a valid text extension, False otherwise.
    """
    return is_plaintext(file_path) or is_document(file_path)


def is_plaintext(file_path: str) -> bool:
    """
    Checks if the given file path has a valid plaintext extension.
    :param file_path: File path.
    :return: True if the file path has a valid plaintext extension, False otherwise.
    """
    extensions: Set[str] = {".txt", ".md"}
    return any(file_path.lower().endswith(ext) for ext in extensions)


def is_document(file_path: str) -> bool:
    """
    Checks if the given file path has a valid document extension.
    :param file_path: File path.
    :return: True if the file path has a valid document extension, False otherwise.
    """
    extensions: Set[str] = {".odt", ".docx", ".rtf", ".html"}
    return any(file_path.lower().endswith(ext) for ext in extensions)


def is_pdf_document(file_path: str) -> bool:
    """
    Checks if the given file path has a valid PDF document extension.
    :param file_path: File path.
    :return: True if the file path has a valid PDF document extension, False otherwise.
    """
    extensions: Set[str] = {".pdf"}
    return any(file_path.lower().endswith(ext) for ext in extensions)


def load_text(file_path: str) -> Optional[str]:
    """
    Load text.
    :param file_path: File path.
    :return: Text if successful, None otherwise.
    """
    if is_plaintext(file_path):
        return load_plaintext(file_path)

    elif is_document(file_path):
        return load_document(file_path)

    else:
        logger.warning(f"Cannot load {format_file(file_path)}")
        return None


def load_plaintext(file_path: str) -> Optional[str]:
    """
    Load plaintext.
    :param file_path: File path.
    :return: Plaintext if successful, None otherwise.
    """
    try:
        matches = from_path(file_path)
    except IOError as e:
        logger.warning(f"Failed to read {format_file(file_path)}: {e}")
        return None

    best_match = matches.best()
    if best_match is None:
        logger.warning(f"Failed to decode {format_file(file_path)}: Best match is None")
        return None

    return str(best_match)


def load_document(file_path: str) -> Optional[str]:
    """
    Load document.
    :param file_path: File path.
    :return: Text if successful, None otherwise.
    """
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    try:
        text = pypandoc.convert_file(file_path, to='plain', format=ext, extra_args=["--wrap=preserve"])
        return text.encode('utf-8', errors='replace').decode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to convert {format_file(file_path)}: {e}")
        return None


def load_pdf_document(
        file_path: str,
        image_to_text_callback: Callable[[Image.Image], Optional[str]]
) -> Optional[str]:
    """
    Load PDF document, extracting text and images in order.
    :param file_path: File path.
    :param image_to_text_callback: Function converting Image to text.
    :return: Text with image descriptions if successful, None otherwise.
    """
    try:
        # Extract markdown text using pymupdf4llm
        md_text = pymupdf4llm.to_markdown(file_path).split("\n")

        # Open document with PyMuPDF
        doc = fitz.open(file_path)

        result_parts: list[str] = []

        # noinspection PyTypeChecker
        for page_index, page in enumerate(doc):
            # Append markdown content line by line
            page_md_lines = [line for line in md_text if f"Page {page_index + 1}" in line]
            if page_md_lines:
                result_parts.extend(page_md_lines)
            else:
                logger.warning(f"Page {page_index + 1} appears to be a scanned page without OCR")

            # Extract images from page
            image_blocks = [
                b for b in page.get_text("dict")["blocks"] if b["type"] == 1
            ]
            for img_index, img_block in enumerate(image_blocks, start=1):
                result_parts.append(f"[Image {img_index} on Page {page_index + 1}]")
                image_bytes = img_block["image"]
                try:
                    with io.BytesIO(image_bytes) as img_io:
                        with Image.open(img_io) as img:
                            image_text = image_to_text_callback(img)
                            if image_text is None:
                                logger.warning(f"Failed to convert image on Page {page_index + 1}")
                                return None
                            result_parts.append(image_text)
                except Exception as e:
                    logger.warning(f"Failed to load {format_file(file_path)}: {e}")
                    return None

        return "\n\n".join(result_parts)

    except Exception as e:
        logger.warning(f"Failed to load {format_file(file_path)}: {e}")
        return None


def split_sentences(text: str) -> List[str]:
    """
    Split text into sentences.
    :param text: Text.
    :return: Sentences.
    """
    nlp = spacy.load("xx_sent_ud_sm")
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]


def sanitize_sentences(sentences: List[str]) -> List[str]:
    """
    Sanitize sentences (strip whitespace, split on newlines, ignore empty lines).
    :param sentences: Sentences.
    :return: Sanitized sentences.
    """
    result = []
    for sentence in sentences:
        for part in sentence.splitlines():
            s = part.strip()
            if s:
                result.append(s)
    return result


def group_blocks_of_sentences(sentences: List[str], sentences_per_block: int) -> List[List[str]]:
    """
    Group sentences into blocks of multiple sentences.
    :param sentences: Sentences.
    :param sentences_per_block: Sentences per block.
    :return: Blocks of multiple sentences.
    """
    return [
        sentences[i:i + sentences_per_block]
        for i in range(0, len(sentences), sentences_per_block)
    ]


def prepend_line_numbers(sentences: List[str]) -> List[str]:
    """
    Prepend line numbers to sentences.
    :param sentences: Sentences.
    :return: Sentences with line numbers.
    """
    return [
        f"{line_number + 1:<4}{sentence}"
        for line_number, sentence in enumerate(sentences)
    ]


def replace_file_uris_with_markdown(text: str) -> str:
    """
    Replace file:// URIs with Markdown links.
    :param text: Text.
    :return: Markdown.
    """
    pattern = re.compile(r'file://[^\s\])]+')

    def replacer(match):
        uri = match.group(0)
        decoded_path = urllib.parse.unquote(uri.replace('file://', ''))
        return f'[{decoded_path}]({uri})'

    return pattern.sub(replacer, text)
