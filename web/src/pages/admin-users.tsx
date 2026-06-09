import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Navigate } from "react-router-dom"
import { Plus, ShieldCheck, Trash2, User as UserIcon } from "lucide-react"
import { usersRepo } from "@/api/users"
import type { UserDetail } from "@/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { ListGroup, ListPage, ListRow } from "@/components/ui/list"
import { PageHeader } from "@/components/ui/page-header"
import { Spinner } from "@/components/ui/spinner"
import { useAuthStore } from "@/stores/auth"
import { toast } from "@/stores/toast"
import { fmtDateShort } from "@/lib/format"

export default function AdminUsersPage() {
    const me = useAuthStore((s) => s.user)
    const [users, setUsers] = useState<UserDetail[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [showCreate, setShowCreate] = useState(false)

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            setUsers(await usersRepo.list())
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load users")
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        if (me?.is_admin) void load()
    }, [me?.is_admin, load])

    if (me && !me.is_admin) {
        return <Navigate to="/settings" replace />
    }

    const handleDelete = useCallback(async (user: UserDetail) => {
        if (user.id === me?.id) {
            toast.error("Can't delete your own account")
            return
        }
        if (!confirm(`Delete user "${user.username}"?`)) return
        try {
            await usersRepo.remove(user.id)
            setUsers((prev) => prev.filter((u) => u.id !== user.id))
            toast.success(`Deleted ${user.username}`)
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Delete failed")
        }
    }, [me?.id])

    return (
        <div className="pb-24 min-h-screen">
            <PageHeader
                title="Users"
                back
                largeTitle
                actions={
                    <Button
                        size="sm"
                        variant="plain"
                        onClick={() => setShowCreate((v) => !v)}
                    >
                        <Plus className="h-4 w-4" />
                        New
                    </Button>
                }
            />

            <ListPage>
                {showCreate && (
                    <CreateUserForm
                        onCancel={() => setShowCreate(false)}
                        onCreated={(u) => {
                            // Returned shape lacks created_at; refetch to keep list consistent.
                            void load()
                            setShowCreate(false)
                            toast.success(`Created ${u.username}`)
                        }}
                    />
                )}

                {loading && users.length === 0 && (
                    <div className="py-12 flex justify-center"><Spinner /></div>
                )}

                {!loading && error && (
                    <EmptyState
                        icon={UserIcon}
                        title="Couldn’t load users"
                        description={error}
                        action={{ label: "Retry", onClick: () => void load(), variant: "primary" }}
                    />
                )}

                {users.length > 0 && (
                    <ListGroup label={`${users.length} ${users.length === 1 ? "user" : "users"}`}>
                        {users.map((user) => {
                            const isMe = user.id === me?.id
                            return (
                                <ListRow
                                    key={user.id}
                                    icon={{
                                        icon: user.is_admin ? <ShieldCheck className="h-4 w-4" /> : <UserIcon className="h-4 w-4" />,
                                        tint: user.is_admin ? "#ff9500" : "#8e8e93",
                                    }}
                                    label={user.display_name || user.username}
                                    sublabel={[
                                        user.display_name ? `@${user.username}` : null,
                                        user.created_at ? `Joined ${fmtDateShort(user.created_at)}` : null,
                                        isMe ? "You" : null,
                                    ].filter(Boolean).join(" · ")}
                                    trailing={
                                        !isMe && (
                                            <button
                                                onClick={(e) => { e.stopPropagation(); void handleDelete(user) }}
                                                className="text-destructive hover:text-destructive/80 p-1.5 -mr-1.5 rounded-full hover:bg-destructive/10"
                                                aria-label={`Delete ${user.username}`}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </button>
                                        )
                                    }
                                />
                            )
                        })}
                    </ListGroup>
                )}
            </ListPage>
        </div>
    )
}

function CreateUserForm({
    onCancel,
    onCreated,
}: {
    onCancel: () => void
    onCreated: (user: { username: string }) => void
}) {
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    const [displayName, setDisplayName] = useState("")
    const [isAdmin, setIsAdmin] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const submit = async (e: FormEvent) => {
        e.preventDefault()
        if (!username.trim() || !password) return
        setSubmitting(true)
        setError(null)
        try {
            const u = await usersRepo.create({
                username: username.trim(),
                password,
                display_name: displayName.trim() || undefined,
                is_admin: isAdmin,
            })
            onCreated(u)
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create user")
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Card>
            <CardContent className="pt-5">
                <form onSubmit={submit} className="space-y-3">
                    <h3 className="text-[15px] font-semibold">New user</h3>
                    <Input
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Username"
                        autoComplete="off"
                        autoFocus
                    />
                    <Input
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                        placeholder="Display name (optional)"
                        autoComplete="off"
                    />
                    <Input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Password"
                        autoComplete="new-password"
                    />
                    <label className="flex items-center gap-2.5 px-1 py-1 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={isAdmin}
                            onChange={(e) => setIsAdmin(e.target.checked)}
                            className="h-4 w-4 accent-primary"
                        />
                        <span className="text-[14px]">Administrator</span>
                    </label>
                    {error && <p className="text-[12px] text-destructive">{error}</p>}
                    <div className="flex gap-2 justify-end pt-1">
                        <Button type="button" variant="plain" onClick={onCancel} disabled={submitting}>
                            Cancel
                        </Button>
                        <Button type="submit" loading={submitting} disabled={!username.trim() || !password}>
                            Create
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    )
}
