import { buildGraph } from '@/lib/build-graph';
import { GraphView } from '@/components/graph-view';
import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Documentation Graph',
  description: 'Visual graph of all documentation pages and their relationships',
};

export default async function GraphPage() {
  const graph = await buildGraph();

  return (
    <div className="flex flex-col gap-4 p-6 max-w-[1200px] mx-auto">
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-fd-muted-foreground hover:text-fd-foreground transition-colors"
        >
          <ArrowLeft className="size-4" />
          Back to Docs
        </Link>
      </div>
      <div>
        <h1 className="text-2xl font-semibold mb-1">Documentation Graph</h1>
        <p className="text-sm text-fd-muted-foreground">
          Interactive visualization of all {graph.nodes.length} documentation pages.
          Hover to preview, click to navigate.
        </p>
      </div>
      <GraphView graph={graph} />
    </div>
  );
}
