# Compiler options.
CC = gcc
WINDRES=windres

# Game version to build: 115 = 1.0, 118 = 1.3.
PROTOCOL=115
# PLUS=1 builds the CoD2 1.3 Plus server, which takes only the Plus client
# (docs/architecture/plus-protocol.md); it is a 1.3 build.
PLUS=0
ifeq ($(PLUS),1)
ifneq ($(origin PROTOCOL),file)
ifneq ($(PROTOCOL),118)
$(error PLUS=1 is a 1.3 build: leave PROTOCOL out or set it to 118)
endif
endif
override PROTOCOL=118
else ifneq ($(PLUS),0)
$(error PLUS must be 0 or 1)
endif
# CPU architecture: x64 (64-bit) or x86 (32-bit). Windows is 32-bit only.
ifeq ($(OS),Windows_NT)
ARCH=x86
else
ARCH=x64
endif

CFLAGS=-fno-pie -O1 -fno-omit-frame-pointer -DNDEBUG -Wformat -DPROTOCOL_VERSION=$(PROTOCOL) -MMD -MP
ifeq ($(PLUS),1)
CFLAGS+=-DCOD2_PLUS
endif
LFLAGS=-no-pie
ifneq ($(ARCH),arm64)
CFLAGS+=-mfpmath=387
endif
# Cheap protection against buffer overflows. The reversed code casts between
# types and relies on signed overflow wrapping, which -fno-strict-aliasing and
# -fwrapv keep safe if the optimization level is ever raised.
CFLAGS+=-fstack-protector-strong -D_FORTIFY_SOURCE=2 -fno-strict-aliasing -fwrapv
# FORTIFY marks write() and the like; the unchecked calls are in the crash
# handler and console output, where there is nothing to do on failure.
CFLAGS+=-Wno-unused-result

ifeq ($(OS),Windows_NT)
ifneq ($(ARCH),x86)
$(error The Windows build is 32-bit only)
endif
LLIBS=-static -mwindows -lstdc++ -lws2_32 -lwinmm
else
ifeq ($(ARCH),x86)
# Force a 32-bit build on 64-bit hosts (needs gcc-multilib and g++-multilib).
CFLAGS+=-m32
LFLAGS+=-m32
else ifeq ($(ARCH),x64)
CFLAGS+=-m64
LFLAGS+=-m64
else ifeq ($(ARCH),arm64)
# The reversed code expects x86's signed char; no FMA, which rounds differently than x87.
CFLAGS+=-fsigned-char -ffp-contract=off
else
$(error ARCH must be x86, x64 or arm64)
endif
# Without 64-bit file offsets and inodes a 32-bit binary cannot list or open files
# on file systems with large inode numbers (Windows drives under WSL, big XFS volumes).
CFLAGS+=-D_FILE_OFFSET_BITS=64
LLIBS=-lm -lpthread -lstdc++ -ldl
# Read-only relocations, so an overflow cannot redirect calls through the GOT.
LFLAGS+=-Wl,-z,relro,-z,now
endif

# Setup binary names.
ifeq ($(OS),Windows_NT)
BIN_NAME=cod2rev_win32
BIN_EXT=.exe
else
BIN_NAME=cod2rev_lnxded
BIN_EXT=
endif

# Setup directory names.
BIN_DIR=bin
# Empty for the 32-bit build, whose object folders and stamps are older than ARCH.
ifeq ($(ARCH),x86)
BUILD_ARCH=
else
BUILD_ARCH=_$(ARCH)
endif
# The Plus build keeps its own objects and stamp too.
ifeq ($(PLUS),1)
BUILD_ARCH:=$(BUILD_ARCH)_plus
endif
# Each platform and game version keeps its own objects, so they can be built side by side.
OBJ_ROOT=obj
OBJ_DIR=$(OBJ_ROOT)/$(BIN_NAME)_$(PROTOCOL)$(BUILD_ARCH)
# Records which game version and architecture the binary in bin/ was built for.
BUILD_STAMP=$(BIN_DIR)/.$(BIN_NAME).build
SRC_DIR=src

LINUX_DIR=$(SRC_DIR)/unix
WIN32_DIR=$(SRC_DIR)/win32
ZLIB_DIR=$(SRC_DIR)/zlib

