# What's under the hood?

K-Site is a zero-GUI transformation engine that converts any folder into a static, navigable HTML site.

No servers. No frameworks. No runtime dependency chain.

---

## Core Process

- **Python 3.10+**
- **Libraries used**:
  - `jinja2` → HTML rendering from templates
  - `markdown`, `toc`, `extra` → for .md content + TOC logic
  - `yaml` → configuration rules (render extensions, output paths)
  - `csv`, `json`, `io` → structured content parsing
  - `pathlib`, `os`, `shutil` → folder traversal, file ops
  - `re` → content rewrites (autolink TOCs, viewer redirects)

---

## Execution Flow

1. **Folder scan**  
   Each subfolder is walked recursively. Logic skips ignored folders by YAML config.

2. **Content classification**  
   - `.md`, `.txt`, `.csv`, `.json`, `.py` → rendered with `viewer.html`  
   - Images → copied directly  
   - Other files → either skipped or zipped (configurable)

3. **Viewer generation**  
   Rendered HTML is injected with a `viewer.html` template, embedding content and safe download links.

4. **Subfolder `index.html` build**  
   Each folder gets its own index with file links, built from the list of generated items.

5. **Root `index.html` (landing)**  
   Generated from `README.md` with markdown-to-HTML conversion. Injected into a stripped landing template.

6. **Static variant (`index_static.html`)**  
   Optionally generated as a no-script fallback using the same file map, minus JS logic.

7. **Packaging**  
   Entire `docs/` is zipped into a standalone site bundle.

---

K-Site is meant to ship offline.  
No runtime, no build chain, no NPM, no Docker, no bullshit.

Just Python + Jinja + a structured mind.


-- [Kay](https://linkedin.com/in/taras-khamardiuk)  

    `#ksite #aiposbuilt #foldertransformationengine #fromukrainianswithlovetohumankind 🇺🇦`
