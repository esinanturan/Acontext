import { createApiResponse, createApiError } from "@/lib/api-response";
import { GetFileResp } from "@/types";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ artifact_id: string }> }
) {
  const artifact_id = (await params).artifact_id;
  if (!artifact_id) {
    return createApiError("artifact_id is required");
  }

  const { searchParams } = new URL(req.url);
  const file_path = searchParams.get("file_path") || "";
  if (!file_path) {
    return createApiError("file_path is required");
  }

  const getFile = new Promise<GetFileResp>(async (resolve, reject) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_SERVER_URL}/api/v1/artifact/${artifact_id}/file?file_path=${file_path}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer sk-ac-${process.env.ROOT_API_BEARER_TOKEN}`,
          },
        }
      );
      if (response.status !== 200) {
        reject(new Error("Internal Server Error"));
      }

      const result = await response.json();
      if (result.code !== 0) {
        reject(new Error(result.message));
      }
      resolve(result.data);
    } catch {
      reject(new Error("Internal Server Error"));
    }
  });

  try {
    const res = await getFile;
    return createApiResponse(res || {});
  } catch (error) {
    console.error(error);
    return createApiError("Internal Server Error");
  }
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ artifact_id: string }> }
) {
  const artifact_id = (await params).artifact_id;
  if (!artifact_id) {
    return createApiError("artifact_id is required");
  }

  try {
    const formData = await req.formData();
    const file = formData.get("file");
    const file_path = formData.get("file_path");
    const meta = formData.get("meta");

    if (!file || !(file instanceof File)) {
      return createApiError("file is required");
    }

    if (!file_path || typeof file_path !== "string") {
      return createApiError("file_path is required");
    }

    // Create new FormData to forward to backend
    const backendFormData = new FormData();
    backendFormData.append("file", file);
    backendFormData.append("file_path", file_path);

    // Add meta if provided
    if (meta && typeof meta === "string") {
      backendFormData.append("meta", meta);
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_SERVER_URL}/api/v1/artifact/${artifact_id}/file`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer sk-ac-${process.env.ROOT_API_BEARER_TOKEN}`,
        },
        body: backendFormData,
      }
    );

    if (response.status !== 201) {
      const result = await response.json();
      return createApiError(result.message || "Failed to upload file");
    }

    const result = await response.json();
    if (result.code !== 0) {
      return createApiError(result.message);
    }

    return createApiResponse(result.data || {});
  } catch (error) {
    console.error("Upload error:", error);
    return createApiError("Internal Server Error");
  }
}

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ artifact_id: string }> }
) {
  const artifact_id = (await params).artifact_id;
  if (!artifact_id) {
    return createApiError("artifact_id is required");
  }

  const { searchParams } = new URL(req.url);
  const file_path = searchParams.get("file_path");

  if (!file_path) {
    return createApiError("file_path is required");
  }

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_SERVER_URL}/api/v1/artifact/${artifact_id}/file?file_path=${encodeURIComponent(file_path)}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer sk-ac-${process.env.ROOT_API_BEARER_TOKEN}`,
        },
      }
    );

    if (response.status !== 200) {
      const result = await response.json();
      return createApiError(result.message || "Failed to delete file");
    }

    const result = await response.json();
    if (result.code !== 0) {
      return createApiError(result.message);
    }

    return createApiResponse({});
  } catch (error) {
    console.error("Delete error:", error);
    return createApiError("Internal Server Error");
  }
}
