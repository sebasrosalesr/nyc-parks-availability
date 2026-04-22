export type FieldType = "soccer" | "baseball" | "basketball" | "softball" | "football" | "cricket";

export interface TimeBlock {
  start: string;
  end: string;
}

export interface DayAvailability {
  date: string;
  open_blocks: TimeBlock[];
  open_minutes: number;
  potential_minutes: number;
}

export interface FieldSchedule {
  field_id: string;
  field_name: string;
  park_name: string;
  prop_id: string;
  borough: string;
  surface_type: string | null;
  total_available_minutes: number;
  days: DayAvailability[];
}

export interface AvailabilityQuery {
  field_type: string;
  start_date: string;
  end_date: string;
  prop_ids: string[];
  matching_field_count: number;
  matching_park_count: number;
  snapshot_count: number;
  live_snapshot_count: number;
  cached_snapshot_count: number;
}

export interface AvailabilityResponse {
  fields: FieldSchedule[];
  fetched_at: string;
  query: AvailabilityQuery;
}

export interface ParkInfo {
  prop_id: string;
  name: string;
  borough: string;
}
