# C# project structure and build process

# Define the project name
PROJECT_NAME = Morpheus

# Define the source files
CS_SOURCES = \
    betamorph.cs \
    checkcmpstem.cs \
    checkcrasis.cs \
    checkdict.cs \
    checkgenwds.cs \
    checkhalf1.cs \
    checkindecl.cs \
    checkirreg.cs \
    checknom.cs \
    checkpreverb.cs \
    checkstem.cs \
    checkstring.cs \
    checkverb.cs \
    checkword.cs \
    dictstems.cs

# Define the output directory
OUTPUT_DIR = bin

# Define the compiler
CSC = csc

# Define the compiler flags
CSC_FLAGS = -out:$(OUTPUT_DIR)/$(PROJECT_NAME).exe

# Define the build target
all: $(OUTPUT_DIR)/$(PROJECT_NAME).exe

# Define the build rule
$(OUTPUT_DIR)/$(PROJECT_NAME).exe: $(CS_SOURCES)
	$(CSC) $(CSC_FLAGS) $(CS_SOURCES)

# Define the clean target
clean:
	rm -rf $(OUTPUT_DIR)
