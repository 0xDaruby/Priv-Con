"use client";

import { useState, type DragEvent, type KeyboardEvent } from "react";

import {
  DragHandleIcon,
  RemoveFileIcon,
  ToolFileIcon,
} from "@/components/icons/PrivConIcons";
import { formatBytes } from "@/lib/format";
import type { SelectedFile, ToolConfig } from "@/lib/types";

interface ReorderListProps {
  readonly config: ToolConfig;
  readonly items: readonly SelectedFile[];
  readonly onRemove: (id: string) => void;
  readonly onReorder: (items: readonly SelectedFile[]) => void;
}

function moveItem(
  items: readonly SelectedFile[],
  fromIndex: number,
  toIndex: number,
): readonly SelectedFile[] {
  if (fromIndex === toIndex || toIndex < 0 || toIndex >= items.length) return items;
  const next = [...items];
  const [moved] = next.splice(fromIndex, 1);
  if (!moved) return items;
  next.splice(toIndex, 0, moved);
  return next;
}

export function ReorderList({
  config,
  items,
  onRemove,
  onReorder,
}: ReorderListProps) {
  const [draggedId, setDraggedId] = useState<string>();
  const [announcement, setAnnouncement] = useState("");

  const moveByKeyboard = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    if (!event.altKey || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
    event.preventDefault();
    const direction = event.key === "ArrowUp" ? -1 : 1;
    const targetIndex = index + direction;
    const reordered = moveItem(items, index, targetIndex);
    onReorder(reordered);
    if (reordered !== items) {
      setAnnouncement(`${items[index]?.file.name} moved to position ${targetIndex + 1}.`);
    }
  };

  const handleDrop = (event: DragEvent<HTMLLIElement>, targetIndex: number) => {
    event.preventDefault();
    const sourceIndex = items.findIndex(({ id }) => id === draggedId);
    if (sourceIndex !== -1) {
      const reordered = moveItem(items, sourceIndex, targetIndex);
      onReorder(reordered);
      if (reordered !== items) {
        setAnnouncement(
          `${items[sourceIndex]?.file.name} moved to position ${targetIndex + 1}.`,
        );
      }
    }
    setDraggedId(undefined);
  };

  return (
    <div className="reorder-region">
      <p className="reorder-hint" id="reorder-hint">
        Drag to reorder, or focus a handle and press Alt + ↑ or ↓.
      </p>
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
      <ol className="file-list reorder-list" aria-describedby="reorder-hint">
        {items.map(({ id, file }, index) => (
          <li
            className="file-row reorder-row"
            data-dragging={draggedId === id || undefined}
            key={id}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => handleDrop(event, index)}
          >
            <button
              aria-label={`Move ${file.name}, position ${index + 1}. Use Alt plus up or down arrow to reorder.`}
              className="drag-handle"
              draggable
              onDragEnd={() => setDraggedId(undefined)}
              onDragStart={(event) => {
                setDraggedId(id);
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", id);
              }}
              onKeyDown={(event) => moveByKeyboard(event, index)}
              type="button"
            >
              <DragHandleIcon />
            </button>
            <span className="file-position" aria-label={`Position ${index + 1}`}>
              {index + 1}
            </span>
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
    </div>
  );
}
