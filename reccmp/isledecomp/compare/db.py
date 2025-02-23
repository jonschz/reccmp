"""Wrapper for database (here an in-memory sqlite database) that collects the
addresses/symbols that we want to compare between the original and recompiled binaries."""

import sqlite3
import logging
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, List, Optional
from reccmp.isledecomp.types import SymbolType
from reccmp.isledecomp.cvdump.demangler import get_vtordisp_name

_SETUP_SQL = """
    CREATE TABLE `symbols` (
        compare_type int,
        orig_addr int unique,
        recomp_addr int unique,
        name text,
        decorated_name text,
        size int
    );

    CREATE TABLE `match_options` (
        addr int not null,
        name text not null,
        value text,
        primary key (addr, name)
    ) without rowid;

    CREATE VIEW IF NOT EXISTS `match_info`
    (compare_type, orig_addr, recomp_addr, name, size) AS
        SELECT compare_type, orig_addr, recomp_addr, name, size
        FROM `symbols`
        ORDER BY orig_addr NULLS LAST;

    CREATE INDEX `symbols_na` ON `symbols` (name);
"""


SymbolTypeLookup: dict[int, str] = {
    value: name for name, value in SymbolType.__members__.items()
}


@dataclass
class MatchInfo:
    compare_type: Optional[int]
    orig_addr: Optional[int]
    recomp_addr: Optional[int]
    name: Optional[str]
    size: Optional[int]

    def match_name(self) -> Optional[str]:
        """Combination of the name and compare type.
        Intended for name substitution in the diff. If there is a diff,
        it will be more obvious what this symbol indicates."""
        if self.name is None:
            return None

        ctype = SymbolTypeLookup.get(self.compare_type or -1, "UNK")
        name = repr(self.name) if self.compare_type == SymbolType.STRING else self.name
        return f"{name} ({ctype})"

    def offset_name(self, ofs: int) -> Optional[str]:
        if self.name is None:
            return None

        return f"{self.name}+{ofs} (OFFSET)"


def matchinfo_factory(_, row):
    return MatchInfo(*row)


logger = logging.getLogger(__name__)


