import json
import re
import runpy
from pathlib import Path

path = Path("audit/prompts/registry_candidate.py")
source = path.read_text(encoding="utf-8-sig")
ns = runpy.run_path(str(path))
nav_lines = ["NAV_ITEMS = ["]
for item in ns["NAV_ITEMS"]:
    nav_lines.append(f'    {{"code": {json.dumps(item["code"])},')
    nav_lines.append(f'     "label": {json.dumps(item["label"])},')
    nav_lines.append(f'     "icon": {json.dumps(item["icon"])},')
    nav_lines.append(f'     "to": {json.dumps(item["to"])},')
    nav_lines.append(
        f'     "required_permission": {json.dumps(item["required_permission"])},'
    )
    nav_lines.append(f'     "sort_order": {item["sort_order"]}}},')
nav_lines.append("]")
permission_lines = ["PERMISSIONS = ["]
for code, label in ns["PERMISSIONS"]:
    permission_lines.append(f'    ({json.dumps(code)},')
    permission_lines.append(f'     {json.dumps(label)}),')
permission_lines.append("]")
source = re.sub(r"(?s)NAV_ITEMS = \[.*?\n\]", "\n".join(nav_lines), source)
source = re.sub(
    r"(?s)PERMISSIONS = \[.*?\n\]", "\n".join(permission_lines), source
)
path.write_text(source, encoding="utf-8")
