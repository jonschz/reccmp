import logging
import sys

# from pyghidra import GuiPyGhidraLauncher
from pyghidra import HeadlessPyGhidraLauncher

# Suppress linter warnings related to the fact that the header support for Ghidra is limited
# and that we cannot import Ghidra classes before Ghidra has been loaded

# pylint: disable=import-outside-toplevel
# pyright: reportMissingModuleSource=false


logger = logging.getLogger(__file__)

# TODO
# - Test again if anything GUI related is possible at all
# - Load a remote project, check out and check in a remote project
#   - possibly something like
#     ```
#     repo = GhidraProject.getServerRepository(...)
#     repo.checkout(...)
#     ```
#   - set up local server for testing
#   - search API for "checkin" -> multiple candidates


def main():
    logging.root.handlers.clear()
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    # formatter = logging.Formatter("%(name)s %(levelname)-8s %(message)s") # use this to identify loggers
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logging.root.addHandler(stdout_handler)
    logging.root.level = logging.DEBUG

    logger.info("Starting import...")

    launcher = HeadlessPyGhidraLauncher()
    launcher.start()

    logger.info("Ghidra started. Opening Ghidra project...")

    from ghidra.base.project import GhidraProject
    from ghidra.program.flatapi import FlatProgramAPI
    from reccmp.ghidra_scripts.import_functions_and_types_from_pdb import (
        main as reccmpImportMain,
    )
    from ghidra.app.script import GhidraScriptUtil

    # based on the source code of pyghidra.open_program()
    project = GhidraProject.openProject(
        "C:\\Users\\Jonathan\\Documents\\ghidra",
        # "isle",
        "test-repo-2",
        True,
    )
    folder = project.getRootFolder()
    files = list(folder.getFiles())
    logger.info(files)

    logger.info("Ghidra project opened. Opening Program...")

    program = project.openProgram("/", "CONFIG.EXE", False)

    logger.info("Program opened. Starting reccmp import...")

    # Not exactly sure why this is necessary, but it can't hurt
    GhidraScriptUtil.acquireBundleHostReference()

    # This name is irrelevant, but we have to give it some name
    transaction_name = "pyghidra-reccmp-import-script"
    transaction = program.startTransaction(transaction_name)
    try:
        api = FlatProgramAPI(program)
        reccmpImportMain(api)
    finally:
        # Second argument: Whether to commit (True) or abort (False)
        program.endTransaction(transaction, True)

    # Not exactly sure why this is necessary, but it can't hurt
    GhidraScriptUtil.releaseBundleHostReference()

    # Note that `program.save()` is wrong and does not work.
    project.save(program)
    project.close(program)

    logger.info("Done!")


if __name__ == "__main__":
    main()
