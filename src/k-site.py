from pathlib import Path
import os
import shutil
import yaml
import markdown
import re
import json
import csv
import io
from jinja2 import Environment, FileSystemLoader
from markdown.extensions.toc import TocExtension
from markdown.extensions.extra import ExtraExtension

# === PATHS ===
BASE_DIR = Path(__file__).resolve().parent.parent
METHODS_DIR = BASE_DIR / "methods"
DOWNLOADS_SRC = BASE_DIR / "downloads"
CONFIG_FILE = BASE_DIR / "config" / "settings.yaml"
TEMPLATE_DIR = BASE_DIR / "src" / "templates"
OUTPUT_DIR = BASE_DIR / "docs"
DOWNLOAD_DIR = OUTPUT_DIR / "download"
CONTENT_DIR = METHODS_DIR  # patching the previous omission

# === LOAD CONFIG ===
def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "ga_tracking_id": None,
        "site_base_path": "/",
        "rules": {
            "ignore_folders": [],
            "viewer_extensions": [".txt", ".md", ".py", ".json", ".csv"],
            "image_extensions": [".jpg", ".jpeg", ".png"],
            "download_extensions": [".txt", ".md", ".py", ".json", ".csv"],
            "classify_folders": False
        }
    }

cfg = load_config()
rules = cfg.get("rules", {})
GA_ID = cfg.get("ga_tracking_id", None)
site_base_path = cfg.get("site_base_path", "/")
repo_name = BASE_DIR.name

# === AUTO-LINK FIXER FOR README ===
def fix_links_in_readme(md: str) -> str:
    md = re.sub(r'\(([^\)]+)\.md\)', r'(\1-viewer.html)', md)
    md = re.sub(r'\(([^\)]+)\.txt\)', r'(\1-viewer.html)', md)
    md = re.sub(r'\(([^\)]+)\.py\)', r'(\1-viewer.html)', md)
    md = re.sub(r'\(([^\)]+)\.json\)', r'(\1-viewer.html)', md)
    md = re.sub(r'\(([^\)]+)\.csv\)', r'(\1-viewer.html)', md)
    md = re.sub(r'\(([^\)\s]+?)/\)', r'(\1/index.html)', md)
    return markdown.markdown(md, extensions=["fenced_code", "tables", TocExtension(permalink=True), ExtraExtension()])

# === BUILD TOC FROM OUTPUT DIR ===
def generate_site_toc():
    toc_lines = ["## Site Contents", ""]
    for item in sorted(OUTPUT_DIR.iterdir()):
        if item.is_dir() and (item / "index.html").exists():
            toc_lines.append(f"- 📁 [{item.name}]({item.name}/index.html)")
    return "\n".join(toc_lines)

# === JINJA SETUP ===
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
viewer_template = env.get_template("viewer.html")
index_template = env.get_template("index.html")

# === RESET OUTPUT DIR ===
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True)
DOWNLOAD_DIR.mkdir(parents=True)

# === COPY DOWNLOAD FILES FROM /downloads TO /docs/download/
for file in DOWNLOADS_SRC.iterdir():
    if file.suffix.lower() in [".zip", ".exe", ".appimage"]:
        shutil.copy2(file, DOWNLOAD_DIR / file.name)

