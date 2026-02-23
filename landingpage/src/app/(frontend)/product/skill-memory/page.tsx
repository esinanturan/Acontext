import Script from 'next/script'
import type { Metadata } from 'next'
import { Hero, Comparison, Advantages, HowItWorks } from '@/components/skill-memory'
import { createSoftwareApplicationJsonLd, generateJsonLdScript } from '@/lib/jsonld'

const baseUrl = process.env.NEXT_PUBLIC_SERVER_URL || 'https://acontext.io'

export const metadata: Metadata = {
  title: 'Skill Memory - Agent Memory as Skills | Acontext',
  description:
    'Agent memory stored as skills — filesystem-compatible, configurable, and human-readable. No opaque embeddings. No vendor lock-in.',
  keywords: [
    'skill memory',
    'agent memory',
    'AI agent',
    'filesystem memory',
    'human-readable memory',
    'open source',
  ],
  openGraph: {
    title: 'Skill Memory - Agent Memory as Skills | Acontext',
    description:
      'Agent memory stored as skills — filesystem-compatible, configurable, and human-readable.',
    url: `${baseUrl}/product/skill-memory`,
    siteName: 'Acontext',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Skill Memory - Agent Memory as Skills | Acontext',
    description:
      'Agent memory stored as skills — filesystem-compatible, configurable, and human-readable.',
  },
  alternates: {
    canonical: `${baseUrl}/product/skill-memory`,
  },
}

export default function SkillMemoryPage() {
  const skillMemoryJsonLd = createSoftwareApplicationJsonLd(
    'Acontext Skill Memory',
    'Skill memory for AI agents — store agent memory as filesystem-compatible, configurable, human-readable skill files.',
    `${baseUrl}/product/skill-memory`,
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
        id="skill-memory-jsonld"
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: generateJsonLdScript(skillMemoryJsonLd),
        }}
      />
      <Hero />
      <Advantages />
      <Comparison />
      <HowItWorks />
    </>
  )
}
