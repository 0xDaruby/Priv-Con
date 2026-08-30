import { RemoveFileIcon, ToolFileIcon } from "@/components/icons/PrivConIcons";
import { formatBytes } from "@/lib/format";
import type { SelectedFile, ToolConfig } from "@/lib/types";

interface FileListPreviewProps {
  readonly config: ToolConfig;
  readonly files: readonly SelectedFile[];
  readonly onRemove: (id: string) => void;
}

export function FileListPreview({
  config,
  files,
  onRemove,
}: FileListPreviewProps) {
  return (
    <ol className="file-list" aria-label="Selected files">
      {files.map(({ id, file }, index) => (
        <li className="file-row" key={id}>
          {config.reorderable ? (
            <span className="file-position" aria-label={`Position ${index + 1}`}>
              {index + 1}
            </span>
          ) : null}
          <span className="file-row-icon" aria-hidden="true">
            <ToolFileIcon name={config.icon} />
          </span>
          <span className="file-details">
            <strong title={file.name}>{file.name}</strong>
            <span>{formatBytes(file.size)}</span>
          </span>
          <button
            aria-label={`Remove ${file.name}`}
            className="remove-file"
            onClick={() => onRemove(id)}
            type="button"
          >
            <RemoveFileIcon />
            <span>Remove</span>
          </button>
        </li>
      ))}
    </ol>
  );
}
