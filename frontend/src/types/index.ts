export interface GeoJSONPoint {
  type: string;
  coordinates: [number, number]; // [lng, lat]
}

export interface EventEntities {
  locations: string[];
  organizations: string[];
  equipment: string[];
}

export interface ThreatScoreBreakdown {
  action_score: number;
  equipment_score: number;
  location_score: number;
  frequency_score: number;
  total: number;
}

export interface CredibilityScoreBreakdown {
  max_base_source_reliability: number;
  independent_source_count: number;
  corroboration_bonus: number;
  total: number;
}

export interface ScoreBreakdown {
  threat?: ThreatScoreBreakdown;
  credibility?: CredibilityScoreBreakdown;
  cluster_match_score?: number;
}

export interface Event {
  id: string;
  title: string;
  summary?: string;
  raw_post_ids: string[];
  source_ids: string[];
  event_type?: string;
  entities: EventEntities;
  location_name?: string;
  location?: GeoJSONPoint;
  country_code?: string;
  event_timestamp: string;
  threat_score: number;
  threat_level: 'Low' | 'Medium' | 'High';
  credibility_score: number;
  related_event_ids: string[];
  corroboration_count: number;
  score_breakdown?: ScoreBreakdown;
  created_at: string;
  updated_at: string;
}

export interface EventListResponse {
  total: number;
  limit: number;
  skip: number;
  items: Event[];
}

export interface EventGlobalMetrics {
  total: number;
  high: number;
  medium: number;
  low: number;
}

export interface RawPost {
  id: string;
  source: string;
  source_specific_id: string;
  text: string;
  url?: string;
  original_timestamp: string;
  language?: string;
  author?: string;
  collected_at: string;
  processing_status: string;
  created_at: string;
  updated_at: string;
}

export interface RawPostListResponse {
  total: number;
  limit: number;
  skip: number;
  items: RawPost[];
}

export interface ProcessPendingResponse {
  status?: string;
  unlocked_count?: number;
  deleted_events?: number;
  deleted_posts?: number;
  processed_count?: number;
  passed_relevance?: number;
  geocoded_count?: number;
  events_created?: number;
  events_merged?: number;
  events_ignored?: number;
  errors?: number;
}

export interface EventFilters {
  threat_level?: string;
  min_threat_score?: number;
  search?: string;
  event_type?: string;
  bbox?: string;
  countries?: string[];
}

export interface WebhookAlert {
  id: string;
  url: string;
  provider: 'discord' | 'slack' | 'generic';
  is_active: boolean;
  min_threat_level: 'High' | 'Critical';
  countries?: string[];
  bbox?: [[number, number], [number, number]];
  created_at: string;
  updated_at: string;
}

export type WebhookAlertCreate = Omit<WebhookAlert, 'id' | 'created_at' | 'updated_at'>;
export type WebhookAlertUpdate = Partial<WebhookAlertCreate>;
