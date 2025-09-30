#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Configuration for software-specific file extensions
 */
const SOFTWARE_CONFIG = {
  blender: { extension: 'py' },
  sketchup: { extension: 'rb' },
  rhino: { extension: 'py' },
  revit: { extension: 'py' },
  // Add new software types here as needed
};

/**
 * Recursively find all metadata.json files in a directory
 * @param {string} dir - Directory to search
 * @returns {string[]} Array of metadata.json file paths
 */
function findMetadataFiles(dir) {
  const files = [];

  function traverse(currentDir) {
    const entries = fs.readdirSync(currentDir);

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        traverse(fullPath);
      } else if (entry === 'metadata.json') {
        files.push(fullPath);
      }
    }
  }

  traverse(dir);
  return files;
}

/**
 * Extract software type from metadata file path
 * @param {string} metadataPath - Path to metadata.json file
 * @returns {string} Software type identifier
 */
function extractSoftwareType(metadataPath) {
  const normalizedPath = metadataPath.replace(/\\/g, '/');
  const pathParts = normalizedPath.split('/');
  const toolsIndex = pathParts.indexOf('tools');

  if (toolsIndex === -1 || toolsIndex + 1 >= pathParts.length) {
    throw new Error(`Invalid tool path structure: ${metadataPath}`);
  }

  return pathParts[toolsIndex + 1];
}

/**
 * Extract tool folder name from metadata file path
 * @param {string} metadataPath - Path to metadata.json file
 * @returns {string} Tool folder name
 */
function extractToolName(metadataPath) {
  return path.basename(path.dirname(metadataPath));
}

/**
 * Get the expected main tool file name for a software type
 * @param {string} softwareType - Software type identifier
 * @returns {string} Main tool file name
 */
function getMainFileName(softwareType) {
  const config = SOFTWARE_CONFIG[softwareType];
  if (!config) {
    console.warn(`⚠️ Unknown software type '${softwareType}', defaulting to .py extension`);
    return 'tool.py';
  }
  return `tool.${config.extension}`;
}

/**
 * Find dependency files in tool directory
 * @param {string} metadataPath - Path to metadata.json file
 * @param {string} softwareType - Software type identifier
 * @returns {string[]} Array of dependency file names
 */
function findDependencies(metadataPath, softwareType) {
  const toolDir = path.dirname(metadataPath);
  const entries = fs.readdirSync(toolDir);
  const mainFileName = getMainFileName(softwareType);
  const excludedFiles = new Set(['metadata.json', mainFileName]);

  return entries.filter(entry => {
    if (excludedFiles.has(entry)) return false;

    const fullPath = path.join(toolDir, entry);
    return fs.statSync(fullPath).isFile();
  });
}

/**
 * Verify main tool file exists
 * @param {string} metadataPath - Path to metadata.json file
 * @param {string} softwareType - Software type identifier
 * @returns {boolean} True if main tool file exists
 */
function verifyMainToolFile(metadataPath, softwareType) {
  const toolDir = path.dirname(metadataPath);
  const mainFileName = getMainFileName(softwareType);
  const mainFilePath = path.join(toolDir, mainFileName);
  return fs.existsSync(mainFilePath);
}

/**
 * Get last git commit date for a directory
 * @param {string} dirPath - Directory path
 * @returns {string} ISO 8601 formatted date string
 */
function getLastCommitDate(dirPath) {
  try {
    const relativePath = path.relative(process.cwd(), dirPath);
    const command = `git log -1 --format=%aI -- "${relativePath}"`;
    const result = execSync(command, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe']
    });

    const date = result.trim();
    if (!date) {
      console.warn(`⚠️ No git history found for ${relativePath}, using current date`);
      return new Date().toISOString();
    }

    return date;
  } catch (error) {
    console.warn(`⚠️ Failed to get git date for ${dirPath}: ${error.message}`);
    return new Date().toISOString();
  }
}

/**
 * Discover software types from tools directory structure
 * @param {string} toolsDir - Path to tools directory
 * @returns {string[]} Sorted array of software type names
 */
function discoverSoftwareTypes(toolsDir) {
  const entries = fs.readdirSync(toolsDir);
  const softwareTypes = [];

  for (const entry of entries) {
    const entryPath = path.join(toolsDir, entry);
    if (fs.statSync(entryPath).isDirectory()) {
      softwareTypes.push(entry);
    }
  }

  return softwareTypes.sort();
}

