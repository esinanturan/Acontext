'use client';

import {
  SearchDialog,
  SearchDialogClose,
  SearchDialogContent,
  SearchDialogFooter,
  SearchDialogHeader,
  SearchDialogIcon,
  SearchDialogInput,
  SearchDialogList,
  SearchDialogOverlay,
  type SearchItemType,
  type SharedProps,
} from 'fumadocs-ui/components/dialog/search';
import { useDocsSearch } from 'fumadocs-core/search/client';
import { useMemo, useState } from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from 'fumadocs-ui/components/ui/popover';
import { ArrowRight, ChevronDown } from 'lucide-react';
import { buttonVariants } from 'fumadocs-ui/components/ui/button';
import { cn } from '@/lib/cn';
import { useTreeContext } from 'fumadocs-ui/contexts/tree';
import type { Item, Node } from 'fumadocs-core/page-tree';
import { useRouter } from 'next/navigation';

const filterItems = [
  { name: 'All', value: undefined, description: 'All documentation' },
  {
    name: 'Guides',
    value: 'guides',
    description: 'Getting started and how-to guides',
  },
  {
    name: 'API Reference',
    value: 'api-reference',
    description: 'REST API documentation',
  },
  {
    name: 'Integrations',
    value: 'integrations',
    description: 'Third-party integrations',
  },
];

function getSectionFromUrl(url: string): string {
  const path = url.replace(/^\//, '');
  const [first] = path.split('/');
  if (first === 'api-reference') return 'api-reference';
  if (first === 'integrations') return 'integrations';
  return 'guides';
}

export default function CustomSearchDialog(props: SharedProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [tag, setTag] = useState<string | undefined>();
  const { search, setSearch, query } = useDocsSearch({
    type: 'static',
    from: '/api/search',
  });

  const { full } = useTreeContext();
  const router = useRouter();

  const searchMap = useMemo(() => {
    const map = new Map<string, Item>();

    function onNode(node: Node) {
      if (node.type === 'page' && typeof node.name === 'string') {
        map.set(node.name.toLowerCase(), node);
      } else if (node.type === 'folder') {
        if (node.index) onNode(node.index);
        for (const item of node.children) onNode(item);
      }
    }

    for (const item of full.children) onNode(item);
    return map;
  }, [full]);

  const pageTreeAction = useMemo<SearchItemType | undefined>(() => {
    if (search.length === 0) return;

    const normalized = search.toLowerCase().trim();
    for (const [k, page] of searchMap) {
      if (!k.startsWith(normalized)) continue;

      return {
        id: 'quick-action',
        type: 'action',
        node: (
          <div className="inline-flex items-center gap-2 text-fd-muted-foreground">
            <ArrowRight className="size-4" />
            <p>
              Jump to{' '}
              <span className="font-medium text-fd-foreground">{page.name}</span>
            </p>
          </div>
        ),
        onSelect: () => router.push(page.url),
      };
    }
  }, [router, search, searchMap]);

  const filteredData = useMemo(() => {
    if (query.data === 'empty' || !Array.isArray(query.data)) return query.data;
    if (!tag) return query.data;

    return query.data.filter((item) => {
      if ('url' in item && typeof item.url === 'string') {
        return getSectionFromUrl(item.url) === tag;
      }
      return true;
    });
  }, [query.data, tag]);

  const items: SearchItemType[] | null =
    filteredData !== 'empty' || pageTreeAction
      ? [
          ...(pageTreeAction ? [pageTreeAction] : []),
          ...(Array.isArray(filteredData) ? filteredData : []),
        ]
      : null;

  return (
    <SearchDialog
      search={search}
      onSearchChange={setSearch}
      isLoading={query.isLoading}
      {...props}
    >
      <SearchDialogOverlay />
      <SearchDialogContent>
        <SearchDialogHeader>
          <SearchDialogIcon />
          <SearchDialogInput />
          <SearchDialogClose />
        </SearchDialogHeader>
        <SearchDialogList items={items} />
        <SearchDialogFooter className="flex flex-row flex-wrap gap-2 items-center">
          <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
            <PopoverTrigger
              className={buttonVariants({
                size: 'sm',
                color: 'ghost',
                className: '-m-1.5 me-auto',
              })}
            >
              <span className="text-fd-muted-foreground/80 me-2">Filter</span>
              {filterItems.find((item) => item.value === tag)?.name ?? 'All'}
              <ChevronDown className="size-3.5 text-fd-muted-foreground" />
            </PopoverTrigger>
            <PopoverContent className="flex flex-col p-1 gap-1" align="start">
              {filterItems.map((item) => {
                const isSelected = item.value === tag;

                return (
                  <button
                    key={item.value ?? 'all'}
                    onClick={() => {
                      setTag(item.value);
                      setPopoverOpen(false);
                    }}
                    className={cn(
                      'rounded-lg text-start px-2 py-1.5',
                      isSelected
                        ? 'text-fd-primary bg-fd-primary/10'
                        : 'hover:text-fd-accent-foreground hover:bg-fd-accent'
                    )}
                  >
                    <p className="font-medium mb-0.5">{item.name}</p>
                    <p className="text-xs opacity-70">{item.description}</p>
                  </button>
                );
              })}
            </PopoverContent>
          </Popover>
        </SearchDialogFooter>
      </SearchDialogContent>
    </SearchDialog>
  );
}