# Source dirs
BGAME_DIR=$(SRC_DIR)/bgame
GAME_DIR=$(SRC_DIR)/game
QCOMMON_DIR=$(SRC_DIR)/qcommon
SCR_DIR=$(SRC_DIR)/script
SERVER_DIR=$(SRC_DIR)/server
STRINGED_DIR=$(SRC_DIR)/stringed
UNIVERSAL_DIR=$(SRC_DIR)/universal
XANIM_DIR=$(SRC_DIR)/xanim

# Libcod stuff
WITH_LIBCOD=true
WITH_MYSQL=false
WITH_SQLITE=true
WITH_SPEEX=true
# httpFetch and webSocket*, with Mbed TLS (src/libcod/mbedtls) for https:// and wss://
WITH_HTTP=true

ifeq ($(WITH_LIBCOD),true)
LIBCOD_SETTINGS=-D LIBCOD
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_BOTS=1
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_ENTITY=1
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_EXEC=1
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_GRAPH=1
ifeq ($(WITH_HTTP),true)
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_HTTP=1
endif
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_JSON=1
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_LEVEL=1
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_MEMORY=1
ifeq ($(WITH_MYSQL),true)
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_MYSQL=1
endif
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_PLAYER=1
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_RATELIMITER=1
ifeq ($(WITH_SQLITE),true)
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_SQLITE=1
endif
ifeq ($(WITH_SPEEX),true)
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_SPEEX=1 -I$(SRC_DIR)/libcod/speex/include
endif
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_UTILS=1
LIBCOD_SETTINGS+=-D LIBCOD_COMPILE_WEAPONS=1
endif

