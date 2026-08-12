/**
 * Typed OpenAPI contract for Studio Sunny HQ.
 * Regenerate from FastAPI with:
 *   backend: python -m scripts.export_openapi
 *   frontend: npx openapi-typescript openapi.json -o lib/api-schema.d.ts
 *
 * This file is the committed source of truth until codegen is wired in CI.
 */
import type { ChatChannel, ChatMessage, Task } from "./api";

export interface paths {
  "/api/v1/chat/channels": {
    get: {
      responses: {
        200: { content: { "application/json": ChatChannel[] } };
      };
    };
  };
  "/api/v1/chat/channels/{slug}/messages": {
    get: {
      parameters: { path: { slug: string } };
      responses: {
        200: { content: { "application/json": ChatMessage[] } };
      };
    };
    post: {
      parameters: { path: { slug: string } };
      requestBody: { content: { "application/json": { body: string } } };
      responses: {
        201: { content: { "application/json": ChatMessage } };
      };
    };
  };
  "/api/v1/tasks": {
    get: {
      parameters: { query?: { mine?: boolean; project_id?: string; status?: string } };
      responses: {
        200: { content: { "application/json": Task[] } };
      };
    };
    post: {
      requestBody: { content: { "application/json": Record<string, unknown> } };
      responses: {
        201: { content: { "application/json": Task } };
      };
    };
  };
  "/api/v1/tasks/{task_id}": {
    patch: {
      parameters: { path: { task_id: string } };
      requestBody: { content: { "application/json": { status?: string } } };
      responses: {
        200: { content: { "application/json": Task } };
      };
    };
  };
  "/api/v1/audit": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": {
              id: string;
              user_id: string | null;
              action: string;
              entity_type: string;
              entity_id: string | null;
              ip_address: string | null;
              meta: Record<string, unknown>;
              created_at: string;
            }[];
          };
        };
      };
    };
  };
  "/api/v1/docs": {
    get: {
      parameters: { query?: { q?: string; project_id?: string; client_id?: string; kind?: string } };
      responses: {
        200: { content: { "application/json": import("./api").DocListItem[] } };
      };
    };
    post: {
      requestBody: { content: { "application/json": Record<string, unknown> } };
      responses: {
        201: { content: { "application/json": import("./api").Doc } };
      };
    };
  };
  "/api/v1/docs/{doc_id}": {
    get: {
      parameters: { path: { doc_id: string } };
      responses: {
        200: { content: { "application/json": import("./api").Doc } };
      };
    };
    patch: {
      parameters: { path: { doc_id: string } };
      requestBody: { content: { "application/json": Record<string, unknown> } };
      responses: {
        200: { content: { "application/json": import("./api").Doc } };
      };
    };
    delete: {
      parameters: { path: { doc_id: string } };
      responses: { 204: { content: never } };
    };
  };
}
