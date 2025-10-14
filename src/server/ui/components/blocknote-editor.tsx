"use client";

import { useEffect, useMemo } from "react";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/shadcn";
import { Block } from "@/types";
import "@blocknote/shadcn/style.css";

interface BlockNoteEditorProps {
  blocks: Block[];
  editable?: boolean;
  onChange?: (blocks: Block[]) => void;
}

export function BlockNoteEditor({
  blocks,
  editable = false,
  onChange,
}: BlockNoteEditorProps) {
  // Transform Block[] to BlockNote schema format
  const initialContent = useMemo(() => {
    return blocks.map((block) => {
      const content = block.props?.content || block.title || "";
      return {
        id: block.id,
        type: block.type === "text" ? "paragraph" : block.type,
        content: typeof content === "string" ? content : "",
        children: [],
        props: block.props || {},
      };
    });
  }, [blocks]);

  const editor = useCreateBlockNote({
    initialContent: initialContent.length > 0 ? initialContent : undefined,
  });

  useEffect(() => {
    if (editor && initialContent.length > 0) {
      // Update editor content when blocks change
      // @ts-expect-error - BlockNote type definitions are complex, our Block format needs type casting
      editor.replaceBlocks(editor.document, initialContent);
    }
  }, [editor, initialContent]);

  return (
    <div className="blocknote-editor-container">
      <BlockNoteView
        editor={editor}
        editable={editable}
        theme="light"
        onChange={() => {
          if (onChange && editable) {
            // Convert BlockNote blocks back to our Block format
            // This is a placeholder for future editing functionality
            // const updatedBlocks = editor.document.map((bnBlock) => ({
            //   id: bnBlock.id,
            //   type: bnBlock.type,
            //   title: "",
            //   props: { content: bnBlock.content, ...bnBlock.props },
            // }));
            // onChange(updatedBlocks);
          }
        }}
      />
    </div>
  );
}

