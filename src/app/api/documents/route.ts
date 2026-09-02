import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const datasetId =
      searchParams.get("dataset_id") ||
      process.env.RAGFLOW_DATASET_IDS?.split(",")[0]?.trim() ||
      "d4d0e9c6a05c11f199bf45be651e52f0";
    const page = searchParams.get("page") || "1";
    const pageSize = searchParams.get("page_size") || "50";

    const apiKey = process.env.RAGFLOW_API_KEY || "";
    const ragflowUrl = `http://localhost/api/v1/datasets/${datasetId}/documents?page=${page}&page_size=${pageSize}`;

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
        { error: `Failed to fetch documents from RAGFlow: ${res.statusText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error fetching documents from RAGFlow:", error);
    return NextResponse.json(
      { error: error?.message || "Internal server error" },
      { status: 500 }
    );
  }
}
