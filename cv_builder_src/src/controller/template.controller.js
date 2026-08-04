const fs = require('fs/promises');
const path = require('path');

class TemplateController {
  async listTemplates(req, res) {
    try {
      const templatesDir = path.join(__dirname, '../templates');
      const files = await fs.readdir(templatesDir, { withFileTypes: true });
      const templates = files
        .filter(dirent => dirent.isDirectory())
        .map(dirent => dirent.name);
      
      return res.json({ success: true, templates });
    } catch (err) {
      return res.status(500).json({ success: false, error: err.message });
    }
  }

  async getTemplateFiles(req, res) {
    try {
      const { id } = req.params;
      const templatePath = path.join(__dirname, '../templates', id);
      
      // Basic security check against traversal
      if (id.includes('..') || path.isAbsolute(id)) {
        return res.status(400).json({ success: false, error: 'Invalid template ID' });
      }

      // Check if template exists
      try {
        await fs.access(templatePath);
      } catch {
        return res.status(404).json({ success: false, error: 'Template not found' });
      }

      // Recursively read all .tex files for the LLM to edit
      const getFiles = async (dir, base = '') => {
        const dirents = await fs.readdir(dir, { withFileTypes: true });
        let results = {};
        for (const dirent of dirents) {
          const resPath = path.join(dir, dirent.name);
          const relPath = path.join(base, dirent.name).replace(/\\/g, '/');
          
          if (dirent.isDirectory()) {
            results = { ...results, ...(await getFiles(resPath, relPath)) };
          } else if (dirent.name.endsWith('.tex')) {
            const content = await fs.readFile(resPath, 'utf8');
            results[relPath] = content;
          }
        }
        return results;
      };

      const files = await getFiles(templatePath);
      
      return res.json({ success: true, files });
    } catch (err) {
      return res.status(500).json({ success: false, error: err.message });
    }
  }

  async getTemplateConcatenated(req, res) {
    try {
      const { id } = req.params;
      const templatePath = path.join(__dirname, '../templates', id);
      
      if (id.includes('..') || path.isAbsolute(id)) {
        return res.status(400).json({ success: false, error: 'Invalid template ID' });
      }

      try {
        await fs.access(templatePath);
      } catch {
        return res.status(404).json({ success: false, error: 'Template not found' });
      }

      // 1. Find the main .tex file
      const dirents = await fs.readdir(templatePath, { withFileTypes: true });
      let mainTexPath = null;
      let mainContent = '';

      // Priority list for main file names
      const priorityNames = ['resume.tex', 'cv.tex', 'main.tex', 'sample.tex'];
      
      let candidateFiles = [];
      for (const dirent of dirents) {
        if (!dirent.isDirectory() && dirent.name.endsWith('.tex')) {
          candidateFiles.push(dirent.name);
        }
      }

      // Find the first priority file that exists
      let selectedFile = null;
      for (const pName of priorityNames) {
        if (candidateFiles.includes(pName)) {
          selectedFile = pName;
          break;
        }
      }

      // Fallback: look for \documentclass in any .tex file
      if (selectedFile) {
        mainTexPath = path.join(templatePath, selectedFile);
        mainContent = await fs.readFile(mainTexPath, 'utf8');
      } else {
        for (const file of candidateFiles) {
          const content = await fs.readFile(path.join(templatePath, file), 'utf8');
          if (content.includes('\\documentclass')) {
            mainTexPath = path.join(templatePath, file);
            mainContent = content;
            break;
          }
        }
      }

      if (!mainTexPath) {
        return res.status(404).json({ success: false, error: 'No main .tex file found for this template' });
      }

      // 2. Recursively resolve \input{} tags
      const resolveInputs = async (content, baseDir) => {
        const lines = content.split('\n');
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          // Skip commented lines
          if (line.trim().startsWith('%')) {
            continue;
          }
          
          const inputRegex = /\\input{([^}]+)}/g;
          let match;
          while ((match = inputRegex.exec(line)) !== null) {
            // Check if there is a % before this match on this line
            const beforeMatch = line.substring(0, match.index);
            if (beforeMatch.includes('%')) {
              continue;
            }

            let inputFileName = match[1];
            if (!inputFileName.endsWith('.tex')) {
              inputFileName += '.tex';
            }
            
            const inputFilePath = path.join(baseDir, inputFileName);
            try {
              const inputContent = await fs.readFile(inputFilePath, 'utf8');
              const resolvedInputContent = await resolveInputs(inputContent, path.dirname(inputFilePath));
              
              const wrappedContent = `\n% --- START OF ${match[1]} ---\n${resolvedInputContent}\n% --- END OF ${match[1]} ---\n`;
              lines[i] = lines[i].replace(match[0], wrappedContent);
            } catch (err) {
              console.error(`Could not resolve input file: ${inputFilePath}`);
            }
          }
        }
        return lines.join('\n');
      };

      const finalConcatenatedContent = await resolveInputs(mainContent, templatePath);

      return res.json({ 
        success: true, 
        templateId: id,
        tex: finalConcatenatedContent 
      });
    } catch (err) {
      console.error(err);
      return res.status(500).json({ success: false, error: err.message });
    }
  }
}

module.exports = new TemplateController();
