<p align="center">
  <img src="assets/logo-rounded.png" alt="Decompyler logo" width="180">
</p>

# Decompyler

A desktop tool for extracting PyInstaller-packed executables and decompiling or
disassembling the resulting Python bytecode.

## Features

- Select a compiled PyInstaller binary (EXE or ELF).
- Extract the embedded archive and list its `.pyc` modules.
- Disassemble modules with `pycdas`.
- Decompile modules with `pycdc`.
- Edit, run, and save the decompiled Python source.
- Hide standard library and PyInstaller support modules from the module list.
- Configurable syntax theme, font, and binary paths.
- Find text in either code pane (`Ctrl+F`).

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- `pycdc` and `pycdas` built separately from
  [zrax/pycdc](https://github.com/zrax/pycdc)

Binaries are no longer bundled with Decompyler. Build `pycdc` and `pycdas` from
source, then place them in a directory of your choice.

## Installing pycdc and pycdas

```bash
git clone --recursive https://github.com/zrax/pycdc.git
cd pycdc
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

Install or copy the resulting `pycdc` and `pycdas` executables somewhere
persistent, for example:

```bash
mkdir -p ~/.local/bin
cp build/pycdc build/pycdas ~/.local/bin/
chmod +x ~/.local/bin/pycdc ~/.local/bin/pycdas
```

On Windows the executables are named `pycdc.exe` and `pycdas.exe`.

## Configuration

Binary paths can be set in the application under **Settings > Binary Paths**, or
edited directly in `~/.config/decompyler/settings.toml`:

```toml
[appearance]
theme = "monokai"
font_family = "Monospace"
font_size = 15
hide_stdlib = true

[paths]
pycdc_path = "/home/user/.local/bin/pycdc"
pycdas_path = "/home/user/.local/bin/pycdas"
```

Default paths are:

- Linux/macOS: `~/.local/bin/pycdc` and `~/.local/bin/pycdas`
- Windows: `%USERPROFILE%\.local\bin\pycdc.exe` and
  `%USERPROFILE%\.local\bin\pycdas.exe`

If the configured binaries are missing, Decompyler shows an error directing you
to the Settings dialog.

## Usage

```bash
uv sync
uv run python main.py
```

Or, after installing the package:

```bash
uv run decompyler
```

Select a compiled binary, wait for extraction, choose a module from the dropdown,
then view the disassembly and decompiled source side by side.

## Building a standalone executable

```bash
uv run pyinstaller --noconfirm --clean decompyler.spec
```

The generated executable contains the application and its Python dependencies,
but not `pycdc` or `pycdas`. Users must install those separately and configure
their paths as described above.

## CI and releases

Release artifacts are application-only. The build workflow no longer compiles or
embeds `pycdc`/`pycdas`; the smoke test only verifies that the application starts
and warns about any missing configured binaries.
