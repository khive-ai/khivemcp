from pathlib import Path

from lionagi.libs.file.process import dir_to_files
from lionagi.utils import create_path


def concat_files(
    data_path: str | Path | list,
    file_types: list[str],
    output_dir: str | Path,
    filename: str,
    file_exist_ok: bool = True,
    recursive: bool = True,
    exclude_patterns: list[str] = [".venv"],
    minimum_size: int = 50,
):
    persist_path = create_path(
        output_dir, filename, file_exist_ok=file_exist_ok
    )
    texts = []
    data_path = (
        [str(data_path)] if not isinstance(data_path, list) else data_path
    )
    data_path = sorted(data_path)
    data_path = [Path(dp) for dp in data_path if Path(dp).exists()]

    for dp in data_path:
        fps = dir_to_files(dp, recursive=recursive, file_types=file_types)

        data_path = sorted([str(i) for i in fps])
        data_path = [Path(dp) for dp in data_path if Path(dp).exists()]

        if exclude_patterns:
            for pattern in exclude_patterns:
                data_path = [fp for fp in data_path if pattern not in str(fp)]
        for fp in data_path:
            try:
                text = fp.read_text(encoding="utf-8")
            except Exception:
                continue

            if minimum_size > 0 and len(text) < minimum_size:
                continue

            texts.append("---")
            texts.append(str(fp))
            texts.append("---\n")
            texts.append(text)

    text = "\n".join(texts)
    persist_path.write_text(text, encoding="utf-8")
    print(f"Concatenated {len(fps)} files to {persist_path}")
    print(f"The file contains {len(text)} characters.")

    return texts, fps
