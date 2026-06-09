import { useEffect, useState } from "react"
import { catalogRepo, type CameraInfo } from "@/api/catalog"

export function useCameras(): CameraInfo[] {
    const [cameras, setCameras] = useState<CameraInfo[]>([])
    useEffect(() => {
        let alive = true
        catalogRepo.listCameras()
            .then((data) => { if (alive) setCameras(data) })
            .catch(() => { })
        return () => { alive = false }
    }, [])
    return cameras
}
