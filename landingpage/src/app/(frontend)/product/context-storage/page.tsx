import Script from 'next/script'
import type { Metadata } from 'next'
import { Hero, Features, Comparison, HowItWorks } from '@/components/context-storage'
import { StandaloneComparison, scenes } from '@/components/landing/acontext-vs-claude'
import { createSoftwareApplicationJsonLd, generateJsonLdScript } from '@/lib/jsonld'

const baseUrl = process.env.NEXT_PUBLIC_SERVER_URL || 'https://acontext.io'

export const metadata: Metadata = {
  title: 'Context Storage - Messages, Files & Skills | Acontext',
  description:
    'Complete agent storage: multi-provider messages (OpenAI, Anthropic, Gemini), S3-backed disk storage with search, and reusable skill packages that agents discover and use.',
  keywords: [
    'context storage',
    'AI agent context',
    'session management',
    'multi-provider',
    'OpenAI',
    'Anthropic',
    'Gemini',
    'token optimization',
    'disk storage',
    'file storage',
    'agent skills',
    'skill packages',
    'skill tools',
  ],
  openGraph: {
    title: 'Context Storage - Messages, Files & Skills | Acontext',
    description:
      'Complete agent storage: multi-provider messages, S3-backed disk storage, and reusable skill packages in one platform.',
    url: `${baseUrl}/product/context-storage`,
    siteName: 'Acontext',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Context Storage - Messages, Files & Skills | Acontext',
    description:
      'Complete agent storage: multi-provider messages, S3-backed disk storage, and reusable skill packages in one platform.',
  },
  alternates: {
    canonical: `${baseUrl}/product/context-storage`,
  },
}

export default function ContextStoragePage() {
  const jsonLd = createSoftwareApplicationJsonLd(
    'Acontext Context Storage',
    'Complete agent storage — multi-provider messages, S3-backed disk storage with search, and reusable skill packages that agents discover and use.',
    `${baseUrl}/product/context-storage`,
    {
      applicationCategory: 'DeveloperApplication',
      operatingSystem: 'Any',
      price: '0',
      priceCurrency: 'USD',
    },
  )

  return (
    <>
      <Script
        id="context-storage-jsonld"
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: generateJsonLdScript(jsonLd),
        }}
      />
      <Hero />
      <Features />
      <StandaloneComparison scene={scenes[0]} />
      <Comparison />
      <HowItWorks />
    </>
  )
}
