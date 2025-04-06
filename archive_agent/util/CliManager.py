#  Copyright © 2025 Dr.-Ing. Paul Wilhelm <paul@wilhelm.dev>
#  This file is part of Archive Agent. See LICENSE for details.

from rich import print
from rich.panel import Panel
from rich.pretty import Pretty
import json
import logging
from typing import Callable, List

from openai.types.responses import Response

from qdrant_client.models import ScoredPoint

from archive_agent.util.format import format_file, format_time

logger = logging.getLogger(__name__)


class CliManager:
    """
    CLI manager.
    """

    VERBOSE_EMBED: bool = False
    VERBOSE_QUERY: bool = False
    VERBOSE_VISION: bool = True
    VERBOSE_RETRIEVAL: bool = True
    VERBOSE_USAGE: bool = False

    def __init__(self):
        """
        Initialize CLI manager.
        """
        pass

    @staticmethod
    def format_json(text: str) -> None:
        """
        Format text as JSON.
        :param text: Text.
        """
        try:
            data = json.loads(text)
            pretty = Pretty(data, expand_all=True)
            print(Panel(pretty, title="Structured output", border_style="white"))
        except json.JSONDecodeError:
            print(Panel(f"[white]{text}", title="Raw output", border_style="red"))

    @staticmethod
    def format_chunk(chunk: str) -> None:
        """
        Format chunk.
        :param chunk: Chunk.
        """
        print(Panel(f"[yellow]{chunk}", title="Chunk", border_style="white"))

    @staticmethod
    def format_openai_embed(callback: Callable[[], Response], chunk: str) -> Response:
        """
        Format OpenAI response of embed callback.
        :param callback: Embed callback returning OpenAI response.
        :param chunk: Chunk.
        :return: OpenAI response.
        """
        logger.info(f"Embedding...")

        if CliManager.VERBOSE_EMBED:
            CliManager.format_chunk(chunk)

        response = callback()

        if CliManager.VERBOSE_USAGE:
            logger.info(f"Used ({response.usage.total_tokens}) token(s)")

        return response

    @staticmethod
    def format_openai_query(callback: Callable[[], Response], prompt: str) -> Response:
        """
        Format OpenAI response of query callback.
        :param callback: Query callback returning OpenAI response.
        :param prompt: Prompt.
        :return: OpenAI response.
        """
        logger.info(f"Querying...")

        if CliManager.VERBOSE_QUERY:
            print(Panel(f"[red]{prompt}", title="Query", border_style="white"))

        response = callback()

        if CliManager.VERBOSE_QUERY:
            CliManager.format_json(response.output_text)

        if CliManager.VERBOSE_USAGE:
            logger.info(f"Used ({response.usage.total_tokens}) token(s)")

        return response

    @staticmethod
    def format_openai_vision(callback: Callable[[], Response]) -> Response:
        """
        Format OpenAI response of vision callback.
        :param callback: Vision callback returning OpenAI response.
        :return: OpenAI response.
        """
        logger.info(f"Image vision...")

        response = callback()

        if CliManager.VERBOSE_VISION:
            CliManager.format_json(response.output_text)

        if CliManager.VERBOSE_USAGE:
            logger.info(f"Used ({response.usage.total_tokens}) token(s)")

        return response

    @staticmethod
    def format_points(points: List[ScoredPoint]) -> None:
        """
        Format chunks of retreived points.
        :param points: Retrieved points.
        """
        for point in points:

            logger.info(
                f"({point.score * 100:.2f} %) matching chunk in {format_file(point.payload['file_path'])}"
                f" @ {format_time(point.payload['file_mtime'])}:"
            )

            if CliManager.VERBOSE_RETRIEVAL:
                CliManager.format_chunk(point.payload['chunk'])

        logger.warning(f"Found ({len(points)}) matching chunk(s)")

    @staticmethod
    def format_question(question: str) -> None:
        """
        Format question.
        :param question: Question.
        """
        print(Panel(f"[white]{question}", title="Question", border_style="red"))

    @staticmethod
    def format_answer(answer: str, warning: bool = False) -> None:
        """
        Format answer.
        :param answer: Answer.
        :param warning: Use red border if True, green otherwise.
        """
        print(Panel(f"[white]{answer}", title="Answer", border_style="red" if warning else "green"))
