/** Custom error classes for the USF TypeScript SDK. */

export class USFSDKError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly detail: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "USFSDKError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class AuthError extends USFSDKError {
  constructor(message = "Authentication required or token expired") {
    super(message, 401);
    this.name = "AuthError";
  }
}

export class ContextAmbiguousError extends USFSDKError {
  constructor(
    public readonly metric: string,
    public readonly availableContexts: string[],
    message?: string,
  ) {
    super(
      message ??
        `Metric '${metric}' is ambiguous. Set context to one of: ${availableContexts.join(", ")}`,
      409,
    );
    this.name = "ContextAmbiguousError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class NotFoundError extends USFSDKError {
  constructor(message = "Resource not found") {
    super(message, 404);
    this.name = "NotFoundError";
  }
}

export class AccessDeniedError extends USFSDKError {
  constructor(message = "Access denied by ABAC policy") {
    super(message, 403);
    this.name = "AccessDeniedError";
  }
}

export class ValidationError extends USFSDKError {
  constructor(message: string, statusCode: number, detail: Record<string, unknown> = {}) {
    super(message, statusCode, detail);
    this.name = "ValidationError";
  }
}
