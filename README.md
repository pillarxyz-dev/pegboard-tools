# PegBoard Tool Library

A community-driven collection of automation tools for design software, accessible through the PegBoard application.

## 🚀 Quick Start

**Adding a new tool is simple:**

1. Create a folder: `tools/{software}/your-tool-name/`
2. Add `metadata.json` with your tool info
3. Add your tool file (`tool.py`, `tool.rb`, etc.)
4. Submit a pull request

**That's it!** Our automated system handles the rest.

## 📁 Repository Structure

```
├── catalog.json                 # Auto-generated tool registry
├── .github/workflows/           # Automated catalog generation
├── scripts/generate-catalog.js  # Catalog generation script
├── tools/
│   ├── blender/
│   │   └── tool-1/
│   │       ├── metadata.json    # Tool metadata
│   │       └── tool.py          # Tool code
│   ├── sketchup/
│   │   └── tool-2/
│   │       ├── metadata.json
│   │       └── tool.rb
│   └── revit/
│       ├── tool-3/
│       │   ├── metadata.json
│       │   └── tool.py
│       └── tool-4/
│           ├── metadata.json
│           └── tool.py
```

## 🔄 Automated System

This repository uses **GitHub Actions** to automatically maintain the tool catalog:

- ✅ **Auto-detection**: New tools and software types are discovered dynamically
- ✅ **Auto-generation**: `catalog.json` is generated from individual `metadata.json` files
- ✅ **Git-based timestamps**: Tools get `updated_at` from their last commit date
- ✅ **CDN cache purging**: jsDelivr CDN cache is automatically purged on updates
- ✅ **Zero maintenance**: No manual catalog editing required

## 🤝 Contributing

### Quick Start Guide

1. **Fork and clone** this repository
2. **Create your tool** following the structure below
3. **Submit a pull request** - automation handles the rest!

### Adding a New Tool

```bash
# 1. Create tool directory structure
mkdir -p tools/{software}/{your-tool-name}

# 2. Add metadata.json
cat > tools/{software}/{your-tool-name}/metadata.json << EOF
{
  "name": "Your Tool Name",
  "description": "Brief description of what your tool does"
}
EOF

# 3. Add your main tool file
# - For Blender: tool.py
# - For SketchUp: tool.rb
# - For Revit: tool.py
# - For Rhino: tool.py
cp your-script.{py,rb} tools/{software}/{your-tool-name}/tool.{py,rb}

# 4. Add any dependency files (optional)
cp additional-files.* tools/{software}/{your-tool-name}/

# 5. Submit your pull request!
```

### Metadata Format

```json
{
  "name": "Display Name",
  "description": "Tool description",
  "id": "optional-unique-id"
}
```

### File Structure Requirements

```
tools/{software}/{tool-name}/
├── metadata.json          # Required: Tool information
├── tool.{py,rb}          # Required: Main tool file
├── additional-file.py    # Optional: Dependencies
└── helper-script.txt     # Optional: Dependencies
```

### Validation Rules

The automated system validates:

- ✅ `metadata.json` exists and is valid JSON
- ✅ Main tool file exists (`tool.py`, `tool.rb`, etc.)
- ✅ Tool directory follows naming conventions
- ✅ Software type is recognized or automatically added

## Usage

These tools are designed to be used with the PegBoard application. Users can browse the library within PegBoard and clone tools to their local workspace for use and modification.