ifeq ($(WITH_LIBCOD),true)
ifeq ($(WITH_MYSQL),true)
ifeq ($(OS),Windows_NT)
MYSQL_COPY_CMD=xcopy $(SRC_DIR)\libcod\mysql\windows\lib\libmysql.dll $(BIN_DIR) /Y
LLIBS+=$(SRC_DIR)/libcod/mysql/windows/lib/libmysql.lib
else
# The system's client library: MariaDB Connector/C (libmariadb-dev) or MySQL's
# (libmysqlclient-dev), as their config tool reports it. Distributions ship it
# 64-bit only, so ARCH=x86 usually cannot use it; MYSQL_LIBS=... overrides it.
MYSQL_LIBS?=$(shell mariadb_config --libs 2>/dev/null || mysql_config --libs 2>/dev/null || echo -lmysqlclient)
LLIBS+=$(MYSQL_LIBS)
endif
endif
LIBCOD_DIR=$(SRC_DIR)/libcod
LIBCOD_SOURCES=$(wildcard $(LIBCOD_DIR)/*.cpp)
LIBCOD_OBJ=$(patsubst $(LIBCOD_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(LIBCOD_SOURCES))
YYJSON_DIR=$(SRC_DIR)/libcod/yyjson
YYJSON_SOURCES=$(wildcard $(YYJSON_DIR)/*.c)
YYJSON_OBJ=$(patsubst $(YYJSON_DIR)/%.c,$(OBJ_DIR)/%.o,$(YYJSON_SOURCES))
ifeq ($(WITH_SPEEX),true)
SPEEX_DIR=$(SRC_DIR)/libcod/speex
SPEEX_SOURCES=$(wildcard $(SPEEX_DIR)/libspeex/*.c)
SPEEX_OBJ=$(patsubst $(SPEEX_DIR)/libspeex/%.c,$(OBJ_DIR)/%.o,$(SPEEX_SOURCES))
endif
ifeq ($(WITH_SQLITE),true)
SQLITE_DIR=$(SRC_DIR)/libcod/sqlite
SQLITE_SOURCES=$(wildcard $(SQLITE_DIR)/*.c)
SQLITE_OBJ=$(patsubst $(SQLITE_DIR)/%.c,$(OBJ_DIR)/%.o,$(SQLITE_SOURCES))
endif
ifeq ($(WITH_HTTP),true)
MBEDTLS_DIR=$(SRC_DIR)/libcod/mbedtls
MBEDTLS_SOURCES=$(wildcard $(MBEDTLS_DIR)/library/*.c)
# In their own folder: several names (cipher, platform, sha1...) are generic.
MBEDTLS_OBJ=$(patsubst $(MBEDTLS_DIR)/library/%.c,$(OBJ_DIR)/mbedtls/%.o,$(MBEDTLS_SOURCES))
MBEDTLS_FLAGS=-I$(MBEDTLS_DIR) -I$(MBEDTLS_DIR)/include -DMBEDTLS_CONFIG_FILE=\"cod2rev_mbedtls_config.h\"
ifeq ($(ARCH),x64)
# On x86-64 Mbed TLS only builds AES-NI with these; it still checks the CPU at run time.
MBEDTLS_FLAGS+=-maes -mpclmul
endif
ifeq ($(OS),Windows_NT)
# BCryptGenRandom for the entropy source, the system certificate store for the CA list
LLIBS+=-lbcrypt -lcrypt32
endif
endif
endif

# Target files
TARGET=$(addprefix $(BIN_DIR)/,$(BIN_NAME)$(BIN_EXT))

# C files
BGAME_SOURCES=$(wildcard $(BGAME_DIR)/*.cpp)
GAME_SOURCES=$(wildcard $(GAME_DIR)/*.cpp)
QCOMMON_SOURCES=$(wildcard $(QCOMMON_DIR)/*.cpp)
SCR_SOURCES=$(wildcard $(SCR_DIR)/*.cpp)
SERVER_SOURCES=$(wildcard $(SERVER_DIR)/*.cpp)
STRINGED_SOURCES=$(wildcard $(STRINGED_DIR)/*.cpp)
UNIVERSAL_SOURCES=$(wildcard $(UNIVERSAL_DIR)/*.cpp)
XANIM_SOURCES=$(wildcard $(XANIM_DIR)/*.cpp)
LINUX_SOURCES=$(wildcard $(LINUX_DIR)/*.cpp)
WIN32_SOURCES=$(wildcard $(WIN32_DIR)/*.cpp)
WIN32_RESOURCES=$(wildcard $(WIN32_DIR)/*.rc)
ZLIB_SOURCES=$(wildcard $(ZLIB_DIR)/*.c)

# Object files.
BGAME_OBJ=$(patsubst $(BGAME_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(BGAME_SOURCES))
GAME_OBJ=$(patsubst $(GAME_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(GAME_SOURCES))
QCOMMON_OBJ=$(patsubst $(QCOMMON_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(QCOMMON_SOURCES))
SCR_OBJ=$(patsubst $(SCR_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(SCR_SOURCES))
SERVER_OBJ=$(patsubst $(SERVER_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(SERVER_SOURCES))
STRINGED_OBJ=$(patsubst $(STRINGED_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(STRINGED_SOURCES))
UNIVERSAL_OBJ=$(patsubst $(UNIVERSAL_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(UNIVERSAL_SOURCES))
XANIM_OBJ=$(patsubst $(XANIM_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(XANIM_SOURCES))

# Platform specific lists
ifeq ($(OS),Windows_NT)
WIN32_OBJ=$(patsubst $(WIN32_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(WIN32_SOURCES))
WIN32_RES_OBJ=$(patsubst $(WIN32_DIR)/%.rc,$(OBJ_DIR)/%.res,$(WIN32_RESOURCES))
else
LINUX_OBJ=$(patsubst $(LINUX_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(LINUX_SOURCES))
endif
ZLIB_OBJ=$(patsubst $(ZLIB_DIR)/%.c,$(OBJ_DIR)/%.o,$(ZLIB_SOURCES))


# Default rule.
cod2rev: mkdir $(TARGET)
    $(TARGET): \
	$(BGAME_OBJ) $(GAME_OBJ) $(QCOMMON_OBJ) $(SCR_OBJ) $(SERVER_OBJ) $(STRINGED_OBJ) $(UNIVERSAL_OBJ) $(XANIM_OBJ) \
	$(LINUX_OBJ) $(WIN32_OBJ) $(WIN32_RES_OBJ) $(ZLIB_OBJ) $(LIBCOD_OBJ) $(YYJSON_OBJ) $(SPEEX_OBJ) $(SQLITE_OBJ) $(MBEDTLS_OBJ)
	$(CC) $(LFLAGS) -o $@ $^ $(LLIBS)
	@echo $(PROTOCOL)$(BUILD_ARCH) > $(BUILD_STAMP)

# Create the output folders before compiling anything, also with -j.
$(BGAME_OBJ) $(GAME_OBJ) $(QCOMMON_OBJ) $(SCR_OBJ) $(SERVER_OBJ) $(STRINGED_OBJ) $(UNIVERSAL_OBJ) $(XANIM_OBJ) \
$(LINUX_OBJ) $(WIN32_OBJ) $(WIN32_RES_OBJ) $(ZLIB_OBJ) $(LIBCOD_OBJ) $(YYJSON_OBJ) $(SPEEX_OBJ) $(SQLITE_OBJ) $(MBEDTLS_OBJ): | mkdir

# Link again when the binary in bin/ was built for another game version or architecture.
ifneq ($(strip $(file <$(BUILD_STAMP))),$(PROTOCOL)$(BUILD_ARCH))
.PHONY: $(TARGET)
endif

# CROSS=1 means a Windows build made from Linux, where the shell is sh and not cmd.
ifeq ($(OS)$(CROSS),Windows_NT)
mkdir:
	if not exist $(BIN_DIR) md $(BIN_DIR)
	if not exist $(subst /,\,$(OBJ_DIR)) md $(subst /,\,$(OBJ_DIR))
	if not exist $(subst /,\,$(OBJ_DIR))\mbedtls md $(subst /,\,$(OBJ_DIR))\mbedtls
	$(MYSQL_COPY_CMD)
else
mkdir:
	mkdir -p $(BIN_DIR)
	mkdir -p $(OBJ_DIR)
	mkdir -p $(OBJ_DIR)/mbedtls
endif


# Build C sources


# A rule to build the engine source code.
vpath %.cpp $(BGAME_DIR) $(SCR_DIR) $(GAME_DIR) $(QCOMMON_DIR) $(SERVER_DIR) $(STRINGED_DIR) $(UNIVERSAL_DIR) $(XANIM_DIR)
$(OBJ_DIR)/%.o: %.cpp
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) $(LIBCOD_SETTINGS) -o $@ $<

# A rule to build linux source code.
$(OBJ_DIR)/%.o: $(LINUX_DIR)/%.cpp
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) -o $@ $<

# A rule to build win32 source code.
$(OBJ_DIR)/%.o: $(WIN32_DIR)/%.cpp
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) -o $@ $<

# A rule to build win32 resource files.
$(OBJ_DIR)/%.res: $(WIN32_DIR)/%.rc
	@echo $(WINDRES)  $@
	@$(WINDRES) -i $< -O coff $@

# A rule to build zlib source code.
$(OBJ_DIR)/%.o: $(ZLIB_DIR)/%.c
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) -o $@ $<

# A rule to build libcod source code.
$(OBJ_DIR)/%.o: $(LIBCOD_DIR)/%.cpp
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) $(LIBCOD_SETTINGS) $(MBEDTLS_FLAGS) -o $@ $<

# A rule to build yyjson source code.
$(OBJ_DIR)/%.o: $(YYJSON_DIR)/%.c
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) -o $@ $<

# A rule to build libspeex source code.
$(OBJ_DIR)/%.o: $(SPEEX_DIR)/libspeex/%.c
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) -DHAVE_CONFIG_H -I$(SPEEX_DIR) -I$(SPEEX_DIR)/include -o $@ $<

# A rule to build sqlite source code.
$(OBJ_DIR)/%.o: $(SQLITE_DIR)/%.c
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) -o $@ $<

# A rule to build Mbed TLS source code.
$(OBJ_DIR)/mbedtls/%.o: $(MBEDTLS_DIR)/library/%.c
	@echo $(CC)  $@
	@$(CC) -c $(CFLAGS) $(MBEDTLS_FLAGS) -o $@ $<


# Cleanup


ifeq ($(OS),Windows_NT)
clean:
	del /Q /S "$(BIN_DIR)\$(BIN_NAME)$(BIN_EXT)"
	del /Q /S "$(BIN_DIR)\libmysql.dll"
	del /Q /S "$(BIN_DIR)\.$(BIN_NAME).build"
	del /Q /S "$(OBJ_ROOT)\*.o"
	del /Q /S "$(OBJ_ROOT)\*.res"
	del /Q /S "$(OBJ_ROOT)\*.d"
else
clean:
	rm -f $(BIN_DIR)/$(BIN_NAME)$(BIN_EXT)
	rm -f $(BUILD_STAMP)
	rm -rf $(OBJ_ROOT)
endif


# Cross-compile the Windows binary from Linux with MinGW-w64.
MINGW_PREFIX=i686-w64-mingw32
windows:
	$(MAKE) OS=Windows_NT CROSS=1 CC=$(MINGW_PREFIX)-gcc-posix WINDRES=$(MINGW_PREFIX)-windres $(BIN_DIR)/cod2rev_win32.exe

.PHONY: cod2rev mkdir clean windows

# Header dependencies generated by the compiler (-MMD).
-include $(wildcard $(OBJ_DIR)/*.d $(OBJ_DIR)/mbedtls/*.d)
