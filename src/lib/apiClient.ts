import { API_CONFIG } from '../config/constants';

export type ApiErrorCategory = 'network' | 'timeout' | 'auth' | 'server' | 'client' | 'unknown';

export interface ApiErrorShape {
  message: string;
  status: number;
  category: ApiErrorCategory;
  detail?: unknown;
  retryable?: boolean;
}

export class ApiError extends Error implements ApiErrorShape {
  status: number;
  category: ApiErrorCategory;
  detail?: unknown;
  retryable?: boolean;

  constructor(message: string, status: number, category: ApiErrorCategory, detail?: unknown, retryable = false) {
    super(message);
    this.status = status;
    this.category = category;
    this.detail = detail;
    this.retryable = retryable;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

type ResponseType = 'json' | 'blob' | 'text' | 'void';

interface RequestOptions extends RequestInit {
  query?: Record<string, unknown>;
  timeoutMs?: number;
  responseType?: ResponseType;
}

export class ApiClient {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string = API_CONFIG.BASE_URL, timeout: number = API_CONFIG.TIMEOUT) {
    this.baseUrl = this.normalizeBaseUrl(baseUrl);
    this.timeout = timeout;
  }

  private normalizeBaseUrl(baseUrl: string): string {
    const normalized = baseUrl.replace(/\/$/, '');
    if (normalized.endsWith('/api/v1')) {
      return normalized;
    }
    return `${normalized}/api/v1`;
  }

  private buildUrl(path: string, query?: Record<string, unknown>): string {
    const normalizedPath = path.startsWith('http')
      ? path
      : `${this.baseUrl}${path.startsWith('/') ? '' : '/'}${path}`;

    if (!query) {
      return normalizedPath;
    }

    const searchParams = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      searchParams.append(key, String(value));
    });

    const queryString = searchParams.toString();
    if (!queryString) {
      return normalizedPath;
    }

    return `${normalizedPath}${normalizedPath.includes('?') ? '&' : '?'}${queryString}`;
  }

  private getHeaders(initHeaders: HeadersInit | undefined, body: unknown): Headers {
    const headers = new Headers(initHeaders || {});
    const isFormData = body instanceof FormData;

    if (!isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    return headers;
  }

  private categorizeStatus(status: number): ApiErrorCategory {
    if (status === 0) return 'network';
    if (status === 401 || status === 403) return 'auth';
    if (status >= 500) return 'server';
    if (status >= 400) return 'client';
    return 'unknown';
  }

  private async parseResponse<T>(response: Response, responseType: ResponseType): Promise<T> {
    if (responseType === 'void' || response.status === 204) {
      return {} as T;
    }

    if (responseType === 'blob') {
      return await response.blob() as T;
    }

    if (responseType === 'text') {
      return await response.text() as T;
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return await response.json() as T;
    }

    const text = await response.text();
    return text as unknown as T;
  }

  private async buildError(response: Response): Promise<ApiError> {
    let detail: unknown;
    try {
      const contentType = response.headers.get('content-type') || '';
      detail = contentType.includes('application/json') ? await response.json() : await response.text();
    } catch {
      detail = undefined;
    }

    const category = this.categorizeStatus(response.status);
    const message =
      (detail as any)?.detail ||
      (detail as any)?.message ||
      response.statusText ||
      'Request failed';

    const retryable = category === 'network' || category === 'server';
    return new ApiError(message, response.status, category, detail, retryable);
  }

  private prepareBody(body: unknown): BodyInit | undefined {
    if (!body) return undefined;
    if (body instanceof FormData || typeof body === 'string' || body instanceof Blob) {
      return body as BodyInit;
    }
    return JSON.stringify(body);
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const {
      query,
      timeoutMs,
      responseType = 'json',
      headers,
      ...fetchOptions
    } = options;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs ?? this.timeout);

    try {
      const response = await fetch(this.buildUrl(path, query), {
        credentials: 'include',
        ...fetchOptions,
        headers: this.getHeaders(headers, fetchOptions.body),
        body: this.prepareBody(fetchOptions.body),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw await this.buildError(response);
      }

      return await this.parseResponse<T>(response, responseType);
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        throw new ApiError('Request timed out', 0, 'timeout', null, true);
      }

      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError(
        error?.message || 'Network error or server unavailable',
        0,
        'network',
        error,
        true
      );
    } finally {
      clearTimeout(timer);
    }
  }

  async get<T>(path: string, query?: Record<string, unknown>, options?: Omit<RequestOptions, 'method' | 'query'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET', query });
  }

  async post<T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body });
  }

  async put<T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PUT', body });
  }

  async delete<T>(path: string, options?: Omit<RequestOptions, 'method'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' });
  }

  async upload<T>(path: string, formData: FormData, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'POST',
      body: formData,
      headers: {
        ...(options?.headers || {}),
        // Let the browser set multipart boundaries
      },
    });
  }

  async uploadFile<T>(path: string, formData: FormData, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.upload<T>(path, formData, options);
  }

  async download(path: string, query?: Record<string, unknown>, options?: Omit<RequestOptions, 'method' | 'responseType'>): Promise<Blob> {
    return this.request<Blob>(path, { ...options, method: 'GET', query, responseType: 'blob' });
  }
}

export const apiClient = new ApiClient();
