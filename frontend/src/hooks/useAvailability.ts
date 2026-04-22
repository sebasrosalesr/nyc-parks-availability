import { useEffect, useRef, useState } from "react";
import { fetchAvailability } from "../api/parks";
import type { AvailabilityResponse, FieldType } from "../types";
import { format } from "date-fns";

interface Params {
  fieldType: FieldType;
  startDate: Date | null;
  endDate: Date | null;
}

export function useAvailability({ fieldType, startDate, endDate }: Params) {
  const [data, setData] = useState<AvailabilityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!startDate || !endDate) return;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setLoading(true);
    setError(null);

    fetchAvailability({
      field_type: fieldType,
      start_date: format(startDate, "yyyy-MM-dd"),
      end_date: format(endDate, "yyyy-MM-dd"),
    }, ctrl.signal)
      .then((res) => {
        if (!ctrl.signal.aborted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!ctrl.signal.aborted && err.name !== "AbortError") {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => ctrl.abort();
  }, [fieldType, startDate, endDate]);

  return { data, loading, error };
}
