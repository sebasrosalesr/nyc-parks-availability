import type { AvailabilityResponse, ParkInfo } from "../types";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function apiFetch<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { signal });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function fetchParks(): Promise<ParkInfo[]> {
  return apiFetch<ParkInfo[]>("/api/parks");
}

export function fetchAvailability(params: {
  field_type: string;
  start_date: string;
  end_date: string;
  prop_ids?: string;
}, signal?: AbortSignal): Promise<AvailabilityResponse> {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined) as [string, string][]
    )
  ).toString();
  return apiFetch<AvailabilityResponse>(`/api/availability?${qs}`, signal);
}
