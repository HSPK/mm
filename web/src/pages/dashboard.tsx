import { useNavigate } from "react-router-dom"
import { useMediaStore } from "@/stores/media"
import { Card, CardContent } from "@/components/ui/card"
import { Images, Film, Clock, Upload, Scan, ChevronLeft } from "lucide-react"

export default function DashboardPage() {
    const navigate = useNavigate()
    const total = useMediaStore((s) => s.total)

    const stats = [
        { label: "Total Media", value: total.toLocaleString(), icon: Images, color: "text-blue-400" },
        { label: "Videos", value: Math.floor(total * 0.2).toLocaleString(), icon: Film, color: "text-purple-400" },
        { label: "Last Scan", value: "2 hours ago", icon: Clock, color: "text-green-400" },
    ]

    const activity = [
        { type: "upload" as const, count: 5, date: "Today" },
        { type: "scan" as const, count: 120, date: "Yesterday" },
    ]

    return (
        <div>
            {/* Sticky header */}
            <div className="sticky top-0 z-20 flex items-center gap-3 px-4 h-14 bg-background/80 backdrop-blur-xl border-b border-border/40">
                <button
                    onClick={() => navigate(-1)}
                    className="flex items-center justify-center h-9 w-9 rounded-full hover:bg-secondary transition-colors"
                >
                    <ChevronLeft className="h-5 w-5" />
                </button>
                <h1 className="text-lg font-semibold">Dashboard</h1>
            </div>

            <div className="p-6 max-w-5xl mx-auto space-y-8">

                {/* stat cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {stats.map((s) => (
                        <Card key={s.label}>
                            <CardContent className="pt-6">
                                <div className="flex items-center gap-3">
                                    <div className={`rounded-lg bg-secondary p-2.5 ${s.color}`}>
                                        <s.icon className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">{s.label}</p>
                                        <p className="text-2xl font-semibold">{s.value}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* recent activity */}
                <div>
                    <h2 className="text-lg font-semibold mb-3">Recent Activity</h2>
                    <Card>
                        <CardContent className="pt-4 divide-y divide-border">
                            {activity.map((a, i) => (
                                <div key={i} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                                    <div className={`rounded-lg p-2 ${a.type === "upload" ? "bg-blue-500/10 text-blue-400" : "bg-green-500/10 text-green-400"}`}>
                                        {a.type === "upload" ? <Upload className="h-4 w-4" /> : <Scan className="h-4 w-4" />}
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm font-medium">
                                            {a.type === "upload" ? "New Uploads" : "System Scan"}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {a.count} items &middot; {a.date}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
