'use client';

import { RootProvider } from 'fumadocs-ui/provider/base';
import dynamic from 'next/dynamic';
import type { ReactNode } from 'react';

const SearchDialog = dynamic(() => import('@/components/search-dialog'), {
  ssr: false,
});

export function Providers({ children }: { children: ReactNode }) {
  return (
    <RootProvider
      search={{
        SearchDialog,
        options: {
          type: 'static',
        },
      }}
    >
      {children}
    </RootProvider>
  );
}
