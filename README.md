# EpochOfMods Minecraft Mod Catalog Generator

EpochOfMods is a Minecraft mod catalog generator for Minecraft 1.20.1 Forge modpacks. It uses the public Modrinth API to discover real Forge-compatible mods, classify them into broad categories, verify published JAR versions, and write a reviewable catalog with project links, download URLs, version details, file information, and required dependency IDs.

## Install

Requirements:

- Python 3.10 or newer
- Internet access
- A Minecraft 1.20.1 Forge installation for using selected mods

Clone or download this project, then open a terminal in its directory:

```text
python --version
```

On Windows PowerShell:

```text
py --version
```

The generator uses only Python's standard library and does not require third-party packages.

## Use

Run the generator:

```text
python generate_modpack_catalog.py
```

On Windows PowerShell:

```text
py .\generate_modpack_catalog.py
```

The script queries the public Modrinth API and writes:

```text
forge_1.20.1_mod_catalog.txt
```

The catalog searches for projects that declare Minecraft 1.20.1 and Forge support. It classifies matching projects into Weapons, Decoration, Other, Roleplay, Essential, Helper, and Fun categories. Projects can appear in more than one category because the classifications are broad and are based on Modrinth tags and project text.

Review every selected project, dependency, license, client/server requirement, and known incompatibility before installation. Download the chosen JAR files from their listed Modrinth URLs and place compatible files in the `mods` folder of a Minecraft 1.20.1 Forge instance. Install required dependencies and test the collection incrementally.

The generator does not download JAR files, create a launcher-importable modpack, test runtime compatibility, or guarantee 1,000 verified entries in every category. The live Modrinth catalog may contain fewer matching projects, and metadata alone cannot prove that a large group of mods will work together.

---

More Minecraft mod projects by EnderDevelopment: https://github.com/EnderDevelopment

Project page: https://dash.enderdevelopment.com/community/b714f104-ec54-4273-b7f7-59501e17c90c?utm_source=github&utm_medium=readme&utm_campaign=auto_publish&utm_content=b714f104-ec54-4273-b7f7-59501e17c90c
