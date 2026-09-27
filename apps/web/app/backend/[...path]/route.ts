import { NextRequest, NextResponse } from "next/server";

const UPSTREAM = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const url = new URL(path.join("/"), `${UPSTREAM.replace(/\/$/, "")}/`);
  url.search = request.nextUrl.search;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);
  const accept = request.headers.get("accept");
  if (accept) headers.set("accept", accept);
  const userAgent = request.headers.get("user-agent");
  if (userAgent) headers.set("user-agent", userAgent);

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  const upstream = await fetch(url, {
    method: request.method,
    headers,
    body,
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("transfer-encoding");
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("set-cookie");
  // Buffer before building the response. Appending Set-Cookie onto a streamed
  // body is ignored on Vercel, so the login succeeds and the next page has
  // no session cookie and sends the browser back to sign-in.
  const payload = await upstream.arrayBuffer();
  const response = new NextResponse(payload, {
    status: upstream.status,
    headers: responseHeaders,
  });
  for (const line of upstream.headers.getSetCookie()) {
    const parsed = parseSetCookie(line);
    if (!parsed) continue;
    response.cookies.set(parsed.name, parsed.value, parsed.options);
  }
  return response;
}

function parseSetCookie(line: string): {
  name: string;
  value: string;
  options: {
    path: string;
    httpOnly: boolean;
    secure: boolean;
    sameSite: "lax" | "strict" | "none";
    maxAge?: number;
  };
} | null {
  const [pair, ...attrs] = line.split(";").map((part) => part.trim());
  const eq = pair.indexOf("=");
  if (eq < 1) return null;
  const options: {
    path: string;
    httpOnly: boolean;
    secure: boolean;
    sameSite: "lax" | "strict" | "none";
    maxAge?: number;
  } = { path: "/", httpOnly: false, secure: false, sameSite: "lax" };
  for (const attr of attrs) {
    const [rawKey, rawValue] = attr.split("=");
    const key = rawKey.toLowerCase();
    if (key === "path" && rawValue) options.path = rawValue;
    else if (key === "httponly") options.httpOnly = true;
    else if (key === "secure") options.secure = true;
    else if (key === "max-age" && rawValue) options.maxAge = Number(rawValue);
    else if (key === "samesite" && rawValue) {
      const site = rawValue.toLowerCase();
      if (site === "lax" || site === "strict" || site === "none") options.sameSite = site;
    }
  }
  return { name: pair.slice(0, eq), value: pair.slice(eq + 1), options };
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
