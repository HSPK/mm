import { describe, expect, it } from "vitest"
import { isActiveOrganizerJob, isTerminalOrganizerJob } from "./use-organizer-job"

describe("organizer job lifecycle", () => {
    it("treats canceling jobs as active and partial/canceled jobs as terminal", () => {
        expect(isActiveOrganizerJob("queued")).toBe(true)
        expect(isActiveOrganizerJob("canceling")).toBe(true)
        expect(isTerminalOrganizerJob("completed_with_errors")).toBe(true)
        expect(isTerminalOrganizerJob("canceled")).toBe(true)
        expect(isTerminalOrganizerJob("running")).toBe(false)
    })
})
