import type { AxiosInstance } from "axios"
import { api as defaultApi } from "@/api/client"
import type {
    CameraStats,
    GeoPoint,
    LibraryStats,
    TimelineEntry,
} from "@/api/types"

export interface StatsRepository {
    overview(): Promise<LibraryStats>
    listCameras(): Promise<CameraStats[]>
    timeline(): Promise<TimelineEntry[]>
    /** Compact GPS-tagged media markers for the Map view (single fast query). */
    geo(limit?: number): Promise<GeoPoint[]>
}

export function createStatsRepository(api: AxiosInstance = defaultApi): StatsRepository {
    return {
        overview: async () => (await api.get<LibraryStats>("/stats")).data,
        listCameras: async () => (await api.get<CameraStats[]>("/cameras")).data,
        timeline: async () => (await api.get<TimelineEntry[]>("/timeline")).data,
        geo: async (limit) =>
            (await api.get<GeoPoint[]>("/geo", limit ? { params: { limit } } : undefined)).data,
    }
}

export const statsRepo: StatsRepository = createStatsRepository()
