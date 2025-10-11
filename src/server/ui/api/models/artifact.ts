import service, { Res } from "../http";
import { Artifact, ListFilesResp, GetFileResp } from "@/types";

export const getArtifacts = async (): Promise<Res<Artifact[]>> => {
  return await service.get("/api/artifact");
};

export const getListFiles = async (
  artifact_id: string,
  path: string
): Promise<Res<ListFilesResp>> => {
  return await service.get(`/api/artifact/${artifact_id}/file/ls?path=${path}`);
};

export const getFile = async (
  artifact_id: string,
  file_path: string
): Promise<Res<GetFileResp>> => {
  return await service.get(
    `/api/artifact/${artifact_id}/file?file_path=${file_path}`
  );
};

export const createArtifact = async (): Promise<Res<Artifact>> => {
  return await service.post("/api/artifact");
};

export const deleteArtifact = async (
  artifact_id: string
): Promise<Res<null>> => {
  return await service.delete(`/api/artifact/${artifact_id}`);
};

export const uploadFile = async (
  artifact_id: string,
  file_path: string,
  file: File,
  meta?: Record<string, string>
): Promise<Res<null>> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("file_path", file_path);
  if (meta && Object.keys(meta).length > 0) {
    formData.append("meta", JSON.stringify(meta));
  }

  const response = await fetch(`/api/artifact/${artifact_id}/file`, {
    method: "POST",
    body: formData,
  });

  return await response.json();
};

export const deleteFile = async (
  artifact_id: string,
  file_path: string
): Promise<Res<null>> => {
  return await service.delete(
    `/api/artifact/${artifact_id}/file?file_path=${encodeURIComponent(
      file_path
    )}`
  );
};
