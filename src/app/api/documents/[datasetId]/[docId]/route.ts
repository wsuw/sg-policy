import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ datasetId: string; docId: string }> }
) {
  try {
    const { datasetId, docId } = await params;

    if (!datasetId || !docId) {
      return NextResponse.json({ error: "Missing datasetId or docId" }, { status: 400 });
    }

    const apiKey = process.env.RAGFLOW_API_KEY || "";
    // RAGFlow document download endpoint
    const ragflowUrl = `http://localhost/api/v1/datasets/${datasetId}/documents/${docId}`;

    const headers: Record<string, string> = {};
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    const res = await fetch(ragflowUrl, {
      method: "GET",
      headers,
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Failed to fetch document from RAGFlow: ${res.statusText}` },
        { status: res.status }
      );
    }

    const contentType = res.headers.get("content-type") || "application/octet-stream";
    const contentDisposition = res.headers.get("content-disposition") || "";

    const buffer = await res.arrayBuffer();

    const responseHeaders: Record<string, string> = {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=3600",
    };
    if (contentDisposition) {
      responseHeaders["Content-Disposition"] = contentDisposition;
    }

    return new NextResponse(buffer, {
      status: 200,
      headers: responseHeaders,
    });
  } catch (error: any) {
    console.error("Error proxying document from RAGFlow:", error);
    return NextResponse.json(
      { error: error?.message || "Internal server error" },
      { status: 500 }
    );
  }
}
