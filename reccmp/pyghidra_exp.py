# from pyghidra import GuiPyGhidraLauncher
import time
from pyghidra import HeadlessPyGhidraLauncher

# Suppress linter warnings related to the fact that the header support for Ghidra is limited
# and that we cannot import Ghidra classes before Ghidra has been loaded

# pylint: disable=import-outside-toplevel
# pyright: reportMissingModuleSource=false


# TODO
# - Refactor to logging library
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
    print("Starting Ghidra...")

    # launcher = GuiPyGhidraLauncher()
    launcher = HeadlessPyGhidraLauncher()
    launcher.start()

    print("Ghidra started. Opening Ghidra project...")

    from ghidra.base.project import GhidraProject
    from ghidra.program.flatapi import FlatProgramAPI
    from ghidra.util.task import TaskMonitor
    from ghidra.framework.model import TransactionInfo
    from reccmp.ghidra_scripts.import_functions_and_types_from_pdb import main as reccmpImportMain

    # based on the source code of pyghidra.open_program()
    project = GhidraProject.openProject("C:\\Users\\Jonathan\\Documents\\ghidra", "isle", True)
    folder = project.getRootFolder()
    files = list(folder.getFiles())
    print(files)


    print("Ghidra project opened. Opening Program...")

    program = project.openProgram("/", "LEGO1.DLL (Ghidra 11.4.2 experiment)", False)
    print(program)
    print(program.getName())

    print("Program opened. Starting reccmp import...")

    # This name is irrelevant, but we have to give it some name
    transaction_name = "pyghidra-reccmp-import-script"
    # transaction = program.startTransaction(transaction_name)
    # try:
        # api = FlatProgramAPI(program)
        # reccmpImportMain(api)
    # finally:
        # Second argument: Whether to commit (True) or abort (False)
        # program.endTransaction(transaction, True)

    # TODO: Try a local file first before trying to fix the online repo
    # TODO: Look into the existing setup, maybe it does something else to address this

    # WIP: experiments trying to finish a potential transaction. Might be completely wrong
    while True:
        transaction_info = program.getCurrentTransactionInfo()
        status = transaction_info.getStatus()

        if status != TransactionInfo.Status.NOT_DONE:
            break

        time.sleep(1.0)
        print("Waiting for transaction...")
        id = int(transaction_info.getID())
        program.endTransaction(id, True)


    # WIP: Saving fails with some transaction warning
    program.save("Test file comment", TaskMonitor.DUMMY)


if __name__ == "__main__":
    main()
