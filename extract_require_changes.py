
import os
import pandas as pd
from tabulate import tabulate


BASE_DIR      = "/Users/mac/Desktop/RepairComp/results/smartbugs"
OUTPUT_CSV    = os.path.join(BASE_DIR, "data_analysis", "patches_w_require.csv")
OUTPUT_TABLE  = os.path.join(BASE_DIR, "data_analysis", "pretty_table2.txt")
GITHUB_BASE   = (
    "https://github.com/ASSERT-KTH/RepairComp/blob/main/results/smartbugs"
)

def clean_keys(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("Tool", "Category", "Patch"):
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(r"\s+", " ", regex=True)
        )
    return df


def is_real_require(line: str) -> bool:
    stripped = line.strip()[1:].strip()  
    # remove +/-, och whitespace
    has_require = "require(" in stripped
    full_comment = stripped.startswith("//") or stripped.startswith("/*")
    return has_require and not full_comment

def classify_require_type(line: str) -> str:
    stripped = line.strip()
    if "require(" in stripped:
        lower = stripped.lower()
        if any(x in lower for x in ["call.value", "send(", "transfer(", "success", "now", "block.timestamp"]):
            return "runtime check"
        if "msg.sender" in lower and "==" in lower and "owner" in lower:
            return "modifier"
        if "lock" in lower:
            return "modifier"
        if any(x in lower for x in ["balances", "limit", ">=", "<=", ">", "<", "!=", "=="]):
            return "invariant"
        return "unknown"
    return "unknown"


def flush_changes(
    added: list[str],
    removed: list[str],
    meta: dict[str, str],
    out: list[dict],
) -> None:
    max_len = max(len(added), len(removed))
    for i in range(max_len):
        added_line = added[i] if i < len(added) else ""
        removed_line = removed[i] if i < len(removed) else ""
        if added_line and removed_line:
            out.append({
                **meta,
                "ChangeType": "modified",
                "CodeLine": added_line,
                "RequireType": classify_require_type(added_line)
            })
        elif added_line:
            out.append({
                **meta,
                "ChangeType": "added",
                "CodeLine": added_line,
                "RequireType": classify_require_type(added_line)
            })
        elif removed_line:
            out.append({
                **meta,
                "ChangeType": "removed",
                "CodeLine": removed_line,
                "RequireType": classify_require_type(removed_line)
            })
    added.clear()
    removed.clear()

require_rows: list[dict] = []

for tool in os.listdir(BASE_DIR):
    tool_dir = os.path.join(BASE_DIR, tool)
    if not os.path.isdir(tool_dir):
        continue                                    
    for category in os.listdir(tool_dir):
        cat_dir = os.path.join(tool_dir, category)
        if not os.path.isdir(cat_dir):
            continue
        for patch in os.listdir(cat_dir):
            patch_dir = os.path.join(cat_dir, patch)
            diff_path = os.path.join(patch_dir, f"{patch}.diff")
            if not os.path.isfile(diff_path):
                continue

            added_requires: list[str] = []
            removed_requires: list[str] = []
            in_hunk = False

            with open(diff_path, encoding="utf‑8") as diff:
                for line in diff:
                    if line.startswith("@@"):
                        flush_changes(
                            added_requires,
                            removed_requires,
                            {
                                "Tool": tool,
                                "Category": category,
                                "Patch": patch,
                                "GitHubLink": f"{GITHUB_BASE}/{tool}/{category}/{patch}/{patch}.diff",
                            },
                            require_rows,
                        )
                        in_hunk = True
                        continue
                    if not in_hunk:
                        continue



                    if line.startswith("+") and is_real_require(line):
                        added_requires.append(line[1:].strip())
                    elif line.startswith("-") and is_real_require(line):
                        removed_requires.append(line[1:].strip())

            flush_changes(
                added_requires,
                removed_requires,
                {
                    "Tool": tool,
                    "Category": category,
                    "Patch": patch,
                    "GitHubLink": f"{GITHUB_BASE}/{tool}/{category}/{patch}/{patch}.diff",
                },
                require_rows,
            )


require_df = clean_keys(pd.DataFrame(require_rows))
require_df.to_csv(OUTPUT_CSV, index=False)

# pretty_tbl = tabulate(
#     require_df, headers="keys", tablefmt="fancy_grid", showindex=False
# )
# with open(OUTPUT_TABLE, "w", encoding="utf‑8") as fh:
#     fh.write(pretty_tbl)
