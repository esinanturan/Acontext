'use client';

import {
  type ComponentProps,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Loader2, MessageCircleIcon, RefreshCw, Send, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { buttonVariants } from 'fumadocs-ui/components/ui/button';
import Link from 'fumadocs-core/link';
import { useChat, type UseChatHelpers } from '@ai-sdk/react';
import type { UIMessage } from 'ai';
import { DefaultChatTransport } from 'ai';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const Context = createContext<{
  open: boolean;
  setOpen: (open: boolean) => void;
  chat: UseChatHelpers<UIMessage>;
} | null>(null);

function useAISearchContext() {
  const ctx = useContext(Context);
  if (!ctx) throw new Error('AISearch components must be used within AISearch');
  return ctx;
}

function useChatContext() {
  return useAISearchContext().chat;
}

export function AISearchPanelHeader({
  className,
  ...props
}: ComponentProps<'div'>) {
  const { setOpen } = useAISearchContext();

  return (
    <div
      className={cn(
        'sticky top-0 flex items-start gap-2 border rounded-xl bg-fd-secondary text-fd-secondary-foreground shadow-sm',
        className
      )}
      {...props}
    >
      <div className="px-3 py-2 flex-1">
        <p className="text-sm font-medium mb-2">AI Chat</p>
        <p className="text-xs text-fd-muted-foreground">
          Ask anything about Acontext docs.
        </p>
      </div>
      <button
        aria-label="Close"
        tabIndex={-1}
        className={cn(
          buttonVariants({
            size: 'icon-sm',
            color: 'ghost',
            className: 'text-fd-muted-foreground rounded-full',
          })
        )}
        onClick={() => setOpen(false)}
      >
        <X />
      </button>
    </div>
  );
}

export function AISearchInputActions() {
  const { messages, status, setMessages, regenerate } = useChatContext();
  const isLoading = status === 'streaming';

  if (messages.length === 0) return null;

  return (
    <>
      {!isLoading && messages.at(-1)?.role === 'assistant' && (
        <button
          type="button"
          className={cn(
            buttonVariants({
              color: 'secondary',
              size: 'sm',
              className: 'rounded-full gap-1.5',
            })
          )}
          onClick={() => regenerate()}
        >
          <RefreshCw className="size-4" />
          Retry
        </button>
      )}
      <button
        type="button"
        className={cn(
          buttonVariants({
            color: 'secondary',
            size: 'sm',
            className: 'rounded-full',
          })
        )}
        onClick={() => setMessages([])}
      >
        Clear Chat
      </button>
    </>
  );
}

const StorageKeyInput = '__ai_search_input';

function Input(props: ComponentProps<'textarea'>) {
  const ref = useRef<HTMLDivElement>(null);
  const shared = cn('col-start-1 row-start-1', props.className);

  return (
    <div className="grid flex-1 min-w-0">
      <textarea
        id="nd-ai-input"
        {...props}
        className={cn(
          'resize-none bg-transparent placeholder:text-fd-muted-foreground focus-visible:outline-none',
          shared
        )}
      />
      <div ref={ref} className={cn(shared, 'break-all invisible')}>
        {`${props.value?.toString() ?? ''}\n`}
      </div>
    </div>
  );
}

export function AISearchInput(props: ComponentProps<'form'>) {
  const { status, sendMessage, stop } = useChatContext();
  const [input, setInput] = useState(
    () => (typeof window !== 'undefined' ? localStorage.getItem(StorageKeyInput) : null) ?? ''
  );
  const isLoading = status === 'streaming' || status === 'submitted';

  const onStart = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      if (input.trim()) {
        sendMessage({ text: input });
        setInput('');
      }
    },
    [input, sendMessage]
  );

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(StorageKeyInput, input);
    }
  }, [input]);

  useEffect(() => {
    if (isLoading) document.getElementById('nd-ai-input')?.focus();
  }, [isLoading]);

  return (
    <form
      {...props}
      className={cn('flex items-start pe-2', props.className)}
      onSubmit={onStart}
    >
      <Input
        value={input}
        placeholder={isLoading ? 'AI is answering...' : 'Ask a question'}
        autoFocus
        className="p-3"
        disabled={status === 'streaming' || status === 'submitted'}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (!e.shiftKey && e.key === 'Enter') onStart(e);
        }}
      />
      {isLoading ? (
        <button
          key="bn"
          type="button"
          className={cn(
            buttonVariants({
              color: 'secondary',
              className: 'transition-all rounded-full mt-2 gap-2',
            })
          )}
          onClick={stop}
        >
          <Loader2 className="size-4 animate-spin text-fd-muted-foreground" />
          Abort Answer
        </button>
      ) : (
        <button
          key="bn"
          type="submit"
          className={cn(
            buttonVariants({
              color: 'primary',
              className: 'transition-all rounded-full mt-2',
            })
          )}
          disabled={input.length === 0}
        >
          <Send className="size-4" />
        </button>
      )}
    </form>
  );
}

function List(props: Omit<ComponentProps<'div'>, 'dir'>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const callback = () => {
      container.scrollTo({ top: container.scrollHeight, behavior: 'instant' });
    };
    const observer = new ResizeObserver(callback);
    callback();
    const el = container.firstElementChild;
    if (el) observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={containerRef}
      {...props}
      className={cn(
        'fd-scroll-container overflow-y-auto min-w-0 flex flex-col',
        props.className
      )}
    >
      {props.children}
    </div>
  );
}

const roleName: Record<string, string> = {
  user: 'you',
  assistant: 'Acontext',
};

