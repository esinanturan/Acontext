import Link from 'fumadocs-core/link';
import { source } from '@/lib/source';
import type { ReactNode } from 'react';

export interface Suggestion {
  url: string;
  title: ReactNode;
  description?: string;
}

function getSuggestions(slug: string[]): Suggestion[] {
  const query = slug.join(' ').toLowerCase();
  const pages = source.getPages();

  const scored = pages
    .map((page) => {
      const title = (page.data.title ?? '').toLowerCase();
      const desc = (page.data.description ?? '').toLowerCase();
      const pageSlug = page.slugs.join(' ').toLowerCase();

      let score = 0;
      for (const word of query.split(/[\s\-_/]+/)) {
        if (!word) continue;
        if (title.includes(word)) score += 3;
        if (pageSlug.includes(word)) score += 2;
        if (desc.includes(word)) score += 1;
      }

      return { page, score };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  return scored.map((item) => ({
    url: item.page.url,
    title: item.page.data.title,
    description: item.page.data.description ?? undefined,
  }));
}

export function NotFound({ slug }: { slug?: string[] }) {
  const suggestions = slug ? getSuggestions(slug) : [];

  return (
    <div className="flex flex-col items-center justify-center text-center gap-4 p-8 [grid-area:main]">
      <h1 className="text-4xl font-bold font-mono">404</h1>
      <p className="text-fd-muted-foreground">This page could not be found.</p>
      <div className="w-full max-w-[500px]">
        {suggestions.length > 0 ? (
          <>
            <p className="text-sm text-fd-muted-foreground mb-3">
              Maybe you are looking for:
            </p>
            <div className="flex flex-col rounded-lg border bg-fd-card text-fd-card-foreground shadow-md overflow-hidden divide-y divide-fd-border">
              {suggestions.map((doc) => (
                <Link
                  key={doc.url}
                  href={doc.url}
                  className="inline-flex flex-col gap-0.5 text-sm px-4 py-3 hover:bg-fd-accent hover:text-fd-accent-foreground transition-colors"
                >
                  <span className="font-medium">{doc.title}</span>
                  {doc.description && (
                    <span className="text-xs text-fd-muted-foreground line-clamp-1">
                      {doc.description}
                    </span>
                  )}
                </Link>
              ))}
            </div>
          </>
        ) : (
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-lg border bg-fd-secondary px-4 py-2 text-sm font-medium transition-colors hover:bg-fd-accent hover:text-fd-accent-foreground"
          >
            Return to Home
          </Link>
        )}
      </div>
    </div>
  );
}
