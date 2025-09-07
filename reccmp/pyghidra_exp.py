from typing import TYPE_CHECKING
import pyghidra

# from pyghidra import GuiPyGhidraLauncher
from pyghidra import HeadlessPyGhidraLauncher

if TYPE_CHECKING:
    from ghidra.program.model.listing import Program

def main():
    print("Hi")

    # launcher = GuiPyGhidraLauncher()
    launcher = HeadlessPyGhidraLauncher()
    launcher.start()
    # TODO: Loading existing remote projects seems to be hard
    # This opens the project with a new binary file, but it requires the binary file to be specified, which we don't have in a shared project with an existing file
    # with pyghidra.open_program("../isle/legobin/LEGO1.DLL", analyze=False, project_name="isle", project_location="C:\\Users\\Jonathan\\Documents\\ghidra", program_name="pyghidra_test") as flat_api:

    #     print("Loaded")
    #     # This does not work, unlike the Ghidrathon script. Do we have the flat API actually flat?
    #     # getCurrentProgram()
    #     program: Program = flat_api.getCurrentProgram()
    #     print(program.getName())


    from ghidra.base.project import GhidraProject
    from ghidra.program.flatapi import FlatProgramAPI

    # based on the source code of pyghidra.open_program()
    project = GhidraProject.openProject("C:\\Users\\Jonathan\\Documents\\ghidra", "isle", True)
    folder = project.getRootFolder()
    files = list(folder.getFiles())
    print(files)

    program = project.openProgram("/", "LEGO1.DLL (Ghidra 11.4.2 experiment)", True)
    print(program)
    print(program.getName())

    # Nice, this actually works! I could conceivably try to run the import script from here

    from reccmp.ghidra_scripts.import_functions_and_types_from_pdb import main as importMain

    # TODO: Ideas
    # - How to get the FlatProgramApi? Is it the same as returned by project.openProgram?
    # - give optional parameter to `main` with the API
    # - store the flat program API in a global if exists (not very clean)

    api = FlatProgramAPI(program)

    importMain(api)


if __name__ == "__main__":
    main()