function ChatMessageContent({ text }: { text: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none [&_pre]:rounded-lg [&_pre]:bg-fd-muted [&_pre]:p-3 [&_pre]:text-xs [&_a]:text-fd-primary [&_a]:underline [&_ul]:my-2 [&_ol]:my-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) =>
            href?.startsWith('/') ? (
              <Link href={href}>{children}</Link>
            ) : (
              <a href={href} target="_blank" rel="noreferrer noopener">
                {children}
              </a>
            ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

function Message({ message }: { message: UIMessage } & ComponentProps<'div'>) {
  let markdown = '';
  for (const part of message.parts ?? []) {
    if (part.type === 'text') markdown += part.text;
  }

  return (
    <div onClick={(e) => e.stopPropagation()}>
      <p
        className={cn(
          'mb-1 text-sm font-medium text-fd-muted-foreground',
          message.role === 'assistant' && 'text-fd-primary'
        )}
      >
        {roleName[message.role] ?? 'unknown'}
      </p>
      <div className="prose text-sm">
        <ChatMessageContent text={markdown} />
      </div>
    </div>
  );
}

export function AISearch({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const chat = useChat({
    id: 'search',
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  });

  return (
    <Context.Provider value={useMemo(() => ({ chat, open, setOpen }), [chat, open])}>
      {children}
    </Context.Provider>
  );
}

export function AISearchTrigger({
  position = 'float',
  className,
  ...props
}: ComponentProps<'button'> & { position?: 'float' | 'inline' }) {
  const { open, setOpen } = useAISearchContext();

  return (
    <button
      data-state={open ? 'open' : 'closed'}
      type="button"
      className={cn(
        position === 'float' && [
          'fixed bottom-4 right-4 md:bottom-6 md:right-6 gap-2 shadow-lg z-20 transition-[translate,opacity]',
          open && 'translate-y-10 opacity-0',
        ],
        'inline-flex items-center justify-center rounded-2xl border bg-fd-secondary px-4 py-2.5 text-sm font-medium text-fd-muted-foreground transition-colors hover:bg-fd-accent hover:text-fd-accent-foreground',
        className
      )}
      onClick={() => setOpen(!open)}
      {...props}
    >
      {props.children}
    </button>
  );
}

export function useHotKey() {
  const { open, setOpen } = useAISearchContext();

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        setOpen(false);
        e.preventDefault();
      }
      if (e.key === '/' && (e.metaKey || e.ctrlKey) && !open) {
        setOpen(true);
        e.preventDefault();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, setOpen]);
}

export function AISearchPanel() {
  const { open, setOpen } = useAISearchContext();
  useHotKey();

  return (
    <>
      <style>
        {`
        @keyframes ask-ai-open {
          from { translate: 100% 0; }
          to { translate: 0 0; }
        }
        @keyframes ask-ai-close {
          from { width: var(--ai-chat-width); }
          to { width: 0px; }
        }`}
      </style>
      {open && (
        <div
          className="fixed inset-0 z-30 backdrop-blur-sm bg-black/20 lg:hidden"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}
      {open && (
        <div
          className={cn(
            'overflow-hidden z-30 bg-fd-card text-fd-card-foreground [--ai-chat-width:400px] 2xl:[--ai-chat-width:460px]',
            'max-lg:fixed max-lg:inset-x-2 max-lg:top-4 max-lg:border max-lg:rounded-2xl max-lg:shadow-xl',
            'lg:sticky lg:top-0 lg:h-dvh lg:border-s lg:ms-auto lg:in-[#nd-docs-layout]:[grid-area:toc]',
            'animate-in slide-in-from-right-2 duration-200',
            'lg:animate-[ask-ai-open_200ms]'
          )}
        >
          <div className="flex flex-col size-full p-2 max-lg:max-h-[80dvh] lg:p-3 lg:w-(--ai-chat-width)">
            <AISearchPanelHeader />
            <AISearchPanelList className="flex-1" />
            <div className="rounded-xl border bg-fd-secondary text-fd-secondary-foreground shadow-sm focus-within:shadow-md">
              <AISearchInput />
              <div className="flex items-center gap-1.5 p-1 empty:hidden">
                <AISearchInputActions />
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function AISearchPanelList({
  className,
  style,
  ...props
}: ComponentProps<'div'>) {
  const chat = useChatContext();
  const messages = chat.messages.filter((msg) => msg.role !== 'system');

  return (
    <List
      className={cn('py-4 overscroll-contain', className)}
      style={{
        maskImage:
          'linear-gradient(to bottom, transparent, white 1rem, white calc(100% - 1rem), transparent 100%)',
        ...style,
      }}
      {...props}
    >
      {messages.length === 0 ? (
        <div className="text-sm text-fd-muted-foreground/80 size-full flex flex-col items-center justify-center text-center gap-2">
          <MessageCircleIcon fill="currentColor" stroke="none" />
          <p>Start a new chat below.</p>
        </div>
      ) : (
        <div className="flex flex-col px-3 gap-4">
          {messages.map((item) => (
            <Message key={item.id} message={item} />
          ))}
          {(chat.status === 'submitted' || chat.status === 'streaming') && (
            <div className="flex items-center gap-2 text-sm text-fd-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              <span>
                {chat.status === 'submitted' ? 'Thinking...' : 'Streaming...'}
              </span>
            </div>
          )}
          {chat.error && (
            <p className="text-sm text-red-500" title={String(chat.error)}>
              {chat.error instanceof Error
                ? chat.error.message
                : typeof chat.error === 'string'
                  ? chat.error
                  : 'Something went wrong. Please try again.'}
            </p>
          )}
        </div>
      )}
    </List>
  );
}