class CompareDb:
    # pylint: disable=too-many-public-methods
    def __init__(self):
        self._db = sqlite3.connect(":memory:")
        self._db.executescript(_SETUP_SQL)

    def set_orig_symbol(
        self,
        addr: int,
        compare_type: Optional[SymbolType],
        name: Optional[str],
        size: Optional[int],
    ):
        # Ignore collisions here.
        self._db.execute(
            "INSERT or ignore INTO `symbols` (orig_addr, compare_type, name, size) VALUES (?,?,?,?)",
            (addr, compare_type, name, size),
        )

    def set_recomp_symbol(
        self,
        addr: int,
        compare_type: Optional[SymbolType],
        name: Optional[str],
        decorated_name: Optional[str],
        size: Optional[int],
    ):
        # Ignore collisions here. The same recomp address can have
        # multiple names (e.g. _strlwr and __strlwr)

        self._db.execute(
            "INSERT or ignore INTO `symbols` (recomp_addr, compare_type, name, decorated_name, size) VALUES (?,?,?,?,?)",
            (addr, compare_type, name, decorated_name, size),
        )

    def bulk_cvdump_insert(self, rows: Iterable[dict[str, Any]]):
        self._db.executemany(
            """INSERT or ignore INTO `symbols` (recomp_addr, compare_type, name, decorated_name, size)
            VALUES (:addr, :type, :name, :symbol, :size)""",
            rows,
        )

    def bulk_array_insert(self, rows: Iterable[dict[str, Any]]):
        self._db.executemany(
            """INSERT or ignore INTO `symbols` (orig_addr, recomp_addr, name)
            VALUES (:orig, :recomp, :name)""",
            rows,
        )

    def get_unmatched_strings(self) -> List[str]:
        """Return any strings not already identified by STRING markers."""

        cur = self._db.execute(
            "SELECT name FROM `symbols` WHERE compare_type = ? AND orig_addr IS NULL",
            (SymbolType.STRING,),
        )

        return [string for (string,) in cur.fetchall()]

    def get_all(self) -> Iterator[MatchInfo]:
        cur = self._db.execute("SELECT * FROM `match_info`")
        cur.row_factory = matchinfo_factory
        yield from cur

    def get_matches(self) -> Iterator[MatchInfo]:
        cur = self._db.execute(
            """SELECT * FROM `match_info`
            WHERE orig_addr IS NOT NULL
            AND recomp_addr IS NOT NULL
            """,
        )
        cur.row_factory = matchinfo_factory
        yield from cur

    def get_one_match(self, addr: int) -> Optional[MatchInfo]:
        cur = self._db.execute(
            """SELECT * FROM `match_info`
            WHERE orig_addr = ?
            AND recomp_addr IS NOT NULL
            """,
            (addr,),
        )
        cur.row_factory = matchinfo_factory
        return cur.fetchone()

    def _get_closest_orig(self, addr: int) -> Optional[int]:
        for (value,) in self._db.execute(
            "SELECT orig_addr FROM symbols WHERE ? >= orig_addr ORDER BY orig_addr desc LIMIT 1",
            (addr,),
        ):
            return value

        return None

    def _get_closest_recomp(self, addr: int) -> Optional[int]:
        for (value,) in self._db.execute(
            "SELECT recomp_addr FROM symbols WHERE ? >= recomp_addr ORDER BY recomp_addr desc LIMIT 1",
            (addr,),
        ):
            return value

        return None

    def get_by_orig(self, orig: int, exact: bool = True) -> Optional[MatchInfo]:
        addr = self._get_closest_orig(orig)
        if addr is None or exact and orig != addr:
            return None

        cur = self._db.execute(
            "SELECT * FROM `match_info` WHERE orig_addr = ?",
            (addr,),
        )
        cur.row_factory = matchinfo_factory
        return cur.fetchone()

    def get_by_recomp(self, recomp: int, exact: bool = True) -> Optional[MatchInfo]:
        addr = self._get_closest_recomp(recomp)
        if addr is None or exact and recomp != addr:
            return None

        cur = self._db.execute(
            "SELECT * FROM `match_info` WHERE recomp_addr = ?",
            (addr,),
        )
        cur.row_factory = matchinfo_factory
        return cur.fetchone()

    def get_matches_by_type(self, compare_type: SymbolType) -> Iterator[MatchInfo]:
        cur = self._db.execute(
            """SELECT * FROM `match_info`
            WHERE compare_type = ?
            AND orig_addr IS NOT NULL
            AND recomp_addr IS NOT NULL
            """,
            (compare_type,),
        )
        cur.row_factory = matchinfo_factory
        yield from cur

    def _orig_used(self, addr: int) -> bool:
        cur = self._db.execute("SELECT 1 FROM symbols WHERE orig_addr = ?", (addr,))
        return cur.fetchone() is not None

    def _recomp_used(self, addr: int) -> bool:
        cur = self._db.execute("SELECT 1 FROM symbols WHERE recomp_addr = ?", (addr,))
        return cur.fetchone() is not None

    def set_pair(
        self, orig: int, recomp: int, compare_type: Optional[SymbolType] = None
    ) -> bool:
        if self._orig_used(orig):
            logger.debug("Original address %s not unique!", hex(orig))
            return False

        cur = self._db.execute(
            "UPDATE `symbols` SET orig_addr = ?, compare_type = ? WHERE recomp_addr = ?",
            (orig, compare_type, recomp),
        )

        return cur.rowcount > 0

    def set_pair_tentative(
        self, orig: int, recomp: int, compare_type: Optional[SymbolType] = None
    ) -> bool:
        """Declare a match for the original and recomp addresses given, but only if:
        1. The original address is not used elsewhere (as with set_pair)
        2. The recomp address has not already been matched
        If the compare_type is given, update this also, but only if NULL in the db.

        The purpose here is to set matches found via some automated analysis
        but to not overwrite a match provided by the human operator."""
        if self._orig_used(orig):
            # Probable and expected situation. Just ignore it.
            return False

        cur = self._db.execute(
            """UPDATE `symbols`
            SET orig_addr = ?, compare_type = coalesce(compare_type, ?)
            WHERE recomp_addr = ?
            AND orig_addr IS NULL""",
            (orig, compare_type, recomp),
        )

        return cur.rowcount > 0

    def set_function_pair(self, orig: int, recomp: int) -> bool:
        """For lineref match or _entry"""
        return self.set_pair(orig, recomp, SymbolType.FUNCTION)

    def create_orig_thunk(self, addr: int, name: str) -> bool:
        """Create a thunk function reference using the orig address.
        We are here because we have a match on the thunked function,
        but it is not thunked in the recomp build."""

        if self._orig_used(addr):
            return False

        thunk_name = f"Thunk of '{name}'"

        # Assuming relative jump instruction for thunks (5 bytes)
        cur = self._db.execute(
            """INSERT INTO `symbols`
            (orig_addr, compare_type, name, size)
            VALUES (?,?,?,?)""",
            (addr, SymbolType.FUNCTION, thunk_name, 5),
        )

        return cur.rowcount > 0

    def create_recomp_thunk(self, addr: int, name: str) -> bool:
        """Create a thunk function reference using the recomp address.
        We start from the recomp side for this because we are guaranteed
        to have full information from the PDB. We can use a regular function
        match later to pull in the orig address."""

        if self._recomp_used(addr):
            return False

        thunk_name = f"Thunk of '{name}'"

        # Assuming relative jump instruction for thunks (5 bytes)
        cur = self._db.execute(
            """INSERT INTO `symbols`
            (recomp_addr, compare_type, name, size)
            VALUES (?,?,?,?)""",
            (addr, SymbolType.FUNCTION, thunk_name, 5),
        )

        return cur.rowcount > 0

    def _set_opt_bool(self, addr: int, option: str, enabled: bool = True):
        if enabled:
            self._db.execute(
                """INSERT OR IGNORE INTO `match_options`
                (addr, name)
                VALUES (?, ?)""",
                (addr, option),
            )
        else:
            self._db.execute(
                """DELETE FROM `match_options` WHERE addr = ? AND name = ?""",
                (addr, option),
            )

    def mark_stub(self, orig: int):
        self._set_opt_bool(orig, "stub")

    def skip_compare(self, orig: int):
        self._set_opt_bool(orig, "skip")

    def get_match_options(self, addr: int) -> Optional[dict[str, Any]]:
        cur = self._db.execute(
            """SELECT name, value FROM `match_options` WHERE addr = ?""", (addr,)
        )

        return {
            option: value if value is not None else True
            for (option, value) in cur.fetchall()
        }

    def is_vtordisp(self, recomp_addr: int) -> bool:
        """Check whether this function is a vtordisp based on its
        decorated name. If its demangled name is missing the vtordisp
        indicator, correct that."""
        row = self._db.execute(
            """SELECT name, decorated_name
            FROM `symbols`
            WHERE recomp_addr = ?""",
            (recomp_addr,),
        ).fetchone()

        if row is None:
            return False

        (name, decorated_name) = row
        if "`vtordisp" in name:
            return True

        if decorated_name is None:
            # happens in debug builds, e.g. for "Thunk of 'LegoAnimActor::ClassName'"
            return False

        new_name = get_vtordisp_name(decorated_name)
        if new_name is None:
            return False

        self._db.execute(
            """UPDATE `symbols`
            SET name = ?
            WHERE recomp_addr = ?""",
            (new_name, recomp_addr),
        )

        return True

    def _find_potential_match(
        self, name: str, compare_type: SymbolType
    ) -> Optional[int]:
        """Name lookup"""
        match_decorate = compare_type != SymbolType.STRING and name.startswith("?")
        # If the index on orig_addr is unique, sqlite will prefer to use it over the name index.
        # But this index will not help if we are checking for NULL, so we exclude it
        # by adding the plus sign (Reference: https://www.sqlite.org/optoverview.html#uplus)
        if match_decorate:
            sql = """
            SELECT recomp_addr
            FROM `symbols`
            WHERE +orig_addr IS NULL
            AND decorated_name = ?
            AND (compare_type IS NULL OR compare_type = ?)
            LIMIT 1
            """
        else:
            sql = """
            SELECT recomp_addr
            FROM `symbols`
            WHERE +orig_addr IS NULL
            AND name = ?
            AND (compare_type IS NULL OR compare_type = ?)
            LIMIT 1
            """

        row = self._db.execute(sql, (name, compare_type)).fetchone()
        return row[0] if row is not None else None

    def _match_on(self, compare_type: SymbolType, addr: int, name: str) -> bool:
        # Update the compare_type here too since the marker tells us what we should do

        # Truncate the name to 255 characters. It will not be possible to match a name
        # longer than that because MSVC truncates the debug symbols to this length.
        # See also: warning C4786.
        name = name[:255]

        logger.debug("Looking for %s %s", compare_type.name.lower(), name)
        recomp_addr = self._find_potential_match(name, compare_type)
        if recomp_addr is None:
            return False

        return self.set_pair(addr, recomp_addr, compare_type)

    def get_next_orig_addr(self, addr: int) -> Optional[int]:
        """Return the original address (matched or not) that follows
        the one given. If our recomp function size would cause us to read
        too many bytes for the original function, we can adjust it."""
        result = self._db.execute(
            """SELECT orig_addr
            FROM `symbols`
            WHERE orig_addr > ?
            ORDER BY orig_addr
            LIMIT 1""",
            (addr,),
        ).fetchone()

        return result[0] if result is not None else None

    def match_function(self, addr: int, name: str) -> bool:
        did_match = self._match_on(SymbolType.FUNCTION, addr, name)
        if not did_match:
            logger.error("Failed to find function symbol with name: %s", name)

        return did_match

    def match_vtable(
        self, addr: int, name: str, base_class: Optional[str] = None
    ) -> bool:
        # Set up our potential match names
        bare_vftable = f"{name}::`vftable'"
        for_name = base_class if base_class is not None else name
        for_vftable = f"{name}::`vftable'{{for `{for_name}'}}"

        # Try to match on the "vftable for X first"
        recomp_addr = self._find_potential_match(for_vftable, SymbolType.VTABLE)
        if recomp_addr is not None:
            return self.set_pair(addr, recomp_addr, SymbolType.VTABLE)

        # Only allow a match against "Class:`vftable'"
        # if this is the derived class.
        if base_class is None or base_class == name:
            recomp_addr = self._find_potential_match(bare_vftable, SymbolType.VTABLE)
            if recomp_addr is not None:
                return self.set_pair(addr, recomp_addr, SymbolType.VTABLE)

        logger.error("Failed to find vtable for class: %s", name)
        return False

    def match_static_variable(
        self, addr: int, variable_name: str, function_addr: int
    ) -> bool:
        """Matching a static function variable by combining the variable name
        with the decorated (mangled) name of its parent function."""

        result = self._db.execute(
            "SELECT name, decorated_name FROM `symbols` WHERE orig_addr = ?",
            (function_addr,),
        ).fetchone()

        if result is None:
            logger.error("No function for static variable: %s", variable_name)
            return False

        # Get the friendly name for the "failed to match" error message
        (function_name, function_symbol) = result

        # If the static variable has a symbol, it will contain the parent function's symbol.
        # e.g. Static variable "g_startupDelay" from function "IsleApp::Tick"
        # The function symbol is:                    "?Tick@IsleApp@@QAEXH@Z"
        # The variable symbol is: "?g_startupDelay@?1??Tick@IsleApp@@QAEXH@Z@4HA"
        for (recomp_addr,) in self._db.execute(
            """SELECT recomp_addr FROM symbols
            WHERE orig_addr IS NULL
            AND (compare_type = ? OR compare_type IS NULL)
            AND decorated_name LIKE '%' || ? || '%' || ? || '%'""",
            (SymbolType.DATA, variable_name, function_symbol),
        ):
            return self.set_pair(addr, recomp_addr, SymbolType.DATA)

        logger.error(
            "Failed to match static variable %s from function %s",
            variable_name,
            function_name,
        )

        return False

    def match_variable(self, addr: int, name: str) -> bool:
        did_match = self._match_on(SymbolType.DATA, addr, name) or self._match_on(
            SymbolType.POINTER, addr, name
        )
        if not did_match:
            logger.error("Failed to find variable: %s", name)

        return did_match

    def match_string(self, addr: int, value: str) -> bool:
        did_match = self._match_on(SymbolType.STRING, addr, value)
        if not did_match:
            escaped = repr(value)
            logger.error("Failed to find string: %s", escaped)

        return did_match
