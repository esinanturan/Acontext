"use client";

import { useState, useRef, useEffect } from "react";
import { Tree, NodeRendererProps, TreeApi } from "react-arborist";
import { useTranslations } from "next-intl";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ChevronRight,
  File,
  Folder,
  FolderOpen,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getSpaces,
  getPages,
  getBlocks,
} from "@/api/models/space";
import { Space, Block } from "@/types";
import { BlockNoteEditor } from "@/components/blocknote-editor";

interface TreeNode {
  id: string;
  name: string;
  type: "page" | "block";
  blockType?: string;
  children?: TreeNode[];
  isLoaded?: boolean;
  blockData?: Block;
}

interface NodeProps extends NodeRendererProps<TreeNode> {
  loadingNodes: Set<string>;
}

function Node({ node, style, dragHandle, loadingNodes }: NodeProps) {
  const indent = node.level * 12;
  const isFolder = node.data.type === "page";
  const isLoading = loadingNodes.has(node.id);

  return (
    <div
      ref={dragHandle}
      style={style}
      className={cn(
        "flex items-center cursor-pointer px-2 py-1.5 text-sm rounded-md transition-colors",
        "hover:bg-accent hover:text-accent-foreground",
        node.isSelected && "bg-accent text-accent-foreground"
      )}
      onClick={() => {
        if (isFolder) {
          node.toggle();
        } else {
          node.select();
        }
      }}
    >
      <div
        style={{ marginLeft: `${indent}px` }}
        className="flex items-center gap-1.5 flex-1 min-w-0"
      >
        {isFolder ? (
          <>
            {isLoading ? (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
            ) : (
              <ChevronRight
                className={cn(
                  "h-4 w-4 shrink-0 transition-transform duration-200",
                  node.isOpen && "rotate-90"
                )}
              />
            )}
            {node.isOpen ? (
              <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
            ) : (
              <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
          </>
        ) : (
          <>
            <span className="w-4" />
            <File className="h-4 w-4 shrink-0 text-muted-foreground" />
          </>
        )}
        <span className="min-w-0 truncate" title={node.data.name}>
          {node.data.name}
        </span>
      </div>
    </div>
  );
}

export default function PagesPage() {
  const t = useTranslations("pages");

  const treeRef = useRef<TreeApi<TreeNode>>(null);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [loadingNodes, setLoadingNodes] = useState<Set<string>>(new Set());
  const [treeData, setTreeData] = useState<TreeNode[]>([]);
  const [isInitialLoading, setIsInitialLoading] = useState(false);

  // Space related states
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [selectedSpace, setSelectedSpace] = useState<Space | null>(null);
  const [isLoadingSpaces, setIsLoadingSpaces] = useState(true);
  const [isRefreshingSpaces, setIsRefreshingSpaces] = useState(false);
  const [spaceFilterText, setSpaceFilterText] = useState("");

  // Blocks for BlockNote editor
  const [contentBlocks, setContentBlocks] = useState<Block[]>([]);
  const [isLoadingContent, setIsLoadingContent] = useState(false);

  const filteredSpaces = spaces.filter((space) =>
    space.id.toLowerCase().includes(spaceFilterText.toLowerCase())
  );

  const loadSpaces = async () => {
    try {
      setIsLoadingSpaces(true);
      const res = await getSpaces();
      if (res.code !== 0) {
        console.error(res.message);
        return;
      }
      setSpaces(res.data || []);
    } catch (error) {
      console.error("Failed to load spaces:", error);
    } finally {
      setIsLoadingSpaces(false);
    }
  };

  useEffect(() => {
    loadSpaces();
  }, []);

  const handleSpaceSelect = async (space: Space) => {
    setSelectedSpace(space);
    setTreeData([]);
    setSelectedNode(null);
    setContentBlocks([]);

    try {
      setIsInitialLoading(true);
      const res = await getPages(space.id);
      if (res.code !== 0) {
        console.error(res.message);
        return;
      }

      const pages: TreeNode[] = (res.data || []).map((block) => ({
        id: block.id,
        name: block.title || "Untitled",
        type: "page" as const,
        blockType: block.type,
        isLoaded: false,
        blockData: block,
      }));

      setTreeData(pages);
    } catch (error) {
      console.error("Failed to load pages:", error);
    } finally {
      setIsInitialLoading(false);
    }
  };

  const handleToggle = async (nodeId: string) => {
    const node = treeRef.current?.get(nodeId);
    if (!node || node.data.type !== "page" || !selectedSpace) return;

    if (node.data.isLoaded) return;

    setLoadingNodes((prev) => new Set(prev).add(nodeId));

    try {
      // Load children pages using parent_id parameter
      const childrenRes = await getPages(selectedSpace.id, node.data.id);
      if (childrenRes.code !== 0) {
        console.error(childrenRes.message);
        return;
      }

      const children: TreeNode[] = (childrenRes.data || []).map((block: Block) => ({
        id: block.id,
        name: block.title || "Untitled",
        type: block.type === "page" ? "page" : "block",
        blockType: block.type,
        isLoaded: false,
        blockData: block,
      }));

      setTreeData((prevData) => {
        const updateNode = (nodes: TreeNode[]): TreeNode[] => {
          return nodes.map((n) => {
            if (n.id === nodeId) {
              return {
                ...n,
                children,
                isLoaded: true,
              };
            }
            if (n.children) {
              return {
                ...n,
                children: updateNode(n.children),
              };
            }
            return n;
          });
        };
        return updateNode(prevData);
      });
    } catch (error) {
      console.error("Failed to load children:", error);
    } finally {
      setLoadingNodes((prev) => {
        const next = new Set(prev);
        next.delete(nodeId);
        return next;
      });
    }
  };

  const handleSelect = async (nodes: { data: TreeNode }[]) => {
    const node = nodes[0];
    if (!node) return;

    setSelectedNode(node.data);

    // If it's a page, load its non-page blocks for display
    if (node.data.type === "page" && selectedSpace) {
      try {
        setIsLoadingContent(true);
        const blocksRes = await getBlocks(selectedSpace.id, node.data.id);
        if (blocksRes.code !== 0) {
          console.error(blocksRes.message);
          return;
        }

        // Filter to only non-page blocks
        const nonPageBlocks = (blocksRes.data || []).filter(
          (block) => block.type !== "page"
        );
        setContentBlocks(nonPageBlocks);
      } catch (error) {
        console.error("Failed to load blocks:", error);
      } finally {
        setIsLoadingContent(false);
      }
    }
  };

  const handleRefreshSpaces = async () => {
    setIsRefreshingSpaces(true);
    await loadSpaces();
    setIsRefreshingSpaces(false);
  };

  return (
    <div className="h-full bg-background p-6">
      <ResizablePanelGroup direction="horizontal">
        {/* Left: Space List */}
        <ResizablePanel defaultSize={25} minSize={15} maxSize={35}>
          <div className="h-full flex flex-col space-y-4 pr-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">{t("spaces")}</h2>
              <Button
                variant="outline"
                size="icon"
                onClick={handleRefreshSpaces}
                disabled={isRefreshingSpaces || isLoadingSpaces}
                title={t("refresh")}
              >
                {isRefreshingSpaces ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
            </div>

            <Input
              type="text"
              placeholder={t("filterById")}
              value={spaceFilterText}
              onChange={(e) => setSpaceFilterText(e.target.value)}
            />

            <div className="flex-1 overflow-auto">
              {isLoadingSpaces ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : filteredSpaces.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-sm text-muted-foreground">
                    {spaces.length === 0 ? t("noData") : t("noMatching")}
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredSpaces.map((space) => {
                    const isSelected = selectedSpace?.id === space.id;
                    return (
                      <div
                        key={space.id}
                        className={cn(
                          "group relative rounded-md border p-3 cursor-pointer transition-colors hover:bg-accent",
                          isSelected && "bg-accent border-primary"
                        )}
                        onClick={() => handleSpaceSelect(space)}
                      >
                        <div className="flex-1 min-w-0">
                          <p
                            className="text-sm font-medium truncate font-mono"
                            title={space.id}
                          >
                            {space.id}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(space.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />

        {/* Center: Page Tree */}
        <ResizablePanel defaultSize={30} minSize={20} maxSize={40}>
          <div className="h-full flex flex-col px-4">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">{t("pagesTitle")}</h2>
            </div>

            <div className="flex-1 overflow-auto">
              {!selectedSpace ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-sm text-muted-foreground">
                    {t("selectSpacePrompt")}
                  </p>
                </div>
              ) : isInitialLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      {t("loadingPages")}
                    </p>
                  </div>
                </div>
              ) : treeData.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-sm text-muted-foreground">
                    {t("noPages")}
                  </p>
                </div>
              ) : (
                <Tree
                  ref={treeRef}
                  data={treeData}
                  openByDefault={false}
                  width="100%"
                  height={750}
                  indent={12}
                  rowHeight={32}
                  onToggle={handleToggle}
                  onSelect={handleSelect}
                >
                  {(props) => <Node {...props} loadingNodes={loadingNodes} />}
                </Tree>
              )}
            </div>
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />

        {/* Right: BlockNote Editor */}
        <ResizablePanel>
          <div className="h-full overflow-auto pl-4">
            <h2 className="mb-4 text-lg font-semibold">{t("contentTitle")}</h2>
            <div className="rounded-md border bg-card p-6">
              {!selectedNode ? (
                <p className="text-sm text-muted-foreground">
                  {t("selectPagePrompt")}
                </p>
              ) : isLoadingContent ? (
                <div className="flex items-center justify-center h-64">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : contentBlocks.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {t("noBlocks")}
                </p>
              ) : (
                <BlockNoteEditor blocks={contentBlocks} editable={false} />
              )}
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}

