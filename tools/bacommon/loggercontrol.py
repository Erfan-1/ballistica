# Released under the MIT License. See LICENSE for details.
#
"""System for managing loggers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated
from dataclasses import dataclass, field

from efro.dataclassio import ioprepped, IOAttrs

if TYPE_CHECKING:
    from typing import Self


@ioprepped
@dataclass
class LoggerControlConfig:
    """A logging level configuration that applies to all loggers.

    Any loggers not explicitly contained in the configuration will be
    set to NOTSET.
    """

    # Logger names mapped to log-level values (from system logging module).
    levels: Annotated[dict[str, int], IOAttrs('l', store_default=False)] = (
        field(default_factory=dict)
    )

    def apply(self) -> None:
        """Apply the config to all Python loggers."""
        existinglognames = (
            set(['root']) | logging.root.manager.loggerDict.keys()
        )

        # First, update levels for all existing loggers.
        for logname in existinglognames:
            logger = logging.getLogger(logname)
            level = self.levels.get(logname)
            if level is None:
                level = logging.NOTSET
            logger.setLevel(level)

        # Next, assign levels to any loggers that don't exist.
        for logname, level in self.levels.items():
            if logname not in existinglognames:
                logging.getLogger(logname).setLevel(level)

    def would_make_changes(self) -> bool:
        """Return whether calling apply would change anything."""

        existinglognames = (
            set(['root']) | logging.root.manager.loggerDict.keys()
        )

        # Return True if we contain any nonexistent loggers. Even if
        # we wouldn't change their level, the fact that we'd create
        # them still counts as a difference.
        if any(
            logname not in existinglognames for logname in self.levels.keys()
        ):
            return True

        # Now go through all existing loggers and return True if we
        # would change their level.
        for logname in existinglognames:
            logger = logging.getLogger(logname)
            level = self.levels.get(logname)
            if level is None:
                level = logging.NOTSET
            if logger.level != level:
                return True

        return False

    def diff(self, baseconfig: LoggerControlConfig) -> LoggerControlConfig:
        """Return a config containing only changes compared to a base config.

        Note that this omits all NOTSET values that resolve to NOTSET in
        the base config.

        This diffed config can later be used with apply_diff() against the
        base config to recreate the state represented by self.
        """
        cls = type(self)
        config = cls()
        for loggername, level in self.levels.items():
            baselevel = baseconfig.levels.get(loggername, logging.NOTSET)
            if level != baselevel:
                config.levels[loggername] = level
        return config

    def apply_diff(
        self, diffconfig: LoggerControlConfig
    ) -> LoggerControlConfig:
        """Apply a diff config to ourself."""
        cls = type(self)

        # Create a new config (with an indepenent levels dict copy).
        config = cls(levels=dict(self.levels))

        # Overlay the diff levels dict onto our new one.
        config.levels.update(diffconfig.levels)

        # Note: we do NOT prune NOTSET values here. This is so all
        # loggers mentioned in the base config get created if we are
        # applied, even if they are assigned a default level.
        return config

    @classmethod
    def from_current_loggers(cls) -> Self:
        """Build a config from the current set of loggers."""
        lognames = ['root'] + sorted(logging.root.manager.loggerDict)
        config = cls()
        for logname in lognames:
            config.levels[logname] = logging.getLogger(logname).level
        return config
