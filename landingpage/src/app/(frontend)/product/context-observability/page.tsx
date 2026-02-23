import Script from 'next/script'
import type { Metadata } from 'next'
import { Hero, Features, Capabilities, HowItWorks } from '@/components/context-observability'
import { createSoftwareApplicationJsonLd, generateJsonLdScript } from '@/lib/jsonld'

const baseUrl = process.env.NEXT_PUBLIC_SERVER_URL || 'https://acontext.io'

export const metadata: Metadata = {
  title: 'Context Observability - Monitor AI Agent Sessions | Acontext',
  description:
    'Full observability into your AI agent sessions. Track agent tasks, traces, token usage, and session activity with built-in dashboards and analytics.',
  keywords: [
    'context observability',
    'AI agent monitoring',
    'agent tasks',
    'traces',
    'token usage',
    'session analytics',
    'dashboard',
  ],
  openGraph: {
    title: 'Context Observability - Monitor AI Agent Sessions | Acontext',
    description:
      'Full observability into your AI agent sessions. Track agent tasks, traces, and token usage.',
    url: `${baseUrl}/product/context-observability`,
    siteName: 'Acontext',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Context Observability - Monitor AI Agent Sessions | Acontext',
    description:
      'Full observability into your AI agent sessions. Track agent tasks, traces, and token usage.',
  },
  alternates: {
    canonical: `${baseUrl}/product/context-observability`,
  },
}

export default function ContextObservabilityPage() {
  const jsonLd = createSoftwareApplicationJsonLd(
    'Acontext Context Observability',
    'Full observability for AI agent sessions — track agent tasks, traces, token usage, and session analytics with built-in dashboards.',
    `${baseUrl}/product/context-observability`,
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
        id="context-observability-jsonld"
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: generateJsonLdScript(jsonLd),
        }}
      />
      <Hero />
      <Features />
      <Capabilities />
      <HowItWorks />
    </>
  )
}
