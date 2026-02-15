import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Save } from "lucide-react"

export default function SettingsPage() {
    const [libraryPath, setLibraryPath] = useState("/mnt/media")
    const [autoScan, setAutoScan] = useState(true)
    const [scanInterval, setScanInterval] = useState("02:00:00")
    const [thumbnailQuality, setThumbnailQuality] = useState(80)

    const handleSave = () => {
        console.log("Saving settings:", { libraryPath, autoScan, scanInterval, thumbnailQuality })
    }

    return (
        <div className="p-6 max-w-2xl mx-auto space-y-6">
            <h1 className="text-2xl font-bold">Settings</h1>

            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Library Configuration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Library Path</label>
                        <Input value={libraryPath} onChange={(e) => setLibraryPath(e.target.value)} />
                    </div>

                    <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">Auto Scan</label>
                        <button
                            type="button"
                            role="switch"
                            aria-checked={autoScan}
                            onClick={() => setAutoScan(!autoScan)}
                            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors ${autoScan ? "bg-primary" : "bg-muted"}`}
                        >
                            <span className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform ${autoScan ? "translate-x-5" : "translate-x-0.5"} mt-0.5`} />
                        </button>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Scan Interval</label>
                        <Input value={scanInterval} onChange={(e) => setScanInterval(e.target.value)} placeholder="HH:MM:SS" />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Thumbnail Quality</label>
                        <Input
                            type="number"
                            min={10}
                            max={100}
                            value={thumbnailQuality}
                            onChange={(e) => setThumbnailQuality(Number(e.target.value))}
                        />
                    </div>

                    <div className="flex justify-end pt-2">
                        <Button onClick={handleSave}>
                            <Save className="mr-2 h-4 w-4" />
                            Save Changes
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