/**
 * Process a single tool's metadata
 * @param {string} metadataPath - Path to metadata.json file
 * @returns {Object|null} Tool object or null if processing failed
 */
function processTool(metadataPath) {
  try {
    const metadataContent = fs.readFileSync(metadataPath, 'utf8');
    const metadata = JSON.parse(metadataContent);

    const softwareType = extractSoftwareType(metadataPath);
    const toolName = extractToolName(metadataPath);

    // Validate required files
    if (!verifyMainToolFile(metadataPath, softwareType)) {
      const mainFileName = getMainFileName(softwareType);
      console.error(`❌ Skipping ${toolName}: Missing main file ${mainFileName}`);
      return null;
    }

    // Build tool object
    const dependencies = findDependencies(metadataPath, softwareType);
    const lastCommitDate = getLastCommitDate(path.dirname(metadataPath));

    const tool = {
      name: metadata.name || toolName,
      description: metadata.description || '',
      folder: toolName,
      updated_at: lastCommitDate
    };

    // Add optional fields
    if (dependencies.length > 0) {
      tool.dependencies = dependencies;
    }

    if (metadata.id) {
      tool.id = metadata.id;
    }

    // Log processing result
    const depInfo = dependencies.length > 0 ? ` (${dependencies.length} deps)` : '';
    const idInfo = metadata.id ? ` [${metadata.id}]` : '';
    console.log(`✅ ${tool.name} (${softwareType})${depInfo}${idInfo}`);

    return { tool, softwareType };

  } catch (error) {
    console.error(`❌ Failed to process ${metadataPath}: ${error.message}`);
    return null;
  }
}

/**
 * Generate catalog summary statistics
 * @param {Object} catalog - The generated catalog
 */
function logCatalogSummary(catalog) {
  const totalTools = Object.values(catalog.tools).reduce((sum, tools) => sum + tools.length, 0);

  console.log(`\n🎉 Generated catalog with ${totalTools} tools:`);

  Object.entries(catalog.tools).forEach(([software, tools]) => {
    if (tools.length === 0) return;

    const toolsWithDeps = tools.filter(tool => tool.dependencies?.length > 0).length;
    const depInfo = toolsWithDeps > 0 ? ` (${toolsWithDeps} with dependencies)` : '';
    console.log(`   ${software}: ${tools.length}${depInfo}`);
  });
}

/**
 * Main catalog generation function
 */
async function main() {
  try {
    console.log('🔍 Generating tool catalog...\n');

    // Validate environment
    const toolsDir = path.join(process.cwd(), 'tools');
    if (!fs.existsSync(toolsDir)) {
      throw new Error('Tools directory not found');
    }

    // Discover structure
    const metadataFiles = findMetadataFiles(toolsDir);
    const softwareTypes = discoverSoftwareTypes(toolsDir);

    console.log(`📁 Found ${metadataFiles.length} tools across ${softwareTypes.length} software types`);
    console.log(`🔧 Software types: ${softwareTypes.join(', ')}\n`);

    // Initialize catalog
    const catalog = {
      version: '1.0.0',
      generated_at: new Date().toISOString(),
      tools: Object.fromEntries(softwareTypes.map(type => [type, []]))
    };

    // Process all tools
    for (const metadataPath of metadataFiles) {
      const result = processTool(metadataPath);
      if (result) {
        const { tool, softwareType } = result;
        if (catalog.tools[softwareType]) {
          catalog.tools[softwareType].push(tool);
        } else {
          console.warn(`⚠️ Unknown software type: ${softwareType}`);
        }
      }
    }

    // Sort tools by name within each category
    Object.values(catalog.tools).forEach(tools => {
      tools.sort((a, b) => a.name.localeCompare(b.name));
    });

    // Write catalog
    const catalogPath = path.join(process.cwd(), 'catalog.json');
    fs.writeFileSync(catalogPath, JSON.stringify(catalog, null, 2));

    logCatalogSummary(catalog);

  } catch (error) {
    console.error(`❌ Fatal error: ${error.message}`);
    process.exit(1);
  }
}

// Execute if run directly
if (require.main === module) {
  main().catch(error => {
    console.error(`❌ Unhandled error: ${error.message}`);
    process.exit(1);
  });
}

// Export for testing
module.exports = {
  main,
  findMetadataFiles,
  extractSoftwareType,
  extractToolName,
  getMainFileName,
  findDependencies,
  discoverSoftwareTypes,
  processTool
};