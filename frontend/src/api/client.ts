import axios from 'axios';
import type {
  Event,
  EventFilters,
  EventListResponse,
  ProcessPendingResponse,
  RawPost,
  RawPostListResponse,
  EventGlobalMetrics,
  WebhookAlert,
  WebhookAlertCreate,
  WebhookAlertUpdate,
} from '../types';

const rawApiUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const API_BASE_URL = rawApiUrl
  ? (rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl}/api/v1`)
  : '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchEvents = async (filters: EventFilters = {}, limit?: number): Promise<EventListResponse> => {
  const params: Record<string, any> = { limit: limit ?? (filters as any).limit ?? 100 };
  if (filters.threat_level) params.threat_level = filters.threat_level;
  if (filters.min_threat_score) params.min_threat_score = filters.min_threat_score;
  if (filters.search) params.search = filters.search;
  if (filters.event_type) params.event_type = filters.event_type;
  if (filters.bbox) params.bbox = filters.bbox;
  if (filters.countries && filters.countries.length > 0) {
    params.countries = filters.countries.join(',');
  }

  const response = await apiClient.get<EventListResponse>('/events', { params });
  return response.data;
};

export const exportEvents = async (filters: EventFilters, format: 'pdf' | 'stix'): Promise<void> => {
  const params: Record<string, any> = { format };
  if (filters.threat_level) params.threat_level = filters.threat_level;
  if (filters.min_threat_score) params.min_threat_score = filters.min_threat_score;
  if (filters.search) params.search = filters.search;
  if (filters.event_type) params.event_type = filters.event_type;
  if (filters.bbox) params.bbox = filters.bbox;
  if (filters.countries && filters.countries.length > 0) {
    params.countries = filters.countries.join(',');
  }

  const response = await apiClient.get('/events/export', {
    params,
    responseType: 'blob', // Important for handling binary streams
  });

  // Trigger download
  const blob = new Blob([response.data], {
    type: format === 'pdf' ? 'application/pdf' : 'application/stix+json',
  });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;

  // Extract filename from header if possible, else fallback
  const contentDisposition = response.headers['content-disposition'];
  let filename = format === 'pdf' ? 'threatatlas_export.pdf' : 'threatatlas_export.json';
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
    if (filenameMatch && filenameMatch.length === 2) {
      filename = filenameMatch[1];
    }
  }

  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const fetchGlobalMetrics = async (): Promise<EventGlobalMetrics> => {
  const response = await apiClient.get<EventGlobalMetrics>('/events/stats');
  return response.data;
};

export const fetchAvailableCountries = async (): Promise<string[]> => {
  const response = await apiClient.get<string[]>('/events/countries');
  return response.data;
};

export const getEventById = async (id: string): Promise<Event> => {
  const response = await apiClient.get<Event>(`/events/${id}`);
  return response.data;
};

export const getEventSources = async (id: string): Promise<RawPost[]> => {
  const response = await apiClient.get<RawPost[]>(`/events/${id}/sources`);
  return response.data;
};

export const fetchRawPosts = async (source?: string, status?: string): Promise<RawPostListResponse> => {
  const params: Record<string, any> = { limit: 100 };
  if (source) params.source = source;
  if (status) params.processing_status = status;

  const response = await apiClient.get<RawPostListResponse>('/raw-posts', { params });
  return response.data;
};

export const processPendingPosts = async (): Promise<ProcessPendingResponse> => {
  const response = await apiClient.post<ProcessPendingResponse>('/intelligence/process-pending');
  return response.data;
};

export const checkHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/health', {
      // Prevent axios from throwing on 4xx/5xx so we can handle it manually if needed,
      // though axios defaults to throwing which is fine since it goes to catch block.
      // We'll rely on the default throw for 4xx/5xx.
    });

    if (response.status !== 200) {
      return false;
    }

    const contentType = String(response.headers['content-type'] || '');
    if (!contentType.includes('application/json')) {
      return false;
    }

    const data = response.data;
    if (data && typeof data === 'object' && data.status === 'ok') {
      return true;
    }

    return false;
  } catch (err) {
    return false;
  }
};

// Webhooks API
export const fetchWebhooks = async (): Promise<WebhookAlert[]> => {
  const response = await apiClient.get<WebhookAlert[]>('/webhooks');
  return response.data;
};

export const createWebhook = async (data: WebhookAlertCreate): Promise<WebhookAlert> => {
  const response = await apiClient.post<WebhookAlert>('/webhooks', data);
  return response.data;
};

export const updateWebhook = async (id: string, data: WebhookAlertUpdate): Promise<WebhookAlert> => {
  const response = await apiClient.patch<WebhookAlert>(`/webhooks/${id}`, data);
  return response.data;
};

export const deleteWebhook = async (id: string): Promise<void> => {
  await apiClient.delete(`/webhooks/${id}`);
};

export const testWebhook = async (id: string): Promise<{ status: string, detail: string }> => {
  const response = await apiClient.post<{ status: string, detail: string }>(`/webhooks/${id}/test`);
  return response.data;
};
