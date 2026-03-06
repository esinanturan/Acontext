import { streamText, convertToModelMessages } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import type { UIMessage } from 'ai';
import { getLLMText, source } from '@/lib/source';

export const maxDuration = 30;

const isDev = process.env.NODE_ENV === 'development';
const PRODUCTION_ORIGIN = 'https://docs.acontext.io';

function getAllowedOrigins(): string[] {
  const env = process.env.AI_CHAT_ALLOWED_ORIGINS;
  if (!env) return [PRODUCTION_ORIGIN];
  return env.split(',').map((o) => o.trim()).filter(Boolean);
}

function isOriginAllowed(origin: string | null): boolean {
  if (!origin) return true;
  if (isDev) return true;
  return getAllowedOrigins().includes(origin);
}

const systemPrompt = `You are a helpful AI assistant for Acontext documentation. Answer questions based on the following documentation. If the answer is not in the docs, say so and suggest checking the official docs at https://docs.acontext.io.

Documentation:
`;

async function getDocsContext(): Promise<string> {
  const scan = source.getPages().map(getLLMText);
  const scanned = await Promise.all(scan);
  return scanned.join('\n\n');
}

function corsHeaders(origin: string | null): Record<string, string> {
  if (!origin) return {};
  if (!isOriginAllowed(origin)) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

export async function OPTIONS(req: Request) {
  const origin = req.headers.get('Origin');
  const allowOrigin = isDev
    ? (origin ?? '*')
    : (origin && isOriginAllowed(origin) ? origin : PRODUCTION_ORIGIN);
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': allowOrigin,
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400',
    },
  });
}

export async function POST(req: Request) {
  const origin = req.headers.get('Origin');
  if (!isOriginAllowed(origin)) {
    return new Response(
      JSON.stringify({ error: 'Origin not allowed', origin }),
      { status: 403, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
    );
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return new Response(
      JSON.stringify({
        error: 'OPENAI_API_KEY is not configured. Add it to your environment variables.',
      }),
      { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
    );
  }

  try {
    const body = await req.json();
    const messages = body?.messages as UIMessage[] | undefined;
    if (!Array.isArray(messages)) {
      return new Response(
        JSON.stringify({ error: 'Invalid request: messages array required' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
      );
    }

    const docsContext = await getDocsContext();
    const fullSystemPrompt = systemPrompt + docsContext;

    const baseURL = process.env.OPENAI_BASE_URL ?? process.env.AI_CHAT_BASE_URL;
    const modelId = process.env.AI_CHAT_MODEL ?? process.env.OPENAI_MODEL ?? 'gpt-4o-mini';

    const openai = createOpenAI({
      apiKey,
      ...(baseURL && { baseURL }),
    });
    const model = openai(modelId);

    const result = streamText({
      model,
      system: fullSystemPrompt,
      messages: await convertToModelMessages(messages),
    });

    const response = result.toUIMessageStreamResponse();
    const headers = new Headers(response.headers);
    if (origin) {
      headers.set('Access-Control-Allow-Origin', origin);
    }
    return new Response(response.body, { status: response.status, headers });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error('[api/chat]', err);
    return new Response(
      JSON.stringify({ error: 'Chat request failed', detail: message }),
      { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) } }
    );
  }
}
