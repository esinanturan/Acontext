export interface Artifact {
  id: string;
  project_id: string;
  created_at: string;
  updated_at: string;
}

export interface File {
  artifact_id: string;
  path: string;
  filename: string;
  meta: {
    __file_info__: {
      filename: string;
      mime: string;
      path: string;
      size: number;
    };
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
}

export interface ListFilesResp {
  files: File[];
  directories: string[];
}

export interface GetFileResp {
  file: File;
  public_url: string | null;
}

export interface Space {
  id: string;
  project_id: string;
  configs: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Session {
  id: string;
  project_id: string;
  space_id: string | null;
  configs: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Part {
  type: string;
  text?: string;
  asset?: {
    bucket: string;
    s3_key: string;
    etag: string;
    sha256: string;
    mime: string;
    size_b: number;
  };
  filename?: string;
  meta?: Record<string, unknown>;
}

export interface Message {
  id: string;
  session_id: string;
  parent_id: string | null;
  role: string;
  parts: Part[];
  session_task_process_status: string;
  created_at: string;
  updated_at: string;
}

export interface GetMessagesResp {
  items: Message[];
  next_cursor?: string;
  has_more: boolean;
  public_urls?: Record<string, { url: string; expire_at: string }>;
}

export interface Block {
  id: string;
  space_id: string;
  type: string;
  parent_id: string | null;
  title: string;
  props: Record<string, unknown>;
  sort: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}
