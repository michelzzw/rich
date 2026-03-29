"""
Helper types, protocols, and context managers for the Rich Console.

Extracted from console.py to address the Blob/God Class antipattern
identified in TP1 static analysis (Sokrates, SIG model).
Resolves issue #1.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Type,
    Union,
    runtime_checkable,
)

from .control import Control
from .highlighter import NullHighlighter
from .measure import Measurement, measure_renderables
from .pager import Pager, SystemPager
from .screen import Screen
from .segment import Segment
from .style import Style, StyleType
from .theme import Theme, ThemeStack

if TYPE_CHECKING:
    from rich.console import Console

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

HighlighterType = Callable[[Union[str, "Text"]], "Text"]
JustifyMethod = Literal["default", "left", "center", "right", "full"]
OverflowMethod = Literal["fold", "crop", "ellipsis", "ignore"]


# ---------------------------------------------------------------------------
# NoChange sentinel
# ---------------------------------------------------------------------------

class NoChange:
    pass


NO_CHANGE = NoChange()


# ---------------------------------------------------------------------------
# ConsoleDimensions
# ---------------------------------------------------------------------------

class ConsoleDimensions(NamedTuple):
    """Size of the terminal."""

    width: int
    """The width of the console in 'cells'."""
    height: int
    """The height of the console in lines."""


# ---------------------------------------------------------------------------
# ConsoleOptions
# ---------------------------------------------------------------------------

@dataclass
class ConsoleOptions:
    """Options for __rich_console__ method."""

    size: ConsoleDimensions
    """Size of console."""
    legacy_windows: bool
    """legacy_windows: flag for legacy windows."""
    min_width: int
    """Minimum width of renderable."""
    max_width: int
    """Maximum width of renderable."""
    is_terminal: bool
    """True if the target is a terminal, otherwise False."""
    encoding: str
    """Encoding of terminal."""
    max_height: int
    """Height of container (starts as terminal)"""
    justify: Optional[JustifyMethod] = None
    """Justify value override for renderable."""
    overflow: Optional[OverflowMethod] = None
    """Overflow value override for renderable."""
    no_wrap: Optional[bool] = False
    """Disable wrapping for text."""
    highlight: Optional[bool] = None
    """Highlight override for render_str."""
    markup: Optional[bool] = None
    """Enable markup when rendering strings."""
    height: Optional[int] = None

    @property
    def ascii_only(self) -> bool:
        """Check if renderables should use ascii only."""
        return not self.encoding.startswith("utf")

    def copy(self) -> "ConsoleOptions":
        """Return a copy of the options.

        Returns:
            ConsoleOptions: a copy of self.
        """
        options: ConsoleOptions = ConsoleOptions.__new__(ConsoleOptions)
        options.__dict__ = self.__dict__.copy()
        return options

    def update(
        self,
        *,
        width: Union[int, NoChange] = NO_CHANGE,
        min_width: Union[int, NoChange] = NO_CHANGE,
        max_width: Union[int, NoChange] = NO_CHANGE,
        justify: Union[Optional[JustifyMethod], NoChange] = NO_CHANGE,
        overflow: Union[Optional[OverflowMethod], NoChange] = NO_CHANGE,
        no_wrap: Union[Optional[bool], NoChange] = NO_CHANGE,
        highlight: Union[Optional[bool], NoChange] = NO_CHANGE,
        markup: Union[Optional[bool], NoChange] = NO_CHANGE,
        height: Union[Optional[int], NoChange] = NO_CHANGE,
    ) -> "ConsoleOptions":
        """Update values, return a copy."""
        options = self.copy()
        if not isinstance(width, NoChange):
            options.min_width = options.max_width = max(0, width)
        if not isinstance(min_width, NoChange):
            options.min_width = min_width
        if not isinstance(max_width, NoChange):
            options.max_width = max_width
        if not isinstance(justify, NoChange):
            options.justify = justify
        if not isinstance(overflow, NoChange):
            options.overflow = overflow
        if not isinstance(no_wrap, NoChange):
            options.no_wrap = no_wrap
        if not isinstance(highlight, NoChange):
            options.highlight = highlight
        if not isinstance(markup, NoChange):
            options.markup = markup
        if not isinstance(height, NoChange):
            if height is not None:
                options.max_height = height
            options.height = None if height is None else max(0, height)
        return options

    def update_width(self, width: int) -> "ConsoleOptions":
        """Update just the width, return a copy.

        Args:
            width (int): New width (sets both min_width and max_width)

        Returns:
            ~ConsoleOptions: New console options instance.
        """
        options = self.copy()
        options.min_width = options.max_width = max(0, width)
        return options

    def update_height(self, height: int) -> "ConsoleOptions":
        """Update the height, and return a copy.

        Args:
            height (int): New height

        Returns:
            ~ConsoleOptions: New Console options instance.
        """
        options = self.copy()
        options.max_height = options.height = height
        return options

    def reset_height(self) -> "ConsoleOptions":
        """Return a copy of the options with height set to ``None``.

        Returns:
            ~ConsoleOptions: New console options instance.
        """
        options = self.copy()
        options.height = None
        return options

    def update_dimensions(self, width: int, height: int) -> "ConsoleOptions":
        """Update the width and height, and return a copy.

        Args:
            width (int): New width (sets both min_width and max_width).
            height (int): New height.

        Returns:
            ~ConsoleOptions: New console options instance.
        """
        options = self.copy()
        options.min_width = options.max_width = max(0, width)
        options.height = options.max_height = height
        return options


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

@runtime_checkable
class RichCast(Protocol):
    """An object that may be 'cast' to a console renderable."""

    def __rich__(
        self,
    ) -> Union["ConsoleRenderable", "RichCast", str]:  # pragma: no cover
        ...


@runtime_checkable
class ConsoleRenderable(Protocol):
    """An object that supports the console protocol."""

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# Render type aliases
# ---------------------------------------------------------------------------

# A type that may be rendered by Console.
RenderableType = Union[ConsoleRenderable, RichCast, str]
"""A string or any object that may be rendered by Rich."""

# The result of calling a __rich_console__ method.
RenderResult = Iterable[Union[RenderableType, Segment]]

_null_highlighter = NullHighlighter()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CaptureError(Exception):
    """An error in the Capture context manager."""


# ---------------------------------------------------------------------------
# Renderables
# ---------------------------------------------------------------------------

class NewLine:
    """A renderable to generate new line(s)"""

    def __init__(self, count: int = 1) -> None:
        self.count = count

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Iterable[Segment]:
        yield Segment("\n" * self.count)


class ScreenUpdate:
    """Render a list of lines at a given offset."""

    def __init__(self, lines: List[List[Segment]], x: int, y: int) -> None:
        self._lines = lines
        self.x = x
        self.y = y

    def __rich_console__(
        self, console: "Console", options: ConsoleOptions
    ) -> RenderResult:
        x = self.x
        move_to = Control.move_to
        for offset, line in enumerate(self._lines, self.y):
            yield move_to(x, offset)
            yield from line


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------

class Capture:
    """Context manager to capture the result of printing to the console.
    See :meth:`~rich.console.Console.capture` for how to use.

    Args:
        console (Console): A console instance to capture output.
    """

    def __init__(self, console: "Console") -> None:
        self._console = console
        self._result: Optional[str] = None

    def __enter__(self) -> "Capture":
        self._console.begin_capture()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._result = self._console.end_capture()

    def get(self) -> str:
        """Get the result of the capture."""
        if self._result is None:
            raise CaptureError(
                "Capture result is not available until context manager exits."
            )
        return self._result


class ThemeContext:
    """A context manager to use a temporary theme. See :meth:`~rich.console.Console.use_theme` for usage."""

    def __init__(self, console: "Console", theme: Theme, inherit: bool = True) -> None:
        self.console = console
        self.theme = theme
        self.inherit = inherit

    def __enter__(self) -> "ThemeContext":
        self.console.push_theme(self.theme)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.console.pop_theme()


class PagerContext:
    """A context manager that 'pages' content. See :meth:`~rich.console.Console.pager` for usage."""

    def __init__(
        self,
        console: "Console",
        pager: Optional[Pager] = None,
        styles: bool = False,
        links: bool = False,
    ) -> None:
        self._console = console
        self.pager = SystemPager() if pager is None else pager
        self.styles = styles
        self.links = links

    def __enter__(self) -> "PagerContext":
        self._console._enter_buffer()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type is None:
            with self._console._lock:
                buffer: List[Segment] = self._console._buffer[:]
                del self._console._buffer[:]
                segments: Iterable[Segment] = buffer
                if not self.styles:
                    segments = Segment.strip_styles(segments)
                elif not self.links:
                    segments = Segment.strip_links(segments)
                content = self._console._render_buffer(segments)
            self.pager.show(content)
        self._console._exit_buffer()


class ScreenContext:
    """A context manager that enables an alternative screen. See :meth:`~rich.console.Console.screen` for usage."""

    def __init__(
        self, console: "Console", hide_cursor: bool, style: StyleType = ""
    ) -> None:
        self.console = console
        self.hide_cursor = hide_cursor
        self.screen = Screen(style=style)
        self._changed = False

    def update(
        self, *renderables: RenderableType, style: Optional[StyleType] = None
    ) -> None:
        """Update the screen.

        Args:
            renderable (RenderableType, optional): Optional renderable to replace current renderable,
                or None for no change. Defaults to None.
            style: (Style, optional): Replacement style, or None for no change. Defaults to None.
        """
        if renderables:
            self.screen.renderable = (
                Group(*renderables) if len(renderables) > 1 else renderables[0]
            )
        if style is not None:
            self.screen.style = style
        self.console.print(self.screen, end="")

    def __enter__(self) -> "ScreenContext":
        self._changed = self.console.set_alt_screen(True)
        if self._changed and self.hide_cursor:
            self.console.show_cursor(False)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self._changed:
            self.console.set_alt_screen(False)
            if self.hide_cursor:
                self.console.show_cursor(True)


# ---------------------------------------------------------------------------
# Group and group() decorator
# ---------------------------------------------------------------------------

class Group:
    """Takes a group of renderables and returns a renderable object that renders the group.

    Args:
        renderables (Iterable[RenderableType]): An iterable of renderable objects.
        fit (bool, optional): Fit dimension of group to contents, or fill available space. Defaults to True.
    """

    def __init__(self, *renderables: "RenderableType", fit: bool = True) -> None:
        self._renderables = renderables
        self.fit = fit
        self._render: Optional[List[RenderableType]] = None

    @property
    def renderables(self) -> List["RenderableType"]:
        if self._render is None:
            self._render = list(self._renderables)
        return self._render

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        if self.fit:
            return measure_renderables(console, options, self.renderables)
        else:
            return Measurement(options.max_width, options.max_width)

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> RenderResult:
        yield from self.renderables


def group(fit: bool = True) -> Callable[..., Callable[..., Group]]:
    """A decorator that turns an iterable of renderables in to a group.

    Args:
        fit (bool, optional): Fit dimension of group to contents, or fill available space. Defaults to True.
    """

    def decorator(
        method: Callable[..., Iterable[RenderableType]],
    ) -> Callable[..., Group]:
        """Convert a method that returns an iterable of renderables in to a Group."""

        @wraps(method)
        def _replace(*args: Any, **kwargs: Any) -> Group:
            renderables = method(*args, **kwargs)
            return Group(*renderables, fit=fit)

        return _replace

    return decorator


# ---------------------------------------------------------------------------
# Thread-local console state
# ---------------------------------------------------------------------------

@dataclass
class ConsoleThreadLocals(threading.local):
    """Thread local values for Console context."""

    theme_stack: ThemeStack
    buffer: List[Segment] = field(default_factory=list)
    buffer_index: int = 0


# ---------------------------------------------------------------------------
# RenderHook
# ---------------------------------------------------------------------------

class RenderHook(ABC):
    """Provides hooks in to the render process."""

    @abstractmethod
    def process_renderables(
        self, renderables: List[ConsoleRenderable]
    ) -> List[ConsoleRenderable]:
        """Called with a list of objects to render.

        This method can return a new list of renderables, or modify and return the same list.

        Args:
            renderables (List[ConsoleRenderable]): A number of renderable objects.

        Returns:
            List[ConsoleRenderable]: A replacement list of renderables.
        """
