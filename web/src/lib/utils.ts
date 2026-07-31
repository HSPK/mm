import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]", ""])

/** True when the web app is served from the same machine as the server, so a
 *  server-side "reveal in file manager" action opens on the user's own screen. */
export function isLocalMachine() {
    return typeof window !== "undefined" && LOCAL_HOSTS.has(window.location.hostname)
}