# === FILE PIPELINE ===
for root, _, files in os.walk(CONTENT_DIR):
    rel_root = Path(root).relative_to(CONTENT_DIR)
    if any(str(rel_root).startswith(f) for f in rules.get("ignore_folders", [])):
        continue

    target_folder = OUTPUT_DIR / rel_root
    target_folder.mkdir(parents=True, exist_ok=True)

    index_files = []

    for file in files:
        src_file = Path(root) / file
        ext = src_file.suffix.lower()
        rel_path = src_file.relative_to(CONTENT_DIR)

        if ext in rules.get("viewer_extensions", []):
            with open(src_file, "r", encoding="utf-8") as f:
                raw = f.read()

            if ext == ".md":
                body = markdown.markdown(raw, extensions=["fenced_code", "tables", TocExtension(), ExtraExtension()])
            elif ext == ".json":
                try:
                    parsed = json.loads(raw)
                    body = f"<pre>{json.dumps(parsed, indent=2)}</pre>"
                except Exception as e:
                    body = f"<pre>⚠️ Invalid JSON:\n{str(e)}</pre>"
            elif ext == ".csv":
                try:
                    f_io = io.StringIO(raw)
                    reader = csv.reader(f_io)
                    table_rows = ["<table border='1' cellspacing='0' cellpadding='4'>"]
                    for row in reader:
                        table_rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
                    table_rows.append("</table>")
                    body = "\n".join(table_rows)
                except Exception as e:
                    body = f"<pre>⚠️ Invalid CSV:\n{str(e)}</pre>"
            else:
                body = f"<pre>{raw}</pre>"

            download_link = f"../download/{src_file.name}" if ext in rules.get("download_extensions", []) else None

            html = viewer_template.render(
                filename=src_file.name,
                site_base_path=site_base_path,
                content=body,
                breadcrumbs=str(rel_path.parent),
                ga_tracking_id=GA_ID,
                download_link=download_link
            )

            html_name = src_file.stem + "-viewer.html"
            with open(target_folder / html_name, "w", encoding="utf-8") as f:
                f.write(html)

            index_files.append(html_name)

            if ext in rules.get("download_extensions", []):
                shutil.copy2(src_file, DOWNLOAD_DIR / src_file.name)

        elif ext in rules.get("image_extensions", []):
            shutil.copy2(src_file, target_folder / src_file.name)
            index_files.append(src_file.name)

            if ext in rules.get("download_extensions", []):
                shutil.copy2(src_file, DOWNLOAD_DIR / src_file.name)

    if index_files:
        index_html = index_template.render(
            folder=str(rel_root),
            files=index_files,
            site_base_path=site_base_path
        )
        with open(target_folder / "index.html", "w", encoding="utf-8") as f:
            f.write(index_html)

# === ROOT INDEX OR LANDING PAGE
root_links = []
for sub in OUTPUT_DIR.iterdir():
    if sub.is_dir() and (sub / "index.html").exists():
        root_links.append(f"{sub.name}/index.html")

readme_path = BASE_DIR / "README.md"
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_md = f.read()

methods_readme = METHODS_DIR / "README.md"
if methods_readme.exists():
    with open(methods_readme, "r", encoding="utf-8") as f:
        raw = f.read()
        rendered = fix_links_in_readme(raw)

    # Ensure the target folder exists before writing
    (OUTPUT_DIR / "methods").mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "methods" / "index.html", "w", encoding="utf-8") as f:
        f.write(rendered)

downloads_readme = DOWNLOADS_SRC / "README.md"
if downloads_readme.exists():
    with open(downloads_readme, "r", encoding="utf-8") as f:
        raw = f.read()
        rendered = fix_links_in_readme(raw)

    # === DOWNLOADS README PATCH
downloads_readme = DOWNLOADS_SRC / "README.md"
if downloads_readme.exists():
    with open(downloads_readme, "r", encoding="utf-8") as f:
        raw = f.read()
        rendered = fix_links_in_readme(raw)

    downloads_index = OUTPUT_DIR / "download" / "index.html"
    with open(downloads_index, "w", encoding="utf-8") as f:
        f.write(rendered)

# === ROOT README TOC PATCH
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_md = f.read()

    toc_block = generate_site_toc()

    if "<!-- auto-generated TOC" in readme_md:
        readme_md = re.sub(
            r'<!-- auto-generated TOC.*?-->',
            f'<!-- auto-generated TOC -->\n\n{toc_block}',
            readme_md,
            flags=re.DOTALL
        )
    else:
        readme_md += f"\n\n## Site Contents\n\n{toc_block}"

    readme_html = fix_links_in_readme(readme_md)

    landing_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GitSite Landing</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #fff; color: #000; }}
    a {{ color: #1a73e8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #0d1117; color: #c9d1d9; }}
      a {{ color: #58a6ff; }}
    }}
  </style>
</head>
<body>
  {readme_html}
</body>
</html>"""

    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(landing_html)
else:
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_template.render(
            folder="Root",
            files=root_links,
            site_base_path=site_base_path,
        ))

# === ZIP PACKAGE
shutil.make_archive("docs", "zip", OUTPUT_DIR)
else:
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_template.render(
            folder="Root",
            files=root_links,
            site_base_path=site_base_path,
        ))

# === ZIP PACKAGE
shutil.make_archive("docs", "zip", OUTPUT_DIR)
