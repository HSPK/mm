import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { ImageIcon, Lock, User } from "lucide-react"
import { useAuthStore } from "@/stores/auth"
import { Button } from "@/components/ui/button"

export default function LoginPage() {
    const navigate = useNavigate()
    const { login, loading, error } = useAuthStore()
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        const ok = await login(username, password)
        if (ok) navigate("/", { replace: true })
    }

    return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="w-full max-w-[360px] space-y-10">
                {/* App identity — Apple sign-in style: large icon, name, single-line tagline */}
                <div className="flex flex-col items-center text-center space-y-4">
                    <div className="flex h-[72px] w-[72px] items-center justify-center rounded-[20px] bg-gradient-to-br from-primary to-primary/70 elevation-2">
                        <ImageIcon className="h-9 w-9 text-white" strokeWidth={1.75} />
                    </div>
                    <div className="space-y-1">
                        <h1 className="text-[28px] font-bold tracking-tight">Sign in to MM</h1>
                        <p className="text-[15px] text-muted-foreground">Your personal media library</p>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-3">
                    {/* Apple-style joined field group: rounded card containing inputs separated by hairlines */}
                    <div className="bg-card rounded-2xl overflow-hidden elevation-1">
                        <div className="flex items-center px-4">
                            <User className="h-5 w-5 text-muted-foreground/60 shrink-0" strokeWidth={1.75} />
                            <input
                                id="username"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Apple ID or username"
                                autoComplete="username"
                                autoFocus
                                aria-label="Username"
                                className="flex-1 bg-transparent h-12 px-3 text-[15px] placeholder:text-muted-foreground/60 focus:outline-none"
                            />
                        </div>
                        <div className="border-t border-border" />
                        <div className="flex items-center px-4">
                            <Lock className="h-5 w-5 text-muted-foreground/60 shrink-0" strokeWidth={1.75} />
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Password"
                                autoComplete="current-password"
                                aria-label="Password"
                                aria-invalid={error ? true : undefined}
                                className="flex-1 bg-transparent h-12 px-3 text-[15px] placeholder:text-muted-foreground/60 focus:outline-none"
                            />
                        </div>
                    </div>

                    {error && (
                        <p className="px-2 text-[13px] text-destructive" role="alert">{error}</p>
                    )}

                    <Button
                        type="submit"
                        size="lg"
                        className="w-full"
                        loading={loading}
                        disabled={!username || !password}
                    >
                        {loading ? "Signing in…" : "Sign in"}
                    </Button>
                </form>
            </div>
        </div>
    )
}
